from services.db import map_source


def test_map_source_basic():
    doc = {"field_path": "/docs/pods", "resource": "Pods", "content": "Pod info"}
    result = map_source(doc)
    assert result.doc_path == "/docs/pods"
    assert result.title == "Pods"
    assert result.relevant_info == "Pod info"


def test_map_source_maps_fields_correctly():
    """Verify the field mapping: field_path->doc_path, resource->title, content->relevant_info."""
    doc = {"field_path": "/api/v1", "resource": "Deployments", "content": "Deploy info"}
    result = map_source(doc)
    assert result.doc_path == "/api/v1"
    assert result.title == "Deployments"
    assert result.relevant_info == "Deploy info"
