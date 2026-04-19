#!/usr/bin/env python
"""Retrieval evaluation harness — compares vector-only vs. vector + rerank.

Usage (from the ``backend/`` directory):

    # Make sure DB is up and OPENAI_API_KEY is set
    python -m eval.run_eval          # runs both modes, prints report
    python -m eval.run_eval --k 5    # override top-k (default 3)

The script disables / enables the reranker via the ``RERANK_ENABLED`` env-var
between runs so the same ``search_db`` code path is exercised both ways.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import dataclass, field

# Ensure the backend package root is importable when running as ``python -m``
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from eval import EVAL_SET  # noqa: E402
from models import UserQuery, Source  # noqa: E402


# ---------------------------------------------------------------------------
# Metrics helpers
# ---------------------------------------------------------------------------

@dataclass
class EvalResult:
    question: str
    expected: list[str]
    retrieved: list[str]
    hit: bool
    latency_ms: float


@dataclass
class EvalReport:
    mode: str
    k: int
    results: list[EvalResult] = field(default_factory=list)

    @property
    def recall(self) -> float:
        return sum(r.hit for r in self.results) / len(self.results) if self.results else 0.0

    @property
    def mean_latency_ms(self) -> float:
        return sum(r.latency_ms for r in self.results) / len(self.results) if self.results else 0.0

    def summary_dict(self) -> dict:
        return {
            "mode": self.mode,
            "k": self.k,
            "questions": len(self.results),
            "hits": sum(r.hit for r in self.results),
            "recall@k": round(self.recall, 4),
            "mean_latency_ms": round(self.mean_latency_ms, 1),
        }


def _hit(expected: list[str], sources: list[Source]) -> bool:
    """True if *any* expected resource appears in the retrieved set."""
    retrieved_resources = {s.title.lower() for s in sources}
    retrieved_paths = {s.doc_path.lower() for s in sources}
    for exp in expected:
        exp_lower = exp.lower()
        if exp_lower in retrieved_resources or any(exp_lower in p for p in retrieved_paths):
            return True
    return False


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run_eval(k: int, mode: str) -> EvalReport:
    """Run the eval set in the given *mode* ('vector_only' or 'vector_rerank')."""
    # We import search_db fresh each time so env-var changes take effect
    # on the module-level flag inside services.db.
    import importlib
    import services.rerank as _rerank_mod
    import services.db as _db_mod

    if mode == "vector_only":
        os.environ["RERANK_ENABLED"] = "false"
    else:
        os.environ["RERANK_ENABLED"] = "true"

    # Force the modules to re-read the env var
    importlib.reload(_rerank_mod)
    importlib.reload(_db_mod)

    from services.db import search_db  # re-import after reload

    report = EvalReport(mode=mode, k=k)

    for entry in EVAL_SET:
        query = UserQuery(question=entry["question"])
        t0 = time.perf_counter()
        sources = search_db(query, k=k)
        elapsed_ms = (time.perf_counter() - t0) * 1000

        retrieved_titles = [s.title for s in sources]
        is_hit = _hit(entry["expected"], sources)

        report.results.append(
            EvalResult(
                question=entry["question"],
                expected=entry["expected"],
                retrieved=retrieved_titles,
                hit=is_hit,
                latency_ms=elapsed_ms,
            )
        )

    return report


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Kubebot retrieval eval")
    parser.add_argument("--k", type=int, default=3, help="top-k for retrieval")
    args = parser.parse_args()

    print("=" * 70)
    print("Kubebot Retrieval Eval — vector-only vs vector + cross-encoder rerank")
    print("=" * 70)

    reports: list[EvalReport] = []
    for mode in ("vector_only", "vector_rerank"):
        print(f"\n▶ Running: {mode} (k={args.k}) …")
        report = run_eval(k=args.k, mode=mode)
        reports.append(report)

        for r in report.results:
            status = "✓" if r.hit else "✗"
            print(f"  {status}  {r.question}")
            print(f"       expected: {r.expected}  |  got: {r.retrieved}  ({r.latency_ms:.0f} ms)")

    print("\n" + "=" * 70)
    print("Summary")
    print("=" * 70)
    for rpt in reports:
        print(json.dumps(rpt.summary_dict(), indent=2))

    # Delta
    if len(reports) == 2:
        delta = reports[1].recall - reports[0].recall
        sign = "+" if delta >= 0 else ""
        print(f"\nΔ recall@{args.k}: {sign}{delta:.4f}")
        latency_delta = reports[1].mean_latency_ms - reports[0].mean_latency_ms
        sign_l = "+" if latency_delta >= 0 else ""
        print(f"Δ mean latency: {sign_l}{latency_delta:.1f} ms")


if __name__ == "__main__":
    main()
