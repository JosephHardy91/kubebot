"""Offline evaluation tests — runnable in CI with no external dependencies.

These tests use synthetic retrieval and answer functions to verify the
evaluation framework itself, and demonstrate expected metric ranges.

Run:
    cd backend && python -m pytest evals/test_eval_offline.py -v
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from .eval_retrieval import (
    evaluate_retrieval,
    load_golden_dataset,
    _compute_hit_and_rr,
    RetrievalReport,
)
from .eval_answer import (
    evaluate_answers,
    _keyword_coverage,
    _answer_relevance,
    AnswerReport,
)


GOLDEN_PATH = Path(__file__).parent / "golden_dataset.json"


# ── Fixtures ─────────────────────────────────────────────────────────

@pytest.fixture
def golden_dataset():
    return load_golden_dataset(GOLDEN_PATH)


# ── Golden dataset structural tests ─────────────────────────────────

class TestGoldenDataset:
    def test_dataset_loads(self, golden_dataset):
        assert len(golden_dataset) >= 30

    def test_each_entry_has_required_fields(self, golden_dataset):
        required = {"id", "question", "expected_resources", "expected_keywords"}
        for item in golden_dataset:
            assert required.issubset(item.keys()), f"Missing fields in {item.get('id')}"

    def test_ids_are_unique(self, golden_dataset):
        ids = [item["id"] for item in golden_dataset]
        assert len(ids) == len(set(ids))

    def test_expected_resources_non_empty(self, golden_dataset):
        for item in golden_dataset:
            assert len(item["expected_resources"]) > 0, f"Empty resources in {item['id']}"

    def test_expected_keywords_non_empty(self, golden_dataset):
        for item in golden_dataset:
            assert len(item["expected_keywords"]) > 0, f"Empty keywords in {item['id']}"


# ── Retrieval eval unit tests ────────────────────────────────────────

class TestRetrievalHelpers:
    def test_exact_match(self):
        hit, rr = _compute_hit_and_rr(["pods"], ["pods", "services", "nodes"])
        assert hit is True
        assert rr == 1.0

    def test_match_at_rank_two(self):
        hit, rr = _compute_hit_and_rr(["services"], ["pods", "services", "nodes"])
        assert hit is True
        assert rr == pytest.approx(0.5)

    def test_no_match(self):
        hit, rr = _compute_hit_and_rr(["secrets"], ["pods", "services", "nodes"])
        assert hit is False
        assert rr == 0.0

    def test_partial_match(self):
        """e.g. 'deployments.apps' should match if 'deployments' is retrieved."""
        hit, rr = _compute_hit_and_rr(
            ["deployments.apps"], ["deployments", "services"]
        )
        assert hit is True

    def test_no_false_positive_substring(self):
        """'nodes' should NOT match 'nodeselector' — they are different resources."""
        hit, rr = _compute_hit_and_rr(["nodes"], ["nodeselector"])
        assert hit is False
        assert rr == 0.0

    def test_empty_retrieved(self):
        hit, rr = _compute_hit_and_rr(["pods"], [])
        assert hit is False
        assert rr == 0.0


class TestRetrievalEval:
    def test_perfect_retrieval(self, golden_dataset):
        """Simulate a retriever that always returns the correct resource first."""

        def perfect_retrieval(question: str, k: int) -> list[str]:
            for item in golden_dataset:
                if item["question"] == question:
                    return item["expected_resources"][:k]
            return []

        report = evaluate_retrieval(perfect_retrieval, k=3)
        assert report.hit_rate == 1.0
        assert report.mrr == 1.0

    def test_empty_retrieval(self, golden_dataset):
        """Simulate a retriever that returns nothing."""

        def empty_retrieval(question: str, k: int) -> list[str]:
            return []

        report = evaluate_retrieval(empty_retrieval, k=3)
        assert report.hit_rate == 0.0
        assert report.mrr == 0.0

    def test_report_summary_shape(self, golden_dataset):
        def dummy_retrieval(question: str, k: int) -> list[str]:
            return ["pods"]

        report = evaluate_retrieval(dummy_retrieval, k=3)
        summary = report.summary()
        assert "total_questions" in summary
        assert "hit@k" in summary
        assert "mrr@k" in summary


# ── Answer eval unit tests ───────────────────────────────────────────

class TestAnswerHelpers:
    def test_full_keyword_coverage(self):
        answer = "A Pod is the smallest deployable unit containing one or more containers on a node."
        keywords = ["smallest", "deployable", "container", "node"]
        assert _keyword_coverage(answer, keywords) == 1.0

    def test_partial_keyword_coverage(self):
        answer = "A Pod runs containers."
        keywords = ["smallest", "deployable", "container", "node"]
        assert _keyword_coverage(answer, keywords) == pytest.approx(0.25)

    def test_no_keyword_coverage(self):
        answer = "I don't know."
        keywords = ["smallest", "deployable", "container", "node"]
        assert _keyword_coverage(answer, keywords) == 0.0

    def test_empty_keywords(self):
        assert _keyword_coverage("anything", []) == 1.0

    def test_answer_relevance_positive(self):
        assert _answer_relevance("Pods are containers", ["container"]) == 1.0

    def test_answer_relevance_negative(self):
        assert _answer_relevance("Hello world", ["container"]) == 0.0

    def test_answer_relevance_empty(self):
        assert _answer_relevance("", ["container"]) == 0.0


class TestAnswerEval:
    def test_perfect_answers(self, golden_dataset):
        """Simulate answers that contain all expected keywords."""

        def perfect_answer(question: str) -> tuple[str, str]:
            for item in golden_dataset:
                if item["question"] == question:
                    # Build an answer containing all keywords
                    answer = " ".join(item["expected_keywords"])
                    return answer, "context about " + " ".join(item["expected_resources"])
            return "", ""

        report = evaluate_answers(perfect_answer, run_faithfulness=False)
        assert report.mean_keyword_coverage == 1.0
        assert report.mean_answer_relevance == 1.0
        assert report.mean_faithfulness is None  # not requested

    def test_empty_answers(self, golden_dataset):
        """Simulate empty answers."""

        def empty_answer(question: str) -> tuple[str, str]:
            return "", ""

        report = evaluate_answers(empty_answer, run_faithfulness=False)
        assert report.mean_keyword_coverage == 0.0
        assert report.mean_answer_relevance == 0.0

    def test_report_summary_shape(self):
        def dummy_answer(question: str) -> tuple[str, str]:
            return "some answer", "some context"

        report = evaluate_answers(dummy_answer, run_faithfulness=False)
        summary = report.summary()
        assert "total_questions" in summary
        assert "mean_keyword_coverage" in summary
        assert "mean_answer_relevance" in summary
