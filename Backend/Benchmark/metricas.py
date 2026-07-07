import time
import csv
import math
import pickle
import psycopg2
import random
import numpy as np
from collections import defaultdict
from pathlib import Path
from pgvector.psycopg2 import register_vector

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

TAMAÑOS = [10000, 20000, 30000, 40000]
TOP_K = 50
QUERIES_TEXTO = ["Men|Apparel|Topwear|Shirts|Navy Blue|Fall|2011.0|Casual|Turtle Check Men Navy Blue Shirt", "Men|Apparel|Bottomwear|Jeans|Blue|Summer|2012.0|Casual|Peter England Men Party Blue Jeanss", "Women|Accessories|Watches|Watches|Silver|Winter|2016.0|Casual|Titan Women Silver Watch", "Men|Apparel|Bottomwear|Track Pants|Black|Fall|2011.0|Casual|Manchester United Men Solid Black Track Pants", "Men|Apparel|Topwear|Tshirts|Grey|Summer|2012.0|Casual|Puma Men Grey T-shirt"]

DB_CONFIG = {
    "host": "localhost", 
    "port": "5433", 
    "database": "multimodal", 
    "user": "postgres", 
    "password": "123456"
    }

BASE_DIR = Path(__file__).resolve().parent.parent
IMAGES_DIR = BASE_DIR / "Multimodal" / "Data" / "test_metrics_images"

TODAS_LAS_IMAGENES = list(IMAGES_DIR.glob("*.jpg"))
if not TODAS_LAS_IMAGENES:
    print(f"ADVERTENCIA: No se encontraron imágenes en {IMAGES_DIR}")
    QUERY_IMAGENES = []
else:
    QUERY_IMAGENES = random.sample(TODAS_LAS_IMAGENES, min(5, len(TODAS_LAS_IMAGENES)))

STYLES_CSV = BASE_DIR / "Multimodal" / "Data" / "styles.csv"

def load_subcategory_map(path: Path) -> dict[int, str]:
    mapping: dict[int, str] = {}
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader)
        for row in reader:
            mapping[int(row[0])] = row[1].split("|")[2] if len(row[1].split("|")) > 2 else ""
    return mapping


def preparar_entorno(tamano, db_config):
    data_dir = BASE_DIR / "Multimodal" / "Data"
    carpeta_respaldo = data_dir / str(tamano)
    archivo_csv = carpeta_respaldo / f"descriptors_dump_{tamano}.csv"
    archivo_pkl = carpeta_respaldo / f"visual_codebook_{tamano}.pkl"

    if carpeta_respaldo.exists() and archivo_csv.exists() and archivo_pkl.exists():
        print(f"\nArchivos encontrados para tamaño {tamano}. Actualizando PostgreSQL...")
        from Backend.Multimodal.Offline.Persistence import PersistenceManager
        
        print(f"  Recreando tabla PostgreSQL...")
        pm = PersistenceManager(n_documents=tamano, **db_config)
        pm.create_tables()
        
        print("  Inyectando datos del CSV a PostgreSQL...")
        filas = pm.load_csv(str(archivo_csv))
        pm.close()
        print(f"  Base de datos lista ({filas} filas cargadas).")
        return True
    else:
        print(f"\nNo se encontró respaldo para tamaño {tamano}. Construyendo índice desde cero...")
        import subprocess, sys
        try:
            subprocess.run(
                [sys.executable, "-m", "Backend.Multimodal.Offline.Orquestador", "--dataset-size", str(tamano), "--processes", "4"],
                check=True
            )
            print(f"  Construcción offline completada con éxito para tamaño {tamano}.")
            return True
        except subprocess.CalledProcessError:
            print(f"\nERROR: Falló la construcción offline para el tamaño {tamano}.")
            return False

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
            cur.execute("SELECT pg_relation_size('idx_descriptors_texto_vector_gist')")
            pg_gist = cur.fetchone()[0]
            cur.execute("""
                SELECT COALESCE(pg_relation_size(c.reltoastrelid), 0)
                FROM pg_class c WHERE c.relname = 'descriptors'
            """)
            pg_toast = cur.fetchone()[0]
            cur.execute("SELECT pg_relation_size('idx_descriptors_image_histogram_ivfflat')")
            pg_ivfflat = cur.fetchone()[0]
            cur.execute("SELECT pg_relation_size('idx_descriptors_image_histogram_hnsw')")
            pg_hnsw = cur.fetchone()[0]
        conn.close()
    except Exception:
        pg_gin = pg_gist = pg_toast = pg_ivfflat = pg_hnsw = 0

    codebook_bytes = (data_dir / f"visual_codebook_{tamano}.pkl").stat().st_size

    return {
        "tamano": tamano,
        "spimi_texto_mb": round(spimi_texto_bytes / (1024 * 1024), 2),
        "gin_mb": round(pg_gin / (1024 * 1024), 2),
        "gist_mb": round(pg_gist / (1024 * 1024), 2),
        "spimi_imagen_mb": round(spimi_imagen_bytes / (1024 * 1024), 2),
        "ivfflat_mb": round(pg_ivfflat / (1024 * 1024), 2),
        "hnsw_mb": round(pg_hnsw / (1024 * 1024), 2),
    }

