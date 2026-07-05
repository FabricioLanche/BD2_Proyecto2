"""Initialize PostgreSQL database from CSV dump if empty."""
import os
import pickle
import logging
import time
from pathlib import Path

import psycopg2
from pgvector.psycopg2 import register_vector

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("init_db")

DB_CONFIG = {
    "host":     os.getenv("DB_HOST", "localhost"),
    "port":     os.getenv("DB_PORT", "5432"),
    "database": os.getenv("DB_NAME", "multimodal"),
    "user":     os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", "123456"),
}
DATASET_SIZE = int(os.getenv("DATASET_SIZE", "44446"))
DATA_DIR = Path("/app/Backend/Multimodal/Data") / str(DATASET_SIZE)
CSV_PATH = DATA_DIR / f"descriptors_dump_{DATASET_SIZE}.csv"
VCODEBOOK_PATH = DATA_DIR / f"visual_codebook_{DATASET_SIZE}.pkl"


def histogram_dim_from_codebook() -> int:
    with open(VCODEBOOK_PATH, "rb") as f:
        centers = pickle.load(f)
    return centers.shape[0]


def table_exists(cursor) -> bool:
    cursor.execute(
        "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name='descriptors')"
    )
    return cursor.fetchone()[0]


def table_has_rows(cursor) -> bool:
    cursor.execute("SELECT COUNT(*) FROM descriptors")
    return cursor.fetchone()[0] > 0


def create_table(cursor, dim: int) -> None:
    cursor.execute("DROP TABLE IF EXISTS descriptors;")

    cursor.execute(f"""
        CREATE TABLE descriptors (
            doc_id INTEGER PRIMARY KEY,
            url TEXT,
            texto TEXT,
            texto_vector TSVECTOR GENERATED ALWAYS AS (
                to_tsvector('english', coalesce(texto, ''))
            ) STORED,
            image_histogram VECTOR({dim})
        )
    """)

    cursor.execute("""
        CREATE INDEX idx_descriptors_texto_vector_gin
        ON descriptors USING GIN (texto_vector)
    """)
    cursor.execute("""
        CREATE INDEX idx_descriptors_texto_vector_gist
        ON descriptors USING GiST (texto_vector)
    """)
    cursor.execute("""
        CREATE INDEX idx_descriptors_image_histogram_hnsw
        ON descriptors USING hnsw (image_histogram vector_l2_ops)
    """)
    cursor.execute(f"""
        CREATE INDEX idx_descriptors_image_histogram_ivfflat
        ON descriptors USING ivfflat (image_histogram vector_l2_ops)
        WITH (lists = 100)
    """)

    logger.info("Table 'descriptors' created (dim=%d).", dim)


def load_csv(conn, path: Path) -> int:
    with conn.cursor() as cur:
        with open(path, "r", encoding="utf-8") as f:
            cur.copy_expert(
                "COPY descriptors FROM STDIN WITH CSV HEADER DELIMITER ','",
                f,
            )
        conn.commit()
        count = cur.rowcount
    logger.info("Loaded %d rows from %s", count, path.name)
    return count


def main() -> None:
    if not DATA_DIR.is_dir():
        logger.info("Data directory '%s' does not exist — skipping DB init.", DATA_DIR)
        return
    if not CSV_PATH.is_file():
        logger.info("CSV dump '%s' not found — skipping DB init.", CSV_PATH)
        return

    logger.info("Connecting to PostgreSQL at %s:%s ...", DB_CONFIG["host"], DB_CONFIG["port"])
    for attempt in range(30):
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            break
        except psycopg2.OperationalError:
            if attempt == 29:
                raise
            logger.info("DB not ready yet, retrying in 1s (attempt %d/30)...", attempt + 1)
            time.sleep(1)

    conn.autocommit = True

    with conn.cursor() as cur:
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    register_vector(conn)

    needs_load = False
    with conn.cursor() as cur:
        if table_exists(cur):
            if table_has_rows(cur):
                logger.info("Table 'descriptors' already has data — nothing to do.")
                conn.close()
                return
            logger.info("Table 'descriptors' exists but is empty — dropping and recreating.")
        dim = histogram_dim_from_codebook()
        create_table(cur, dim)
        needs_load = True

    conn.autocommit = False

    if needs_load:
        load_csv(conn, CSV_PATH)

    conn.close()
    logger.info("Database initialization complete.")


if __name__ == "__main__":
    main()
