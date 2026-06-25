import psycopg2
from psycopg2.extras import execute_values

class PersistenceManager:

    def __init__(self, host="localhost", port="5432", database="multimodal", user="postgres", password="123456"):
        
        self.connection = psycopg2.connect(
            self,
            host=host,
            port=port,
            database=database,
            user=user,
            password=password
        )
        
        self.cursor = self.connection.cursor()
    
    def create_tables(self):

        self.cur.execute("""
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

        self.conn.commit()