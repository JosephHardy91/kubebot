"""Retrieval evaluation: measures whether the expected K8s resources
appear in the top-k results returned by the vector search.

Metrics produced:
  - hit@k   : fraction of questions where *any* expected resource appears in top-k
  - mrr@k   : mean reciprocal rank across all questions
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

GOLDEN_PATH = Path(__file__).parent / "golden_dataset.json"


@dataclass
class RetrievalResult:
    """Result for a single question."""
    question_id: str
    question: str
    expected_resources: list[str]
    retrieved_resources: list[str]
    hit: bool = False
    reciprocal_rank: float = 0.0


@dataclass
class RetrievalReport:
    """Aggregate metrics across all questions."""
    results: list[RetrievalResult] = field(default_factory=list)

    @property
    def hit_rate(self) -> float:
        if not self.results:
            return 0.0
        return sum(1 for r in self.results if r.hit) / len(self.results)

    @property
    def mrr(self) -> float:
        if not self.results:
            return 0.0
        return sum(r.reciprocal_rank for r in self.results) / len(self.results)

    def summary(self) -> dict:
        return {
            "total_questions": len(self.results),
            "hit@k": round(self.hit_rate, 4),
            "mrr@k": round(self.mrr, 4),
        }


def load_golden_dataset(path: Path | None = None) -> list[dict]:
    path = path or GOLDEN_PATH
    with open(path) as f:
        return json.load(f)


def _compute_hit_and_rr(
    expected: list[str], retrieved: list[str]
) -> tuple[bool, float]:
    """Return (hit, reciprocal_rank) for one question."""
    for rank, resource in enumerate(retrieved, start=1):
        resource_lower = resource.lower()
        for exp in expected:
            # Match if the expected resource name appears in the retrieved
            # resource path (e.g. "pods" matches "pods" or "pods.v1").
            if exp.lower() in resource_lower or resource_lower in exp.lower():
                return True, 1.0 / rank
    return False, 0.0


# ── Public API ────────────────────────────────────────────────────────

RetrievalFn = Callable[[str, int], list[str]]
"""(question, k) -> list of resource names/paths retrieved."""


def evaluate_retrieval(
    retrieval_fn: RetrievalFn,
    k: int = 3,
    dataset_path: Path | None = None,
) -> RetrievalReport:
    """Run retrieval eval over every question in the golden dataset.

    Args:
        retrieval_fn: callable that takes (question, k) and returns a list of
                      resource names/paths ordered by relevance (most relevant first).
        k: number of documents to retrieve per question.
        dataset_path: override path to golden dataset JSON.
    """
    dataset = load_golden_dataset(dataset_path)
    report = RetrievalReport()

    for item in dataset:
        retrieved = retrieval_fn(item["question"], k)
        hit, rr = _compute_hit_and_rr(item["expected_resources"], retrieved)
        report.results.append(
            RetrievalResult(
                question_id=item["id"],
                question=item["question"],
                expected_resources=item["expected_resources"],
                retrieved_resources=retrieved,
                hit=hit,
                reciprocal_rank=rr,
            )
        )

    return report