def calcular_recall_subcategory(result, sub_map: dict[int, str], k: int) -> float:
    if result and isinstance(result[0], dict):
        doc_ids = [r["doc_id"] for r in result]
    else:
        doc_ids = result
    if not doc_ids:
        return 0.0
    target = sub_map.get(doc_ids[0])
    if not target:
        return 0.0
    matches = sum(1 for doc_id in doc_ids[:k] if sub_map.get(doc_id) == target)
    return matches / k


def busqueda_gin_texto(conn, texto):
    query_explicar = """
        EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) 
        SELECT doc_id FROM descriptors 
        WHERE texto_vector @@ plainto_tsquery('english', %s) 
        ORDER BY ts_rank(texto_vector, plainto_tsquery('english', %s)) DESC 
        LIMIT 50;
    """
    with conn.cursor() as cur:
        cur.execute("SET LOCAL enable_indexscan = OFF;")
        cur.execute("SET LOCAL enable_indexonlyscan = OFF;")
        cur.execute("SET LOCAL enable_seqscan = OFF;")
        cur.execute(query_explicar, (texto, texto))
        explicacion = cur.fetchone()[0][0]
        io_blocks = explicacion.get("Plan", {}).get("Shared Read Blocks", 0)

    query_real = """
        SELECT doc_id FROM descriptors 
        WHERE texto_vector @@ plainto_tsquery('english', %s) 
        ORDER BY ts_rank(texto_vector, plainto_tsquery('english', %s)) DESC 
        LIMIT 50;
    """
    with conn.cursor() as cur:
        cur.execute("SET LOCAL enable_indexscan = OFF;")
        cur.execute("SET LOCAL enable_indexonlyscan = OFF;")
        cur.execute("SET LOCAL enable_seqscan = OFF;")
        cur.execute(query_real, (texto, texto))
        return [row[0] for row in cur.fetchall()], io_blocks


def busqueda_ivfflat_imagen(conn, orquestador, ruta_imagen):
    vector = orquestador._image_histogram(str(ruta_imagen))
    vector_string = f"[{','.join(map(str, vector))}]"

    query_explicar = """
        EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) 
        SELECT doc_id FROM descriptors 
        ORDER BY image_histogram <=> %s::vector 
        LIMIT 50;
    """
    with conn.cursor() as cur:
        cur.execute("SET LOCAL enable_seqscan = OFF;")
        cur.execute(query_explicar, (vector_string,))
        explicacion = cur.fetchone()[0][0]
        io_blocks = explicacion.get("Plan", {}).get("Shared Read Blocks", 0)

    query_real = """
        SELECT doc_id FROM descriptors 
        ORDER BY image_histogram <=> %s::vector 
        LIMIT 50;
    """
    with conn.cursor() as cur:
        cur.execute("SET LOCAL enable_seqscan = OFF;")
        cur.execute(query_real, (vector_string,))
        return [row[0] for row in cur.fetchall()], io_blocks


