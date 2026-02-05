from contextlib import contextmanager
from langgraph.checkpoint.postgres import PostgresSaver
from .db import database
import secrets


def generate_session_id():
    return secrets.token_urlsafe(32)

@contextmanager
def get_checkpointer():
    """
    Create and yield a PostgresSaver checkpointer for LangGraph state persistence.
    
    Usage:
        with get_checkpointer() as checkpointer:
            # Use checkpointer with your LangGraph agent
            agent = create_react_agent(..., checkpointer=checkpointer)
    """
    conn_string = database.get_conn_string()
    
    with PostgresSaver.from_conn_string(conn_string) as checkpointer:
        # Setup the checkpoint tables if they don't exist
        checkpointer.setup()
        yield checkpointer

