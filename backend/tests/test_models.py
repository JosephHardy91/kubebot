import pytest
from models import Source, UserQuery, Answer


# -- Source model tests --

def test_source_creation():
    s = Source(doc_path="/docs/pods", title="Pods", relevant_info="Pod info")
    assert s.doc_path == "/docs/pods"
    assert s.title == "Pods"
    assert s.relevant_info == "Pod info"


def test_source_is_frozen():
    s = Source(doc_path="/docs/pods", title="Pods", relevant_info="Pod info")
    with pytest.raises(Exception):
        s.title = "Changed"


def test_source_equality():
    a = Source(doc_path="/docs/pods", title="Pods", relevant_info="info")
    b = Source(doc_path="/docs/pods", title="Pods", relevant_info="info")
    assert a == b


def test_source_from_dict():
    s = Source.model_validate({"doc_path": "/a", "title": "T", "relevant_info": "R"})
    assert s.title == "T"


# -- UserQuery model tests --

def test_user_query_creation():
    q = UserQuery(question="What is a pod?")
    assert q.question == "What is a pod?"


def test_user_query_missing_field():
    with pytest.raises(Exception):
        UserQuery()


# -- Answer model tests --

def test_answer_creation():
    src = Source(doc_path="/a", title="T", relevant_info="R")
    a = Answer(answer="hello", sources=[src])
    assert a.answer == "hello"
    assert list(a.sources) == [src]


def test_answer_empty_sources():
    a = Answer(answer="text", sources=[])
    assert a.answer == "text"
    assert list(a.sources) == []
