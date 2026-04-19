"""Unit tests for the reranking layer."""

import os
from unittest.mock import patch, MagicMock

import pytest

from models import Source, UserQuery

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_source(title: str, info: str) -> Source:
    return Source(doc_path=f"/{title}", title=title, relevant_info=info)


SOURCES = [
    _make_source("pods", "A Pod is the smallest deployable unit in Kubernetes."),
    _make_source("services", "A Service exposes a set of Pods as a network service."),
    _make_source("configmaps", "ConfigMaps hold configuration data as key-value pairs."),
    _make_source("deployments.apps", "A Deployment provides declarative updates for Pods."),
]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestCrossEncoderReranker:
    """Tests for CrossEncoderReranker with a mocked cross-encoder model."""

    def _make_reranker(self, fake_scores):
        """Build a reranker whose underlying model returns *fake_scores*."""
        with patch("sentence_transformers.CrossEncoder") as MockCE:
            mock_model = MagicMock()
            mock_model.predict.return_value = fake_scores
            MockCE.return_value = mock_model

            from services.rerank import CrossEncoderReranker
            reranker = CrossEncoderReranker(model_name="mock")
            return reranker

    def test_rerank_reorders_by_score(self):
        scores = [0.1, 0.9, 0.3, 0.7]  # services wins, then deployments
        reranker = self._make_reranker(scores)

        result = reranker.rerank("What is a service?", SOURCES)

        assert result[0].title == "services"
        assert result[1].title == "deployments.apps"
        assert len(result) == len(SOURCES)

    def test_rerank_top_k_truncates(self):
        scores = [0.1, 0.9, 0.3, 0.7]
        reranker = self._make_reranker(scores)

        result = reranker.rerank("q", SOURCES, top_k=2)

        assert len(result) == 2
        assert result[0].title == "services"

    def test_rerank_empty_sources(self):
        reranker = self._make_reranker([])
        result = reranker.rerank("q", [])
        assert result == []


class TestRerankSources:
    """Tests for the convenience wrapper ``rerank_sources``."""

    def test_disabled_returns_original_order(self):
        os.environ["RERANK_ENABLED"] = "false"
        # Reset cached reranker
        import services.rerank as mod
        mod._reranker = None

        from services.rerank import rerank_sources

        query = UserQuery(question="test")
        result = rerank_sources(query, SOURCES)

        assert result == SOURCES

    def test_disabled_with_top_k_slices(self):
        os.environ["RERANK_ENABLED"] = "false"
        import services.rerank as mod
        mod._reranker = None

        from services.rerank import rerank_sources

        query = UserQuery(question="test")
        result = rerank_sources(query, SOURCES, top_k=2)

        assert len(result) == 2
        assert result == SOURCES[:2]


class TestEvalSet:
    """Sanity-check the eval set data structure."""

    def test_eval_set_non_empty(self):
        from eval import EVAL_SET

        assert len(EVAL_SET) > 0

    def test_eval_entries_have_required_keys(self):
        from eval import EVAL_SET

        for entry in EVAL_SET:
            assert "question" in entry
            assert "expected" in entry
            assert isinstance(entry["expected"], list)
