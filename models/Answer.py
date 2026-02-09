from pydantic import BaseModel
from typing import Iterable
from .Source import Source

class Answer(BaseModel):
    answer: str
    sources: Iterable[Source]