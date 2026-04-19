import os
from models import UserQuery, Source
from etl.resources import PostgresResource,EmbeddingsResource
from psycopg2.extras import RealDictCursor

database = PostgresResource(
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", "5432")),
            user=os.getenv("DB_USER", "dev"),
            password=os.getenv("DB_PASSWORD", "devpass"),
            dbname=os.getenv("DB_NAME", "kubebot"),
        )
embeddings = EmbeddingsResource(api_key=os.getenv("OPENAI_API_KEY"))

def map_source(k8_doc: dict):
    return Source(
        doc_path = k8_doc['field_path'],
        title = k8_doc['resource'],
        relevant_info = k8_doc['content']
    )

def search_db(query: UserQuery, k:int = 3)->list[Source]:
    question_embedding = embeddings.get_client().embed_query(query.question)
    db_results = []
    with database.get_connection() as conn:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute('''
            SELECT id, resource, field_path, content
            FROM k8s_docs
            ORDER BY embedding <=> %s::vector ASC
            LIMIT %s
        ''', (question_embedding, k))

        related_docs = cur.fetchall()

        db_results: list[Source] = list(map(map_source,related_docs))
    return db_results
