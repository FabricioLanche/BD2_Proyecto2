from pathlib import Path

import psycopg2
import logging
from pgvector.psycopg2 import register_vector

logger = logging.getLogger(__name__)

class PersistenceManager:

    def __init__(
        self, n_documents: int, 
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5433"),
        database=os.getenv("DB_NAME", "multimodal"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "123456")
    ):
        import os
        self.n_documents = n_documents
        base = Path(__file__).resolve().parent.parent / "Data"
        self.data_dir = base / str(n_documents) if n_documents is not None else base
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.connection = psycopg2.connect(
            host=host,
            port=port,
            database=database,
            user=user,
            password=password,
        )

        with self.connection.cursor() as cursor:
            cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        self.connection.commit()

        register_vector(self.connection)

    def _get_cursor(self):
        return self.connection.cursor()
    
    def create_tables(self, histogram_dim: int = 512):
        with self._get_cursor() as cursor:
            try:

                cursor.execute(f"""
                    CREATE EXTENSION IF NOT EXISTS vector;

                    DROP TABLE IF EXISTS descriptors;

                    CREATE TABLE descriptors (
                        doc_id INTEGER PRIMARY KEY,
                        url TEXT,
                        texto TEXT,
                        texto_vector TSVECTOR GENERATED ALWAYS AS (
                            to_tsvector('english', coalesce(texto, ''))
                        ) STORED,
                        image_histogram VECTOR({int(histogram_dim)})
                    );

                CREATE INDEX idx_descriptors_texto_vector_gin
                ON descriptors
                USING GIN (texto_vector);

                CREATE INDEX idx_descriptors_texto_vector_gist
                ON descriptors
                USING GiST (texto_vector);

                CREATE INDEX idx_descriptors_image_histogram_hnsw
                ON descriptors
                USING hnsw (image_histogram vector_l2_ops);
            
                CREATE INDEX idx_descriptors_image_histogram_ivfflat
                ON descriptors
                USING ivfflat (image_histogram vector_l2_ops)
                WITH (lists = 100);
                """)

                self.connection.commit()
            except Exception as e:
                self.connection.rollback()
                logger.error(f"Error creando tablas: {e}")
                raise

    def add_text_histogram_column(self, dim: int) -> None:
        with self._get_cursor() as cursor:
            try:
                cursor.execute(f"""
                    ALTER TABLE descriptors
                    ADD COLUMN IF NOT EXISTS text_histogram VECTOR({int(dim)});
                CREATE INDEX IF NOT EXISTS idx_descriptors_text_histogram_hnsw
                ON descriptors
                USING hnsw (text_histogram vector_l2_ops);
                CREATE INDEX IF NOT EXISTS idx_descriptors_text_histogram_ivfflat
                ON descriptors
                USING ivfflat (text_histogram vector_l2_ops)
                WITH (lists = 100);
                """)
                self.connection.commit()
            except Exception as e:
                self.connection.rollback()
                logger.error(f"Error adding text_histogram column: {e}")
                raise
            
    def insert_document(self, doc_id: int, url: str, texto: str) -> None:
        with self._get_cursor() as cursor:
            try:
                cursor.execute("""
                    INSERT INTO descriptors (doc_id, url, texto)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (doc_id) DO UPDATE SET
                        url = CASE WHEN EXCLUDED.url != '' THEN EXCLUDED.url ELSE descriptors.url END,
                        texto = CASE WHEN EXCLUDED.texto != '' THEN EXCLUDED.texto ELSE descriptors.texto END;
                """, (int(doc_id), url, texto))
                self.connection.commit()
            except Exception as e:
                self.connection.rollback()
                logger.error(f"Error en insert_document doc_id={doc_id}: {e}")
                raise

    def batch_insert_documents(self, docs: list[tuple[int, str, str]]) -> None:
        with self._get_cursor() as cursor:
            try:
                cursor.executemany("""
                    INSERT INTO descriptors (doc_id, url, texto)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (doc_id) DO UPDATE SET
                        url = CASE WHEN EXCLUDED.url != '' THEN EXCLUDED.url ELSE descriptors.url END,
                        texto = CASE WHEN EXCLUDED.texto != '' THEN EXCLUDED.texto ELSE descriptors.texto END;
                """, [(int(doc_id), url, texto) for doc_id, url, texto in docs])
                self.connection.commit()
            except Exception as e:
                self.connection.rollback()
                logger.error(f"Error en batch_insert_documents: {e}")
                raise

    def insert_image_histogram(self, doc_id: int, histogram) -> None:
        with self._get_cursor() as cursor:
            try:
                cursor.execute("""
                    UPDATE descriptors SET image_histogram = %s::vector
                    WHERE doc_id = %s;
                """, (histogram.tolist(), int(doc_id)))
                self.connection.commit()
            except Exception as e:
                self.connection.rollback()
                logger.error(f"Error en insert_image_histogram doc_id={doc_id}: {e}")
                raise

    def insert_text_histogram(self, doc_id: int, histogram) -> None:
        with self._get_cursor() as cursor:
            try:
                cursor.execute("""
                    UPDATE descriptors SET text_histogram = %s::vector
                    WHERE doc_id = %s;
                """, (histogram.tolist(), int(doc_id)))
                self.connection.commit()
            except Exception as e:
                self.connection.rollback()
                logger.error(f"Error en insert_text_histogram doc_id={doc_id}: {e}")
                raise

    def dump_csv(self) -> str:
        filename = str(self.data_dir / f"descriptors_dump_{self.n_documents}.csv")

        with open(filename, "w", encoding="utf-8") as f:
            with self._get_cursor() as cursor:
                cursor.copy_expert(
                    "COPY descriptors TO STDOUT WITH CSV HEADER DELIMITER ','",
                    f,
                )

        logger.info("Dump exportado a %s", filename)
        return filename

    def load_csv(self, filename: str) -> int:
        with self._get_cursor() as cursor:
            with open(filename, "r", encoding="utf-8") as f:
                cursor.copy_expert(
                    "COPY descriptors FROM STDIN WITH CSV HEADER DELIMITER ','",
                    f,
                )
            self.connection.commit()
            count = cursor.rowcount

        logger.info("Cargadas %d filas desde %s", count, filename)
        return count

    def close(self):
        if self.connection and not self.connection.closed:
            self.connection.close()