def busqueda_gist_texto(conn, texto):
    query_explicar = """
        EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) 
        SELECT doc_id FROM descriptors 
        WHERE texto_vector @@ plainto_tsquery('english', %s) 
        ORDER BY ts_rank(texto_vector, plainto_tsquery('english', %s)) DESC 
        LIMIT 50;
    """
    with conn.cursor() as cur:
        cur.execute("SET LOCAL enable_bitmapscan = OFF;")
        cur.execute("SET LOCAL enable_seqscan = OFF;")
        cur.execute(query_explicar, (texto, texto))
        explicacion = cur.fetchone()[0][0]
        io_blocks = explicacion.get("Plan", {}).get("Shared Read Blocks", 0)

    query_real = """
        SELECT doc_id FROM descriptors 
        WHERE texto_vector @@ plainto_tsquery('english', %s) 
        ORDER BY ts_rank(texto_vector, plainto_tsquery('english', %s)) DESC 
        LIMIT 50;
    """
    with conn.cursor() as cur:
        cur.execute("SET LOCAL enable_bitmapscan = OFF;")
        cur.execute("SET LOCAL enable_seqscan = OFF;")
        cur.execute(query_real, (texto, texto))
        return [row[0] for row in cur.fetchall()], io_blocks


def busqueda_hnsw_imagen(conn, orquestador, ruta_imagen):
    vector = orquestador._image_histogram(str(ruta_imagen))
    vector_string = f"[{','.join(map(str, vector))}]"

    query_explicar = """
        EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) 
        SELECT doc_id FROM descriptors 
        ORDER BY image_histogram <=> %s::vector 
        LIMIT 50;
    """
    with conn.cursor() as cur:
        cur.execute("SET LOCAL enable_seqscan = OFF;")
        cur.execute(query_explicar, (vector_string,))
        explicacion = cur.fetchone()[0][0]
        io_blocks = explicacion.get("Plan", {}).get("Shared Read Blocks", 0)

    query_real = """
        SELECT doc_id FROM descriptors 
        ORDER BY image_histogram <=> %s::vector 
        LIMIT 50;
    """
    with conn.cursor() as cur:
        cur.execute("SET LOCAL enable_seqscan = OFF;")
        cur.execute(query_real, (vector_string,))
        return [row[0] for row in cur.fetchall()], io_blocks


def busqueda_lineal_texto(conn, orquestador, texto):
    histogram = orquestador._text_histogram(texto)
    vector_string = f"[{','.join(map(str, histogram))}]"

    old_autocommit = conn.autocommit
    conn.autocommit = False
    cur = conn.cursor()
    try:
        cur.execute("SET LOCAL enable_indexscan = OFF;")
        cur.execute("SET LOCAL enable_indexonlyscan = OFF;")
        cur.execute("SET LOCAL enable_bitmapscan = OFF;")
        cur.execute("""
            SELECT doc_id FROM descriptors
            WHERE text_histogram IS NOT NULL
            ORDER BY text_histogram <=> %s::vector
            LIMIT 50;
        """, (vector_string,))
        results = [row[0] for row in cur.fetchall()]
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.autocommit = old_autocommit
    return results


def busqueda_lineal_imagen(conn, orquestador, ruta_imagen):
    vector = orquestador._image_histogram(str(ruta_imagen))
    vector_string = f"[{','.join(map(str, vector))}]"

    old_autocommit = conn.autocommit
    conn.autocommit = False
    cur = conn.cursor()
    try:
        cur.execute("SET LOCAL enable_indexscan = OFF;")
        cur.execute("SET LOCAL enable_indexonlyscan = OFF;")
        cur.execute("SET LOCAL enable_bitmapscan = OFF;")
        cur.execute("""
            SELECT doc_id FROM descriptors
            WHERE image_histogram IS NOT NULL
            ORDER BY image_histogram <=> %s::vector
            LIMIT 50;
        """, (vector_string,))
        results = [row[0] for row in cur.fetchall()]
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.autocommit = old_autocommit
    return results


