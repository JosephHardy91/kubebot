import dagster as dg
from dataclasses import dataclass

@dataclass
class DocChunk:
    resource: str
    field_path: str
    content: str

@dg.asset
def chunked_docs(k8s_explain_docs: dict[str, str]) -> list[dict]:
    """Chunk explain output by field path."""
    chunks = []
    
    for resource, content in k8s_explain_docs.items():
        # Simple chunking: split by top-level fields
        # TODO: smarter parsing of the explain output
        chunks.append({
            "resource": resource,
            "field_path": resource,
            "content": content
        })
    
    return chunks