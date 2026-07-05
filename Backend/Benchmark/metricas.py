import time
import psutil
import os
import csv
import psycopg2
import random
import shutil
from pathlib import Path

TAMAÑOS = [1001]
QUERIES_TEXTO = ["blue shirt", "black shoes", "red dress", "summer hat", "casual jeans"]
DB_CONFIG = {"host": "localhost", "port": "5432", "database": "multimodal", "user": "postgres", "password": "123456"}

BASE_DIR = Path(__file__).resolve().parent.parent
IMAGES_DIR = BASE_DIR / "Multimodal" / "Data" / "test_metrics_images"

TODAS_LAS_IMAGENES = list(IMAGES_DIR.glob("*.jpg"))
if not TODAS_LAS_IMAGENES:
    print(f"ADVERTENCIA: No se encontraron imágenes en {IMAGES_DIR}")
    QUERY_IMAGENES = []
else:
    QUERY_IMAGENES = random.sample(TODAS_LAS_IMAGENES, min(5, len(TODAS_LAS_IMAGENES)))


def preparar_entorno(tamano, db_config):
    data_dir = BASE_DIR / "Multimodal" / "Data"
    carpeta_respaldo = data_dir / str(tamano)
    archivo_csv = carpeta_respaldo / f"descriptors_dump_{tamano}.csv"
    archivo_pkl = carpeta_respaldo / f"visual_codebook_{tamano}.pkl"

    if carpeta_respaldo.exists() and archivo_csv.exists() and archivo_pkl.exists():
        print(f"\nArchivos encontrados para tamaño {tamano}. Actualizando PostgreSQL...")
        import pickle
        from Backend.Multimodal.Offline.Persistence import PersistenceManager
        
        with open(archivo_pkl, "rb") as f:
            dimension_real = len(pickle.load(f))
            
        print(f"  Recreando tabla PostgreSQL con dimensión {dimension_real}...")
        pm = PersistenceManager(n_documents=tamano, **db_config)
        pm.create_tables(histogram_dim=dimension_real)
        
        print("  Inyectando datos del CSV a PostgreSQL...")
        filas = pm.load_csv(str(archivo_csv))
        pm.close()
        print(f"  Base de datos lista ({filas} filas cargadas).")
        return True
    else:
        print(f"\nNo se encontró respaldo para tamaño {tamano}. Construyendo índice desde cero...")
        import subprocess
        try:
            subprocess.run(
                ["python", "-m", "Backend.Multimodal.Offline.Orquestador", "--dataset-size", str(tamano), "--processes", "4"],
                check=True
            )
            print(f"  Construcción offline completada con éxito para tamaño {tamano}.")
            return True
        except subprocess.CalledProcessError:
            print(f"\nERROR: Falló la construcción offline para el tamaño {tamano}.")
            return False

def medir_memoria_e_io():
    proceso = psutil.Process(os.getpid())
    mem = proceso.memory_info().rss / (1024 * 1024)
    io = proceso.io_counters().read_count 
    return mem, io

def calcular_recall(res_custom, res_pg):
    set_esperado = set(res_pg)
    set_obtenido = set([r["doc_id"] for r in res_custom])
    if not set_esperado: return 0.0
    return len(set_esperado.intersection(set_obtenido)) / len(set_esperado)


def busqueda_nativa_texto(conn, texto):
    query_explicar = """
        EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) 
        SELECT doc_id FROM descriptors 
        WHERE texto_vector @@ plainto_tsquery('english', %s) 
        ORDER BY ts_rank(texto_vector, plainto_tsquery('english', %s)) DESC 
        LIMIT 10;
    """
    with conn.cursor() as cur:
        cur.execute(query_explicar, (texto, texto))
        explicacion = cur.fetchone()[0][0]
        io_blocks = explicacion.get("Plan", {}).get("Shared Read Blocks", 0)
        
    query_real = """
        SELECT doc_id FROM descriptors 
        WHERE texto_vector @@ plainto_tsquery('english', %s) 
        ORDER BY ts_rank(texto_vector, plainto_tsquery('english', %s)) DESC 
        LIMIT 10;
    """
    with conn.cursor() as cur:
        cur.execute(query_real, (texto, texto))
        return [row[0] for row in cur.fetchall()], io_blocks

