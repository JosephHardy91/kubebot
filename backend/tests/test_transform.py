"""Tests for field-path chunking in etl.assets.transform."""
import pytest
from etl.assets.transform import _chunk_explain, _parse_field_line


# ---------------------------------------------------------------------------
# Fixture: a realistic (small) kubectl explain --recursive output that has
# already been run through parse_explain_text (2-space normalised indent).
# ---------------------------------------------------------------------------
SAMPLE_EXPLAIN = """\
KIND:     Deployment
VERSION:  apps/v1

DESCRIPTION:
Deployment enables declarative updates for Pods and ReplicaSets.

FIELDS:
  apiVersion  <string>
  kind  <string>
  metadata  <ObjectMeta>
    name  <string>
    namespace  <string>
    labels  <map[string]string>
  spec  <DeploymentSpec>
    replicas  <integer>
    selector  <LabelSelector>
      matchLabels  <map[string]string>
    template  <PodTemplateSpec>
      metadata  <ObjectMeta>
        labels  <map[string]string>
      spec  <PodSpec>
        containers  <[]Container>
          name  <string>
          image  <string>
  status  <DeploymentStatus>
    availableReplicas  <integer>
    conditions  <[]DeploymentCondition>
      type  <string>
      status  <string>"""


class TestParseFieldLine:
    def test_simple_field(self):
        level, name, ann = _parse_field_line("  apiVersion  <string>")
        assert level == 1
        assert name == "apiVersion"
        assert ann == "<string>"

    def test_nested_field(self):
        level, name, ann = _parse_field_line("      matchLabels  <map[string]string>")
        assert level == 3
        assert name == "matchLabels"

    def test_blank_line(self):
        assert _parse_field_line("") is None

    def test_no_type(self):
        level, name, ann = _parse_field_line("  apiVersion")
        assert ann == ""


class TestChunkExplain:
    def test_preamble_chunk_exists(self):
        chunks = _chunk_explain("deployments.apps", SAMPLE_EXPLAIN)
        preamble = [c for c in chunks if c["field_path"] == "deployments.apps"]
        assert len(preamble) == 1
        assert "Deployment enables declarative" in preamble[0]["content"]
        assert "FIELDS:" in preamble[0]["content"]

    def test_top_level_fields_are_split(self):
        chunks = _chunk_explain("deployments.apps", SAMPLE_EXPLAIN)
        field_paths = [c["field_path"] for c in chunks]
        assert "deployments.apps.apiVersion" in field_paths
        assert "deployments.apps.kind" in field_paths
        assert "deployments.apps.metadata" in field_paths
        assert "deployments.apps.spec" in field_paths
        assert "deployments.apps.status" in field_paths

    def test_nested_fields_included_in_parent(self):
        chunks = _chunk_explain("deployments.apps", SAMPLE_EXPLAIN)
        spec_chunk = next(c for c in chunks if c["field_path"] == "deployments.apps.spec")
        # nested children should be inside the spec chunk
        assert "replicas" in spec_chunk["content"]
        assert "containers" in spec_chunk["content"]
        assert "image" in spec_chunk["content"]

    def test_breadcrumb_in_content(self):
        chunks = _chunk_explain("deployments.apps", SAMPLE_EXPLAIN)
        spec_chunk = next(c for c in chunks if c["field_path"] == "deployments.apps.spec")
        # The content should start with the breadcrumb line
        assert spec_chunk["content"].startswith("deployments.apps > spec")

    def test_no_fields_section(self):
        text = "KIND:     ConfigMap\nVERSION:  v1\n\nDESCRIPTION:\nA key-value store."
        chunks = _chunk_explain("configmaps", text)
        assert len(chunks) == 1
        assert chunks[0]["field_path"] == "configmaps"

    def test_all_chunks_have_required_keys(self):
        chunks = _chunk_explain("deployments.apps", SAMPLE_EXPLAIN)
        for chunk in chunks:
            assert "resource" in chunk
            assert "field_path" in chunk
            assert "content" in chunk
            assert chunk["resource"] == "deployments.apps"

    def test_chunk_count(self):
        chunks = _chunk_explain("deployments.apps", SAMPLE_EXPLAIN)
        # 1 preamble + 5 top-level fields (apiVersion, kind, metadata, spec, status)
        assert len(chunks) == 6
