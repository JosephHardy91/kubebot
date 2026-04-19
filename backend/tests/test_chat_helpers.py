import pytest
from models import Source, UserQuery
from services.chat import (
    ensure_type,
    flatten_list_of_lists,
    to_source,
    get_last_ai_message,
    extract_ai_response,
    collect_sources,
)


# ---------------------------------------------------------------------------
# ensure_type
# ---------------------------------------------------------------------------

def test_ensure_type_simple_int():
    assert ensure_type(42, int) is True


def test_ensure_type_simple_str():
    assert ensure_type("hello", str) is True


def test_ensure_type_simple_mismatch():
    assert ensure_type("hello", int) is False


def test_ensure_type_list_of_int_match():
    assert ensure_type([1, 2, 3], list[int]) is True


def test_ensure_type_list_of_int_mismatch():
    assert ensure_type([1, "two", 3], list[int]) is False


def test_ensure_type_empty_list():
    assert ensure_type([], list[int]) is True


def test_ensure_type_dict_str_int():
    assert ensure_type({"a": 1, "b": 2}, dict[str, int]) is True


def test_ensure_type_dict_mismatch_value():
    assert ensure_type({"a": "not_int"}, dict[str, int]) is False


def test_ensure_type_dict_mismatch_key():
    assert ensure_type({1: "val"}, dict[str, int]) is False


def test_ensure_type_nested_list():
    assert ensure_type([[1, 2], [3]], list[list[int]]) is True


def test_ensure_type_nested_list_mismatch():
    assert ensure_type([[1, "x"]], list[list[int]]) is False


def test_ensure_type_source_instance():
    s = Source(doc_path="/a", title="T", relevant_info="R")
    assert ensure_type(s, Source) is True


def test_ensure_type_list_of_source():
    s = Source(doc_path="/a", title="T", relevant_info="R")
    assert ensure_type([s, s], list[Source]) is True


def test_ensure_type_list_of_source_wrong_element():
    assert ensure_type(["not_a_source"], list[Source]) is False


def test_ensure_type_wrong_container():
    assert ensure_type("not_a_list", list[int]) is False


# ---------------------------------------------------------------------------
# flatten_list_of_lists
# ---------------------------------------------------------------------------

def test_flatten_basic():
    assert flatten_list_of_lists([[1, 2], [3, 4]]) == [1, 2, 3, 4]


def test_flatten_empty():
    assert flatten_list_of_lists([]) == []


def test_flatten_single():
    assert flatten_list_of_lists([[1]]) == [1]


# ---------------------------------------------------------------------------
# to_source
# ---------------------------------------------------------------------------

def test_to_source_from_source():
    s = Source(doc_path="/a", title="T", relevant_info="R")
    assert to_source(s) is s


def test_to_source_from_dict():
    d = {"doc_path": "/a", "title": "T", "relevant_info": "R"}
    result = to_source(d)
    assert isinstance(result, Source)
    assert result.title == "T"


def test_to_source_invalid_type():
    with pytest.raises(ValueError, match="Cannot convert"):
        to_source(42)


# ---------------------------------------------------------------------------
# get_last_ai_message / extract_ai_response
# ---------------------------------------------------------------------------

def test_get_last_ai_message_returns_last():
    from langchain.messages import AIMessage
    m1 = AIMessage(content="first")
    m2 = AIMessage(content="second")
    result = get_last_ai_message([m1, m2])
    assert result is m2


def test_get_last_ai_message_empty():
    assert get_last_ai_message([]) is None


def test_extract_ai_response_with_message():
    from langchain.messages import AIMessage
    m = AIMessage(content="answer text")
    result = extract_ai_response({"messages": [m]})
    assert result == "answer text"


def test_extract_ai_response_empty():
    assert extract_ai_response({"messages": []}) is None


def test_extract_ai_response_missing_key():
    assert extract_ai_response({}) is None


# ---------------------------------------------------------------------------
# collect_sources
# ---------------------------------------------------------------------------

def _make_tool_message(name, artifact=None):
    """Create a real ToolMessage for testing collect_sources."""
    from langchain.messages import ToolMessage
    return ToolMessage(content="ok", name=name, tool_call_id="tc-1", artifact=artifact)


def _make_ai_message(text="hi"):
    from langchain.messages import AIMessage
    return AIMessage(content=text)


def test_collect_sources_empty_messages():
    from ordered_set import OrderedSet
    result = collect_sources({"messages": []})
    assert result == OrderedSet([])


def test_collect_sources_no_search_tools():
    msg = _make_tool_message(name="unrelated_tool", artifact=[{"doc_path": "/a", "title": "T", "relevant_info": "R"}])
    result = collect_sources({"messages": [msg]})
    from ordered_set import OrderedSet
    assert result == OrderedSet([])


def test_collect_sources_with_source_artifacts():
    s = Source(doc_path="/a", title="T", relevant_info="R")
    msg = _make_tool_message(name="initial_search", artifact=[s])
    result = collect_sources({"messages": [msg]})
    assert len(result) == 1
    assert list(result)[0] == s


def test_collect_sources_with_dict_artifacts():
    """Artifacts may be dicts when deserialized from history; collect_sources should convert them."""
    d = {"doc_path": "/a", "title": "T", "relevant_info": "R"}
    msg = _make_tool_message(name="initial_search", artifact=[d])
    result = collect_sources({"messages": [msg]})
    assert len(result) == 1
    assert isinstance(list(result)[0], Source)


def test_collect_sources_skips_none_artifacts():
    msg = _make_tool_message(name="initial_search", artifact=None)
    result = collect_sources({"messages": [msg]})
    from ordered_set import OrderedSet
    assert result == OrderedSet([])


def test_collect_sources_deduplicates():
    s = Source(doc_path="/a", title="T", relevant_info="R")
    msg1 = _make_tool_message(name="initial_search", artifact=[s])
    msg2 = _make_tool_message(name="find_related_resources", artifact=[s])
    result = collect_sources({"messages": [msg1, msg2]})
    assert len(result) == 1


def test_collect_sources_multiple_tools():
    s1 = Source(doc_path="/a", title="A", relevant_info="R1")
    s2 = Source(doc_path="/b", title="B", relevant_info="R2")
    msg1 = _make_tool_message(name="initial_search", artifact=[s1])
    msg2 = _make_tool_message(name="get_resource_by_name", artifact=[s2])
    result = collect_sources({"messages": [msg1, msg2]})
    assert len(result) == 2


def test_collect_sources_ignores_ai_messages():
    ai = _make_ai_message("some response")
    result = collect_sources({"messages": [ai]})
    from ordered_set import OrderedSet
    assert result == OrderedSet([])
