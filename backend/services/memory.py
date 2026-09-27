from contextlib import contextmanager
import re
from langgraph.checkpoint.postgres import PostgresSaver
from .db import database
import secrets

SESSION_ID_BYTES = 32
SESSION_ID_PATTERN = re.compile(rf"^[A-Za-z0-9_-]{{{len(secrets.token_urlsafe(SESSION_ID_BYTES))}}}$")

def generate_session_id():
    return secrets.token_urlsafe(SESSION_ID_BYTES)

def normalize_session_id(session_id: str | None) -> str | None:
    if session_id and SESSION_ID_PATTERN.fullmatch(session_id):
        return session_id
    return None

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
