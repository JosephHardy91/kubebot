from pydantic import BaseModel
from .Source import Source

class Answer(BaseModel):
    answer: str
    sources: list[Source]