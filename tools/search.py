import json
from models import UserQuery, Source
from langchain.tools import tool
from services.db import database, map_source, search_db
from psycopg2.extras import RealDictCursor

def serialize_sources(sources: list[Source]) -> str:
    """Serialize sources to JSON string for LLM consumption."""
    return json.dumps([s.model_dump() for s in sources])

@tool(response_format="content_and_artifact")
def initial_search(query: UserQuery, k:int = 3)->tuple[str, list[Source]]:
    '''Input a user query and get an initial set of sources.'''
    sources = search_db(query, k)
    return serialize_sources(sources), sources

@tool(response_format="content_and_artifact")
def find_related_resources(resource_name: str, k:int = 5)->tuple[str, list[Source]]:
    '''Find resources related to a given resource name by semantic similarity. Use to explore related Kubernetes resources.'''
    sources = search_db(UserQuery(question=resource_name), k)
    return serialize_sources(sources), sources

@tool(response_format="content_and_artifact")
def get_resource_by_name(resource_name: str)->tuple[str, list[Source]]:
    '''Get the full documentation for a specific Kubernetes resource by its exact name (e.g., "pods", "deployments.apps").'''
    sources: list[Source] = []
    with database.get_connection() as conn:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute('''
                SELECT id, resource, field_path, content
                FROM k8s_docs
                WHERE field_path = %s OR resource = %s
                LIMIT 1
                ''', (resource_name, resource_name))
        sources = list(map(map_source, cur.fetchall()))
    return serialize_sources(sources), sources

search_tools = {
    'initial_search':initial_search,
    'find_related_resources':find_related_resources,
    'get_resource_by_name':get_resource_by_name
}