def _linear_tfidf_scores(query_hist, word_idf, doc_norm, db_rows, k):
    qw_map = {}
    qn_sq = 0.0
    for cid in np.nonzero(query_hist)[0]:
        tf = float(query_hist[cid])
        idf = word_idf.get(cid)
        if idf is None or idf == 0.0:
            continue
        w = tf * idf
        qw_map[cid] = w
        qn_sq += w * w
    qn = math.sqrt(qn_sq) if qn_sq > 0 else 1.0
    if not qw_map:
        return []

    scores = {}
    for doc_id, hvec in db_rows:
        if not isinstance(hvec, np.ndarray):
            hvec = np.array(hvec, dtype=np.float32) if hvec is not None else np.zeros(len(query_hist), dtype=np.float32)
        d_norm = doc_norm.get(doc_id, 1.0) or 1.0
        acc = 0.0
        for cid, qw in qw_map.items():
            tf = float(hvec[cid]) if cid < len(hvec) else 0.0
            if tf > 0:
                acc += qw * (tf * (word_idf.get(cid, 0.0) or 0.0))
        s = acc / (d_norm * qn)
        if s > 0:
            scores[doc_id] = s

    top = sorted(scores.items(), key=lambda x: -x[1])[:k]
    return [doc_id for doc_id, _ in top]


def busqueda_lineal_tfidf_texto(conn, orquestador, texto, tamano):
    qhist = orquestador._text_histogram(texto)
    d = BASE_DIR / "Multimodal" / "Data" / str(tamano)
    with open(d / f"text_word_idf_{tamano}.pkl", "rb") as f:
        widf = pickle.load(f)
    with open(d / f"text_doc_norm_{tamano}.pkl", "rb") as f:
        dnorm = pickle.load(f)
    with conn.cursor() as cur:
        cur.execute("SELECT doc_id, text_histogram FROM descriptors WHERE text_histogram IS NOT NULL")
        rows = cur.fetchall()
    return _linear_tfidf_scores(qhist, widf, dnorm, rows, TOP_K)


def busqueda_lineal_tfidf_imagen(conn, orquestador, ruta_imagen, tamano):
    qhist = orquestador._image_histogram(str(ruta_imagen))
    d = BASE_DIR / "Multimodal" / "Data" / str(tamano)
    with open(d / f"image_word_idf_{tamano}.pkl", "rb") as f:
        widf = pickle.load(f)
    with open(d / f"image_doc_norm_{tamano}.pkl", "rb") as f:
        dnorm = pickle.load(f)
    with conn.cursor() as cur:
        cur.execute("SELECT doc_id, image_histogram FROM descriptors WHERE image_histogram IS NOT NULL")
        rows = cur.fetchall()
    return _linear_tfidf_scores(qhist, widf, dnorm, rows, TOP_K)


