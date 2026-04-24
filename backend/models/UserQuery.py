from pydantic import BaseModel

class UserQuery(BaseModel):
    question: str
    streaming: bool = False