import psycopg2
from psycopg2.extras import execute_values

class PersistenceManager:

    def __init__(self, host="localhost", port="5432", database="multimodal", user="postgres", password="123456"):
        
        self.connection = psycopg2.connect(
            host=host,
            port=port,
            database=database,
            user=user,
            password=password
        )

        self.cursor = self.connection.cursor()
    
    def create_tables(self):

        self.cursor.execute("""
            CREATE EXTENSION IF NOT EXISTS vector;

            DROP TABLE IF EXISTS descriptors;

            CREATE TABLE descriptors (
                doc_id INTEGER PRIMARY KEY,
                url TEXT,
                texto TEXT,
                texto_vector TSVECTOR GENERATED ALWAYS AS (
                    to_tsvector('english', coalesce(texto, ''))
                ) STORED,
                image_histogram VECTOR(128)
            );
        """)

        self.connection.commit()

# hablar con el orquestador para definir los nombres de las columnas
    def insert_document(self, df):

        rows = [
            (int(row.doc_id), row.url, row.texto)
            for row in df.itertuples(index=False)
        ]

        execute_values(
            self.cursor,
            """
            INSERT INTO descriptors (doc_id, url, texto)
            VALUES %s
            ON CONFLICT (doc_id) DO UPDATE SET
                url = EXCLUDED.url,
                texto = EXCLUDED.texto;
            """,
            rows,
        )

        self.connection.commit()

    def update_histogram(self, doc_id, histogram):
        self.cursor.execute(
            """
            UPDATE descriptors
            SET image_histogram = %s
            WHERE doc_id = %s;
            """,
            (histogram, doc_id),
        )
        self.connection.commit()

    def close(self):
        self.cursor.close()
        self.connection.close()