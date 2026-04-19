from contextlib import asynccontextmanager
from .chat import init_agents
from .memory import get_checkpointer


@asynccontextmanager
async def lifespan(app):
    """FastAPI lifespan context manager for agent initialization."""
    with get_checkpointer() as checkpointer:
        init_agents(checkpointer)
        yield