def ejecutar_benchmark():
    from Backend.Multimodal.Online.Orquestador import OnlineOrchestrator

    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = True
    register_vector(conn)
    resultados = []
    resultados_disco = []

    sub_map = load_subcategory_map(STYLES_CSV)

    for tamano in TAMAÑOS:
        if not preparar_entorno(tamano, DB_CONFIG):
            continue
        
        orquestador = OnlineOrchestrator(db_config=DB_CONFIG, n_documents=tamano)
        resultados_disco.append(medir_disco(tamano))
        
        print(f"\nEvaluando Textos (Tamaño {tamano})")
        for q in QUERIES_TEXTO:
            orquestador.reset_io_counters()
            ini = time.perf_counter()
            res_custom = orquestador.search_text(q, k=TOP_K)
            lat_custom = time.perf_counter() - ini
            io_spimi = orquestador.io_metrics()["disk_reads"]

            ini = time.perf_counter()
            res_pg, io_pg = busqueda_gin_texto(conn, q)
            lat_pg = time.perf_counter() - ini

            ini = time.perf_counter()
            res_gist, io_gist = busqueda_gist_texto(conn, q)
            lat_gist = time.perf_counter() - ini

            ini = time.perf_counter()
            res_tfidf = busqueda_lineal_tfidf_texto(conn, orquestador, q, tamano)
            lat_tfidf = time.perf_counter() - ini

            resultados.append({"tamano": tamano, "tipo": "Texto", "query": q, "motor": "Custom_SPIMI", "latencia": lat_custom, "throughput_qps": 1.0 / lat_custom if lat_custom > 0 else 0.0, "io": io_spimi, "recall": calcular_recall_subcategory(res_custom, sub_map, TOP_K)})
            resultados.append({"tamano": tamano, "tipo": "Texto", "query": q, "motor": "Postgres_GIN", "latencia": lat_pg, "throughput_qps": 1.0 / lat_pg if lat_pg > 0 else 0.0, "io": io_pg, "recall": calcular_recall_subcategory(res_pg, sub_map, TOP_K)})
            resultados.append({"tamano": tamano, "tipo": "Texto", "query": q, "motor": "Postgres_GiST", "latencia": lat_gist, "throughput_qps": 1.0 / lat_gist if lat_gist > 0 else 0.0, "io": io_gist, "recall": calcular_recall_subcategory(res_gist, sub_map, TOP_K)})
            resultados.append({"tamano": tamano, "tipo": "Texto", "query": q, "motor": "Linear_TFIDF", "latencia": lat_tfidf, "throughput_qps": 1.0 / lat_tfidf if lat_tfidf > 0 else 0.0, "io": 0, "recall": calcular_recall_subcategory(res_tfidf, sub_map, TOP_K)})

        print(f"\nEvaluando Imágenes (Tamaño {tamano})")
        for ruta_img in QUERY_IMAGENES:
            nombre_archivo = ruta_img.name

            orquestador.reset_io_counters()
            ini = time.perf_counter()
            res_custom = orquestador.search_image(str(ruta_img), k=TOP_K)
            lat_custom = time.perf_counter() - ini
            io_spimi = orquestador.io_metrics()["disk_reads"]

            ini = time.perf_counter()
            res_pg, io_pg = busqueda_ivfflat_imagen(conn, orquestador, ruta_img)
            lat_pg = time.perf_counter() - ini

            ini = time.perf_counter()
            res_hnsw, io_hnsw = busqueda_hnsw_imagen(conn, orquestador, ruta_img)
            lat_hnsw = time.perf_counter() - ini

            ini = time.perf_counter()
            res_tfidf = busqueda_lineal_tfidf_imagen(conn, orquestador, ruta_img, tamano)
            lat_tfidf = time.perf_counter() - ini

            resultados.append({"tamano": tamano, "tipo": "Imagen", "query": "IMG_" + nombre_archivo, "motor": "Custom_SPIMI", "latencia": lat_custom, "throughput_qps": 1.0 / lat_custom if lat_custom > 0 else 0.0, "io": io_spimi, "recall": calcular_recall_subcategory(res_custom, sub_map, TOP_K)})
            resultados.append({"tamano": tamano, "tipo": "Imagen", "query": "IMG_" + nombre_archivo, "motor": "Postgres_IVFFlat", "latencia": lat_pg, "throughput_qps": 1.0 / lat_pg if lat_pg > 0 else 0.0, "io": io_pg, "recall": calcular_recall_subcategory(res_pg, sub_map, TOP_K)})
            resultados.append({"tamano": tamano, "tipo": "Imagen", "query": "IMG_" + nombre_archivo, "motor": "Postgres_HNSW", "latencia": lat_hnsw, "throughput_qps": 1.0 / lat_hnsw if lat_hnsw > 0 else 0.0, "io": io_hnsw, "recall": calcular_recall_subcategory(res_hnsw, sub_map, TOP_K)})
            resultados.append({"tamano": tamano, "tipo": "Imagen", "query": "IMG_" + nombre_archivo, "motor": "Linear_TFIDF", "latencia": lat_tfidf, "throughput_qps": 1.0 / lat_tfidf if lat_tfidf > 0 else 0.0, "io": 0, "recall": calcular_recall_subcategory(res_tfidf, sub_map, TOP_K)})

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
        writer = csv.DictWriter(f, fieldnames=["tamano", "spimi_texto_mb", "gin_mb", "gist_mb", "spimi_imagen_mb", "ivfflat_mb", "hnsw_mb"])
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

    with open(resultados_dir / "promedios.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["tamano", "motor", "tipo", "latencia_prom", "throughput_qps_prom", "io_prom", "recall_prom"])
        for (tamano, motor, tipo), vals in sorted(proms.items()):
            w.writerow([tamano, motor, tipo, vals.get("latencia", ""), vals.get("throughput_qps", ""), vals.get("io", ""), vals.get("recall", "")])
    print(f"  Promedios guardados en: promedios.csv")

    sizes = sorted(set(r["tamano"] for r in resultados))

    configs = [
        ("Texto", [
            ("Custom_SPIMI", "Texto", "SPIMI Texto", "o--", "tab:blue"),
            ("Postgres_GIN", "Texto", "PostgreSQL GIN", "o-", "tab:green"),
            ("Postgres_GiST", "Texto", "PostgreSQL GiST", "^-", "tab:purple"),
            ("Linear_TFIDF", "Texto", "Linear TF-IDF", "v:", "tab:cyan"),
        ]),
        ("Imagen", [
            ("Custom_SPIMI", "Imagen", "SPIMI Imagen", "s--", "tab:orange"),
            ("Postgres_IVFFlat", "Imagen", "PostgreSQL IVFFlat", "s-", "tab:red"),
            ("Postgres_HNSW", "Imagen", "PostgreSQL HNSW", "D-", "tab:brown"),
            ("Linear_TFIDF", "Imagen", "Linear TF-IDF", "P:", "tab:cyan"),
        ]),
    ]

    for metrica, ylabel, titulo_base in [
        ("latencia", "Latencia (s)", "Latencia"),
        ("throughput_qps", "QPS", "Throughput"),
        ("io", "Bloques I/O", "Lecturas de Disco"),
        ("recall", "Recall", "Recall por Subcategoría"),
    ]:
        for tipo, series in configs:
            fig, ax = plt.subplots(figsize=(8, 5))
            for motor, t, label, ls, color in series:
                vals = []
                for s in sizes:
                    key = (s, motor, t)
                    v = proms.get(key, {}).get(metrica, None)
                    vals.append(v if v is not None else 0)
                ax.plot(sizes, vals, ls, color=color, label=label, linewidth=2, markersize=8)
            ax.set_xlabel("Volumen del Dataset (documentos)")
            ax.set_ylabel(ylabel)
            ax.set_title(f"{titulo_base} - {tipo}")
            ax.legend()
            ax.grid(True, linestyle=":", alpha=0.7)
            fig.tight_layout()
            safe = metrica.replace("/", "_")
            fig.savefig(resultados_dir / f"grafico_{safe}_{tipo.lower()}.png", dpi=150)
            plt.close(fig)
            print(f"  Gráfico guardado: grafico_{safe}_{tipo.lower()}.png")


def generar_grafico_disco(resultados_disco):
    resultados_dir = BASE_DIR / "Benchmark" / "resultados"
    sizes = [r["tamano"] for r in resultados_disco]

    spimi_texto = [r["spimi_texto_mb"] for r in resultados_disco]
    gin = [r["gin_mb"] for r in resultados_disco]
    gist = [r["gist_mb"] for r in resultados_disco]
    spimi_imagen = [r["spimi_imagen_mb"] for r in resultados_disco]
    ivfflat = [r["ivfflat_mb"] for r in resultados_disco]
    hnsw = [r["hnsw_mb"] for r in resultados_disco]

    x = range(len(sizes))
    width = 0.13

    fig, ax = plt.subplots(figsize=(11, 5))
    ax.bar([i - 2.5 * width for i in x], spimi_texto, width, label="SPIMI Texto", color="tab:blue")
    ax.bar([i - 1.5 * width for i in x], gin, width, label="PostgreSQL GIN", color="tab:green")
    ax.bar([i - 0.5 * width for i in x], gist, width, label="PostgreSQL GiST", color="tab:purple")
    ax.bar([i + 0.5 * width for i in x], spimi_imagen, width, label="SPIMI Imagen", color="tab:orange")
    ax.bar([i + 1.5 * width for i in x], ivfflat, width, label="PostgreSQL IVFFlat", color="tab:red")
    ax.bar([i + 2.5 * width for i in x], hnsw, width, label="PostgreSQL HNSW", color="tab:brown")

    ax.set_xlabel("Volumen del Dataset (documentos)")
    ax.set_ylabel("Tamaño en Disco (MB)")
    ax.set_title("Uso de Disco por Índice")
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