import dagster as dg
from etl.resources import PostgresResource, EmbeddingsResource

@dg.asset
def embedded_docs(
    chunked_docs: list[dict],
    embeddings: EmbeddingsResource
) -> list[dict]:
    """Generate embeddings for each chunk."""
    client = embeddings.get_client()
    
    for chunk in chunked_docs:
        chunk["embedding"] = client.embed_query(chunk["content"])
    
    return chunked_docs

@dg.asset
def stored_docs(
    embedded_docs: list[dict],
    database: PostgresResource
) -> int:
    """Store embeddings in pgvector."""
    with database.get_connection() as conn:
        cur = conn.cursor()
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS k8s_docs (
                id SERIAL PRIMARY KEY,
                resource TEXT,
                field_path TEXT,
                content TEXT,
                embedding vector(1536)
            )
        """)
        
        cur.execute("TRUNCATE k8s_docs")
        
        for doc in embedded_docs:
            cur.execute(
                "INSERT INTO k8s_docs (resource, field_path, content, embedding) VALUES (%s, %s, %s, %s)",
                (doc["resource"], doc["field_path"], doc["content"], doc["embedding"])
            )
        
        conn.commit()
    
    return len(embedded_docs)