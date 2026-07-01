import psycopg2
import logging
from psycopg2.extras import execute_values
from pgvector.psycopg2 import register_vector

logger = logging.getLogger(__name__)

class PersistenceManager:

    def __init__(self, host="localhost", port="5432", database="multimodal", user="postgres", password="123456"):
        
        self.connection = psycopg2.connect(
            host=host,
            port=port,
            database=database,
            user=user,
            password=password
        )

        # la extension debe existir ANTES de register_vector (si no, falla con
        # 'vector type not found in the database')
        with self.connection.cursor() as cursor:
            cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        self.connection.commit()

        register_vector(self.connection)

    def _get_cursor(self):
        return self.connection.cursor()
    
    def create_tables(self, histogram_dim: int = 128):
        # histogram_dim = k del codebook visual; el orquestador lo pasa
        # tras construir el codebook para que la columna calce con el histograma.

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
                """)

                self.connection.commit()
            except Exception as e:
                self.connection.rollback()
                logger.error(f"Error creando tablas: {e}")
                raise

# hablar con el orquestador para definir los nombres de las columnas
    def insert_document(self, df, page_size = 5000):

        rows = [
            (int(row.doc_id), row.url, row.texto)
            for row in df.itertuples(index=False)
        ]

        with self._get_cursor() as cursor:
            try:
                execute_values(
                    cursor,
                    """
                    INSERT INTO descriptors (doc_id, url, texto)
                    VALUES %s
                    ON CONFLICT (doc_id) DO UPDATE SET
                        url = EXCLUDED.url,
                        texto = EXCLUDED.texto;
                    """,
                    rows,
                    page_size = page_size,
                )
                self.connection.commit()
                logger.info(f"Insertados/actualizados {len(rows)} documentos.")
            except Exception as e:
                self.connection.rollback()
                logger.error(f"Error en insert_document: {e}")
                raise

    def update_histograms(self, histograms, page_size=5000):

        rows = [
            (int(doc_id), histogram)
            for doc_id, histogram in histograms
        ]

        with self._get_cursor() as cursor:
            try: 
                execute_values(
                    cursor,
                    """
                    UPDATE descriptors AS d
                    SET image_histogram = data.image_histogram::vector
                    FROM (VALUES %s) AS data(doc_id, image_histogram)
                    WHERE d.doc_id = data.doc_id::integer;
                    """,
                    rows,
                    page_size=page_size
                )
                self.connection.commit()
                logger.info(f"Histogramas actualizados: {len(rows)}")
            except Exception as e:
                self.connection.rollback()
                logger.error(f"Error en update_histograms: {e}")
                raise

    def close(self):
        if self.connection and not self.connection.closed:
            self.connection.close()