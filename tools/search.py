from models import UserQuery, Source
from langchain.tools import tool
from services.db import database, map_source, search_db
from psycopg2.extras import RealDictCursor

@tool
def initial_search(query: UserQuery, k:int = 3)->list[Source]:
    '''Input a user query and get an initial set of sources.'''
    return search_db(query, k)

@tool
def find_related_resources(resource_name: str, k:int = 5)->list[Source]:
    '''Find resources related to a given resource name by semantic similarity. Use to explore related Kubernetes resources.'''
    # Use the resource name as a query to find semantically similar docs
    return search_db(UserQuery(question=resource_name), k)

@tool 
def get_resource_by_name(resource_name: str)->list[Source]:
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
        print(f'Found {len(sources)} docs for resource {resource_name}')
    return sources

search_tools = [
    initial_search,
    find_related_resources,
    get_resource_by_name
]