def busqueda_nativa_imagen(conn, orquestador, ruta_imagen):
    vector = orquestador._image_histogram(str(ruta_imagen))
    vector_string = f"[{','.join(map(str, vector))}]"
    
    query_explicar = """
        EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) 
        SELECT doc_id FROM descriptors 
        ORDER BY image_histogram <=> %s::vector 
        LIMIT 10;
    """
    with conn.cursor() as cur:
        cur.execute(query_explicar, (vector_string,))
        explicacion = cur.fetchone()[0][0]
        io_blocks = explicacion.get("Plan", {}).get("Shared Read Blocks", 0)
        
    query_real = """
        SELECT doc_id FROM descriptors 
        ORDER BY image_histogram <=> %s::vector 
        LIMIT 10;
    """
    with conn.cursor() as cur:
        cur.execute(query_real, (vector_string,))
        return [row[0] for row in cur.fetchall()], io_blocks


def ejecutar_benchmark():
    from Backend.Multimodal.Online.Orquestador import OnlineOrchestrator

    conn = psycopg2.connect(**DB_CONFIG)
    resultados = []

    for tamano in TAMAÑOS:
        if not preparar_entorno(tamano, DB_CONFIG):
            continue
        
        orquestador = OnlineOrchestrator(db_config=DB_CONFIG, n_documents=tamano)
        
        print(f"\nEvaluando Textos (Tamaño {tamano})")
        for q in QUERIES_TEXTO:
            mem_1, io_1 = medir_memoria_e_io()
            ini = time.perf_counter()
            res_custom = orquestador.search_text(q, k=10)
            lat_custom = time.perf_counter() - ini
            mem_2, io_2 = medir_memoria_e_io()
            
            ini = time.perf_counter()
            res_pg, io_pg = busqueda_nativa_texto(conn, q)
            lat_pg = time.perf_counter() - ini

            resultados.append({"tamano": tamano, "tipo": "Texto", "query": q, "motor": "Custom_SPIMI", "latencia": lat_custom, "throughput_qps": 1.0 / lat_custom if lat_custom > 0 else 0.0, "ram_mb": mem_2 - mem_1, "io": io_2 - io_1, "recall": calcular_recall(res_custom, res_pg)})
            resultados.append({"tamano": tamano, "tipo": "Texto", "query": q, "motor": "Postgres_GIN", "latencia": lat_pg, "throughput_qps": 1.0 / lat_pg if lat_pg > 0 else 0.0, "ram_mb": "En_BD", "io": io_pg, "recall": 1.0})

        print(f"\nEvaluando Imágenes (Tamaño {tamano})")
        for ruta_img in QUERY_IMAGENES:
            nombre_archivo = ruta_img.name
            
            mem_1, io_1 = medir_memoria_e_io()
            ini = time.perf_counter()
            res_custom = orquestador.search_image(str(ruta_img), k=10)
            lat_custom = time.perf_counter() - ini
            mem_2, io_2 = medir_memoria_e_io()
            
            ini = time.perf_counter()
            res_pg, io_pg = busqueda_nativa_imagen(conn, orquestador, ruta_img)
            lat_pg = time.perf_counter() - ini

            resultados.append({"tamano": tamano, "tipo": "Imagen", "query": "IMG_" + nombre_archivo, "motor": "Custom_SPIMI", "latencia": lat_custom, "throughput_qps": 1.0 / lat_custom if lat_custom > 0 else 0.0, "ram_mb": mem_2 - mem_1, "io": io_2 - io_1, "recall": calcular_recall(res_custom, res_pg)})
            resultados.append({"tamano": tamano, "tipo": "Imagen", "query": "IMG_" + nombre_archivo, "motor": "Postgres_pgvector", "latencia": lat_pg, "throughput_qps": 1.0 / lat_pg if lat_pg > 0 else 0.0, "ram_mb": "En_BD", "io": io_pg, "recall": 1.0})

        orquestador.close()

    resultados_dir = BASE_DIR / "Benchmark" / "resultados"
    resultados_dir.mkdir(parents=True, exist_ok=True)
    with open(resultados_dir / "benchmark.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=resultados[0].keys())
        writer.writeheader()
        writer.writerows(resultados)
        
    print(f"\nBenchmark Completado, resultados guardados en: {resultados_dir / 'benchmark.csv'}")
    conn.close()

if __name__ == "__main__":
    ejecutar_benchmark()