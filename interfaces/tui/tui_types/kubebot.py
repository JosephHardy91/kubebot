from pydantic import BaseModel

class KubebotSessionInfo(BaseModel):
    session_id:str|None