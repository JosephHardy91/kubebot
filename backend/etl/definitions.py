import dagster as dg
from etl.assets.extract import k8s_resources, k8s_explain_docs
from etl.assets.transform import chunked_docs
from etl.assets.load import embedded_docs, stored_docs
from etl.resources import PostgresResource, EmbeddingsResource
import os
from dotenv import load_dotenv
load_dotenv()

defs = dg.Definitions(
    assets=[
        k8s_resources,
        k8s_explain_docs,
        chunked_docs,
        embedded_docs,
        stored_docs,
    ],
    resources={
        "database": PostgresResource(
            host=os.getenv("DAGSTER_DB_HOST", "localhost"),
            port=int(os.getenv("DAGSTER_DB_PORT", "5433")),
            user=os.getenv("DB_USER", "dev"),
            password=os.getenv("DB_PASSWORD", "devpass"),
            dbname=os.getenv("DB_NAME", "kubebot"),
        ),
        "embeddings": EmbeddingsResource(
            api_key=os.getenv("OPENAI_API_KEY"),
        ),
    }
)