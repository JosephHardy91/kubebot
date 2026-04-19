"""Shared test fixtures — stub heavy external deps."""

import sys
from types import ModuleType
from unittest.mock import MagicMock

# ── Stub dagster before any etl import ──────────────────────────────────
dagster_stub = ModuleType("dagster")

class _FakeConfigurableResource:
    """Stub for dagster.ConfigurableResource that works as a base class."""
    def __init_subclass__(cls, **kw):
        pass
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

dagster_stub.ConfigurableResource = _FakeConfigurableResource  # type: ignore[attr-defined]
dagster_stub.asset = lambda f=None, **kw: f if f else (lambda fn: fn)  # type: ignore[attr-defined]
sys.modules.setdefault("dagster", dagster_stub)

# ── Stub psycopg2 ──────────────────────────────────────────────────────
psycopg2_stub = ModuleType("psycopg2")
psycopg2_stub.connect = MagicMock()  # type: ignore[attr-defined]
extras_stub = ModuleType("psycopg2.extras")
extras_stub.RealDictCursor = object  # type: ignore[attr-defined]
sys.modules.setdefault("psycopg2", psycopg2_stub)
sys.modules.setdefault("psycopg2.extras", extras_stub)

# ── Stub langchain / openai embeddings ─────────────────────────────────
_langchain_messages = ModuleType("langchain.messages")
_langchain_messages.AIMessage = type("AIMessage", (), {})  # type: ignore[attr-defined]
_langchain_messages.ToolMessage = type("ToolMessage", (), {})  # type: ignore[attr-defined]

_langchain_chat_models = ModuleType("langchain.chat_models")
_langchain_chat_models.init_chat_model = MagicMock()  # type: ignore[attr-defined]
_langchain_chat_models.BaseChatModel = type("BaseChatModel", (), {})  # type: ignore[attr-defined]

_langchain_agents = ModuleType("langchain.agents")
_langchain_agents.create_agent = MagicMock()  # type: ignore[attr-defined]

_langchain_tools = ModuleType("langchain.tools")
_langchain_tools.tool = lambda *a, **kw: (lambda f: f)  # type: ignore[attr-defined]

for mod_name in (
    "langchain",
    "langchain_core", "langchain_community",
    "langgraph", "langgraph.checkpoint", "langgraph.checkpoint.postgres",
    "langgraph.graph", "langgraph.graph.state",
):
    sys.modules.setdefault(mod_name, ModuleType(mod_name))

# langchain_openai needs OpenAIEmbeddings
_langchain_openai = ModuleType("langchain_openai")
_langchain_openai.OpenAIEmbeddings = MagicMock  # type: ignore[attr-defined]
sys.modules.setdefault("langchain_openai", _langchain_openai)

sys.modules.setdefault("langchain.messages", _langchain_messages)
sys.modules.setdefault("langchain.chat_models", _langchain_chat_models)
sys.modules.setdefault("langchain.agents", _langchain_agents)
sys.modules.setdefault("langchain.tools", _langchain_tools)

# ordered_set stub
_ordered_set = ModuleType("ordered_set")
_ordered_set.OrderedSet = list  # type: ignore[attr-defined]
sys.modules.setdefault("ordered_set", _ordered_set)

# Provide a LangGraph CompiledStateGraph stub for TYPE_CHECKING
_lg_state = sys.modules["langgraph.graph.state"]
_lg_state.CompiledStateGraph = type("CompiledStateGraph", (), {})  # type: ignore[attr-defined]

# PostgresSaver stub
_lg_cp_pg = sys.modules["langgraph.checkpoint.postgres"]
_lg_cp_pg.PostgresSaver = MagicMock()  # type: ignore[attr-defined]

