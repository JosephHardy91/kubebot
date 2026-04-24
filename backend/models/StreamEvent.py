from typing import Literal

from pydantic import BaseModel

from .Answer import Answer


class StreamChunkEvent(BaseModel):
    type: Literal['chunk'] = 'chunk'
    content: str


class StreamFinalEvent(BaseModel):
    type: Literal['final'] = 'final'
    answer: Answer


class StreamErrorEvent(BaseModel):
    type: Literal['error'] = 'error'
    content: str