import time
import psutil
import os
import csv
import psycopg2
import random
import shutil
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

TAMAÑOS = [10000, 20000, 30000, 40000]
TOP_K = 100
QUERIES_TEXTO = ["blue shirt", "black shoes", "red dress", "summer hat", "casual jeans"]
DB_CONFIG = {"host": "localhost", "port": "5433", "database": "multimodal", "user": "postgres", "password": "123456"}

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

def medir_disco(tamano):
    data_dir = BASE_DIR / "Multimodal" / "Data" / str(tamano)

    spimi_texto_bytes = sum([
        (data_dir / f"text_codebook_{tamano}.pkl").stat().st_size,
        (data_dir / f"vocab_{tamano}.pkl").stat().st_size,
        (data_dir / f"text_word_idf_{tamano}.pkl").stat().st_size,
        (data_dir / f"text_doc_norm_{tamano}.pkl").stat().st_size,
        (data_dir / f"text_index_{tamano}.btree").stat().st_size,
        (data_dir / f"text_index_{tamano}.heap").stat().st_size,
    ])

    spimi_imagen_bytes = sum([
        (data_dir / f"visual_codebook_{tamano}.pkl").stat().st_size,
        (data_dir / f"image_doc_norm_{tamano}.pkl").stat().st_size,
        (data_dir / f"image_index_{tamano}.btree").stat().st_size,
        (data_dir / f"image_index_{tamano}.heap").stat().st_size,
        (data_dir / f"image_word_idf_{tamano}.pkl").stat().st_size,
    ])

    try:
        conn = psycopg2.connect(**DB_CONFIG)
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute("SELECT pg_relation_size('idx_descriptors_texto_vector_gin')")
            pg_gin = cur.fetchone()[0]
            cur.execute("""
                SELECT COALESCE(pg_relation_size(c.reltoastrelid), 0)
                FROM pg_class c WHERE c.relname = 'descriptors'
            """)
            pg_toast = cur.fetchone()[0]
            cur.execute("SELECT pg_relation_size('idx_descriptors_image_histogram_ivfflat')")
            pg_ivfflat = cur.fetchone()[0]
        conn.close()
    except Exception:
        pg_gin = pg_toast = pg_ivfflat = 0

    codebook_bytes = (data_dir / f"visual_codebook_{tamano}.pkl").stat().st_size

    return {
        "tamano": tamano,
        "spimi_texto_mb": round(spimi_texto_bytes / (1024 * 1024), 2),
        "postgre_texto_mb": round((pg_gin + pg_toast) / (1024 * 1024), 2),
        "spimi_imagen_mb": round(spimi_imagen_bytes / (1024 * 1024), 2),
        "postgre_imagen_mb": round((pg_ivfflat + codebook_bytes) / (1024 * 1024), 2),
    }

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
        LIMIT 100;
    """
    with conn.cursor() as cur:
        cur.execute(query_explicar, (texto, texto))
        explicacion = cur.fetchone()[0][0]
        io_blocks = explicacion.get("Plan", {}).get("Shared Read Blocks", 0)
        
    query_real = """
        SELECT doc_id FROM descriptors 
        WHERE texto_vector @@ plainto_tsquery('english', %s) 
        ORDER BY ts_rank(texto_vector, plainto_tsquery('english', %s)) DESC 
        LIMIT 100;
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
        LIMIT 100;
    """
    with conn.cursor() as cur:
        cur.execute(query_explicar, (vector_string,))
        explicacion = cur.fetchone()[0][0]
        io_blocks = explicacion.get("Plan", {}).get("Shared Read Blocks", 0)
        
    query_real = """
        SELECT doc_id FROM descriptors 
        ORDER BY image_histogram <=> %s::vector 
        LIMIT 100;
    """
    with conn.cursor() as cur:
        cur.execute(query_real, (vector_string,))
        return [row[0] for row in cur.fetchall()], io_blocks


def ejecutar_benchmark():
    from Backend.Multimodal.Online.Orquestador import OnlineOrchestrator

    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = True
    resultados = []
    resultados_disco = []

    for tamano in TAMAÑOS:
        if not preparar_entorno(tamano, DB_CONFIG):
            continue
        
        orquestador = OnlineOrchestrator(db_config=DB_CONFIG, n_documents=tamano)
        resultados_disco.append(medir_disco(tamano))
        
        print(f"\nEvaluando Textos (Tamaño {tamano})")
        for q in QUERIES_TEXTO:
            io_antes = medir_memoria_e_io()[1]
            ini = time.perf_counter()
            res_custom = orquestador.search_text(q, k=TOP_K)
            lat_custom = time.perf_counter() - ini
            io_spimi = medir_memoria_e_io()[1] - io_antes
            
            ini = time.perf_counter()
            res_pg, io_pg = busqueda_nativa_texto(conn, q)
            lat_pg = time.perf_counter() - ini

            resultados.append({"tamano": tamano, "tipo": "Texto", "query": q, "motor": "Custom_SPIMI", "latencia": lat_custom, "throughput_qps": 1.0 / lat_custom if lat_custom > 0 else 0.0, "io": io_spimi, "recall": calcular_recall(res_custom, res_pg)})
            resultados.append({"tamano": tamano, "tipo": "Texto", "query": q, "motor": "Postgres_GIN", "latencia": lat_pg, "throughput_qps": 1.0 / lat_pg if lat_pg > 0 else 0.0, "io": io_pg, "recall": 1.0})

        print(f"\nEvaluando Imágenes (Tamaño {tamano})")
        for ruta_img in QUERY_IMAGENES:
            nombre_archivo = ruta_img.name
            
            io_antes = medir_memoria_e_io()[1]
            ini = time.perf_counter()
            res_custom = orquestador.search_image(str(ruta_img), k=TOP_K)
            lat_custom = time.perf_counter() - ini
            io_spimi = medir_memoria_e_io()[1] - io_antes
            
            ini = time.perf_counter()
            res_pg, io_pg = busqueda_nativa_imagen(conn, orquestador, ruta_img)
            lat_pg = time.perf_counter() - ini

            resultados.append({"tamano": tamano, "tipo": "Imagen", "query": "IMG_" + nombre_archivo, "motor": "Custom_SPIMI", "latencia": lat_custom, "throughput_qps": 1.0 / lat_custom if lat_custom > 0 else 0.0, "io": io_spimi, "recall": calcular_recall(res_custom, res_pg)})
            resultados.append({"tamano": tamano, "tipo": "Imagen", "query": "IMG_" + nombre_archivo, "motor": "Postgres_pgvector", "latencia": lat_pg, "throughput_qps": 1.0 / lat_pg if lat_pg > 0 else 0.0, "io": io_pg, "recall": 1.0})

        orquestador.close()

    resultados_dir = BASE_DIR / "Benchmark" / "resultados"
    resultados_dir.mkdir(parents=True, exist_ok=True)
    with open(resultados_dir / "benchmark.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=resultados[0].keys())
        writer.writeheader()
        writer.writerows(resultados)
        
    print(f"\nBenchmark Completado, resultados guardados en: {resultados_dir / 'benchmark.csv'}")

    print("Guardando métricas de disco...")
    with open(resultados_dir / "resultados_disco.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["tamano", "spimi_texto_mb", "postgre_texto_mb", "spimi_imagen_mb", "postgre_imagen_mb"])
        writer.writeheader()
        writer.writerows(resultados_disco)
    print(f"  Disco guardado en: {resultados_dir / 'resultados_disco.csv'}")

    print("Generando gráficos...")
    generar_graficos(resultados)
    generar_grafico_disco(resultados_disco)

    conn.close()

def generar_graficos(resultados):
    resultados_dir = BASE_DIR / "Benchmark" / "resultados"

    agg: dict[tuple, dict] = defaultdict(lambda: defaultdict(list))
    for r in resultados:
        key = (r["tamano"], r["motor"], r["tipo"])
        for metrica in ["latencia", "throughput_qps", "io", "recall"]:
            agg[key][metrica].append(r[metrica])


    proms: dict[tuple, dict] = {}
    for key, vals in agg.items():
        proms[key] = {k: sum(v)/len(v) for k, v in vals.items() if v}

    sizes = sorted(set(r["tamano"] for r in resultados))

    series = [
        ("Custom_SPIMI", "Texto", "SPIMI Texto", "o-", "tab:blue"),
        ("Custom_SPIMI", "Imagen", "SPIMI Imagen", "s-", "tab:orange"),
        ("Postgres_GIN", "Texto", "PostgreSQL Texto", "o--", "tab:green"),
        ("Postgres_pgvector", "Imagen", "PostgreSQL Imagen", "s--", "tab:red"),
    ]

    graficos = [
        ("latencia", "Latencia (s)", "Comparativa de Latencia al escalar la BD", ["SPIMI Texto", "SPIMI Imagen", "PostgreSQL Texto", "PostgreSQL Imagen"]),
        ("throughput_qps", "QPS", "Throughput (Consultas por segundo)", ["SPIMI Texto", "SPIMI Imagen", "PostgreSQL Texto", "PostgreSQL Imagen"]),
        ("io", "Bloques I/O", "Bloques Leídos del Disco (Accesos I/O)", ["SPIMI Texto", "SPIMI Imagen", "PostgreSQL Texto", "PostgreSQL Imagen"]),
        ("recall", "Recall", "Precisión de Recuperación vs PostgreSQL", ["SPIMI Texto", "SPIMI Imagen"]),
    ]

    for metrica, ylabel, titulo, incluir in graficos:
        fig, ax = plt.subplots(figsize=(8, 5))
        for motor, tipo, label, ls, color in series:
            if label not in incluir:
                continue
            vals = []
            for s in sizes:
                key = (s, motor, tipo)
                v = proms.get(key, {}).get(metrica, None)
                vals.append(v if v is not None else 0)
            ax.plot(sizes, vals, ls, color=color, label=label, linewidth=2, markersize=8)
        ax.set_xlabel("Volumen del Dataset (documentos)")
        ax.set_ylabel(ylabel)
        ax.set_title(titulo)
        ax.legend()
        ax.grid(True, linestyle=":", alpha=0.7)
        fig.tight_layout()
        safe = metrica.replace("/", "_")
        fig.savefig(resultados_dir / f"grafico_{safe}.png", dpi=150)
        plt.close(fig)
        print(f"  Gráfico guardado: grafico_{safe}.png")


def generar_grafico_disco(resultados_disco):
    resultados_dir = BASE_DIR / "Benchmark" / "resultados"
    sizes = [r["tamano"] for r in resultados_disco]

    spimi_texto = [r["spimi_texto_mb"] for r in resultados_disco]
    postgre_texto = [r["postgre_texto_mb"] for r in resultados_disco]
    spimi_imagen = [r["spimi_imagen_mb"] for r in resultados_disco]
    postgre_imagen = [r["postgre_imagen_mb"] for r in resultados_disco]

    x = range(len(sizes))
    width = 0.18

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar([i - 1.5 * width for i in x], spimi_texto, width, label="SPIMI Texto", color="tab:blue")
    ax.bar([i - 0.5 * width for i in x], postgre_texto, width, label="PostgreSQL Texto", color="tab:green")
    ax.bar([i + 0.5 * width for i in x], spimi_imagen, width, label="SPIMI Imagen", color="tab:orange")
    ax.bar([i + 1.5 * width for i in x], postgre_imagen, width, label="PostgreSQL Imagen", color="tab:red")

    ax.set_xlabel("Volumen del Dataset (documentos)")
    ax.set_ylabel("Tamaño en Disco (MB)")
    ax.set_title("Uso de Disco por Motor de Búsqueda")
    ax.set_xticks(list(x))
    ax.set_xticklabels([str(s) for s in sizes])
    ax.legend()
    ax.grid(True, linestyle=":", alpha=0.7, axis="y")
    fig.tight_layout()
    fig.savefig(resultados_dir / "grafico_disco.png", dpi=150)
    plt.close(fig)
    print(f"  Gráfico guardado: grafico_disco.png")


if __name__ == "__main__":
    ejecutar_benchmark()