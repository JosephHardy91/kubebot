from pydantic import BaseModel

class Source(BaseModel):
    doc_path: str
    title: str
    relevant_info: str #would separate this out from strict source modeling in production, for here, this is a TODO
    #could do version, db id, etc. here later