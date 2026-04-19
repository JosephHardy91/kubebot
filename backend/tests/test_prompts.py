from models import Source, UserQuery
from prompts import make_grounding_prompt, make_agent_prompt


# ---------------------------------------------------------------------------
# make_grounding_prompt
# ---------------------------------------------------------------------------

def test_grounding_prompt_returns_dict_with_keys():
    docs = [Source(doc_path="/a", title="Pods", relevant_info="Pod overview")]
    query = UserQuery(question="What is a pod?")
    result = make_grounding_prompt(docs, query)
    assert "system" in result
    assert "user" in result


def test_grounding_prompt_system_is_nonempty():
    docs = [Source(doc_path="/a", title="Pods", relevant_info="Pod overview")]
    query = UserQuery(question="What is a pod?")
    result = make_grounding_prompt(docs, query)
    assert len(result["system"].strip()) > 0


def test_grounding_prompt_user_contains_query():
    docs = [Source(doc_path="/a", title="Pods", relevant_info="info")]
    query = UserQuery(question="What is a pod?")
    result = make_grounding_prompt(docs, query)
    assert "What is a pod?" in result["user"]


def test_grounding_prompt_user_contains_source_title():
    docs = [Source(doc_path="/a", title="Pods", relevant_info="info")]
    query = UserQuery(question="q")
    result = make_grounding_prompt(docs, query)
    assert "Pods" in result["user"]


def test_grounding_prompt_user_contains_relevant_info():
    docs = [Source(doc_path="/a", title="T", relevant_info="detailed pod info")]
    query = UserQuery(question="q")
    result = make_grounding_prompt(docs, query)
    assert "detailed pod info" in result["user"]


def test_grounding_prompt_multiple_docs():
    docs = [
        Source(doc_path="/a", title="Pods", relevant_info="info1"),
        Source(doc_path="/b", title="Services", relevant_info="info2"),
    ]
    query = UserQuery(question="q")
    result = make_grounding_prompt(docs, query)
    assert "Pods" in result["user"]
    assert "Services" in result["user"]
    assert "info1" in result["user"]
    assert "info2" in result["user"]


# ---------------------------------------------------------------------------
# make_agent_prompt
# ---------------------------------------------------------------------------

class _FakeTool:
    """Minimal stand-in for langchain tool objects."""
    def __init__(self, name, description):
        self.name = name
        self.description = description


def test_agent_prompt_contains_query():
    query = UserQuery(question="How do I scale a deployment?")
    result = make_agent_prompt(query, [])
    assert "How do I scale a deployment?" in result


def test_agent_prompt_contains_tool_names():
    tools = [_FakeTool("search", "search docs"), _FakeTool("lookup", "lookup resource")]
    query = UserQuery(question="q")
    result = make_agent_prompt(query, tools)
    assert "search" in result
    assert "lookup" in result


def test_agent_prompt_contains_tool_descriptions():
    tools = [_FakeTool("search", "search docs")]
    query = UserQuery(question="q")
    result = make_agent_prompt(query, tools)
    assert "search docs" in result


def test_agent_prompt_empty_tools():
    query = UserQuery(question="Tell me about pods")
    result = make_agent_prompt(query, [])
    assert "Tell me about pods" in result


def test_agent_prompt_returns_string():
    query = UserQuery(question="q")
    result = make_agent_prompt(query, [])
    assert isinstance(result, str)
