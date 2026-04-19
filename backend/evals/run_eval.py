#!/usr/bin/env python3
"""Run the full evaluation suite against a live Kubebot instance.

Usage:
    # Retrieval only (default k=3):
    python -m evals.run_eval --retrieval

    # Answer quality:
    python -m evals.run_eval --answer

    # Both, with LLM faithfulness scoring:
    python -m evals.run_eval --all --faithfulness

    # Custom k and base URL:
    python -m evals.run_eval --all -k 5 --base-url http://localhost:8000

Environment:
    KUBEBOT_BASE_URL  – override the API base URL (default: http://localhost:8000)
    OPENAI_API_KEY    – required for --faithfulness
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

import requests

from .eval_retrieval import evaluate_retrieval, RetrievalReport
from .eval_answer import evaluate_answers, AnswerReport

DEFAULT_BASE_URL = "http://localhost:8000"


def _make_retrieval_fn(base_url: str):
    """Return a retrieval function that calls the /ask_simple endpoint."""

    def retrieval_fn(question: str, k: int) -> list[str]:
        resp = requests.post(
            f"{base_url}/ask_simple",
            json={"question": question},
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
        sources = data.get("sources", [])
        resources = [
            s.get("doc_path") or s.get("title", "")
            for s in sources
        ]
        return [r for r in resources if r]

    return retrieval_fn


def _make_answer_fn(base_url: str):
    """Return an answer function that calls the /ask endpoint."""

    def answer_fn(question: str) -> tuple[str, str]:
        resp = requests.post(
            f"{base_url}/ask",
            json={"question": question},
            timeout=120,
        )
        resp.raise_for_status()
        data = resp.json()
        answer_text = data.get("answer", "")
        sources = data.get("sources", [])
        context = "\n".join(
            s.get("relevant_info", "") for s in sources
        )
        return answer_text, context

    return answer_fn


def _print_report(title: str, summary: dict):
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")
    for key, value in summary.items():
        print(f"  {key:.<40s} {value}")
    print()


def _print_retrieval_details(report: RetrievalReport):
    print(f"\n{'─' * 60}")
    print("  Per-question retrieval details")
    print(f"{'─' * 60}")
    for r in report.results:
        status = "✓" if r.hit else "✗"
        print(f"  {status}  {r.question_id}: {r.question[:50]}")
        print(f"       expected : {r.expected_resources}")
        print(f"       retrieved: {r.retrieved_resources}")
    print()


def _print_answer_details(report: AnswerReport):
    print(f"\n{'─' * 60}")
    print("  Per-question answer details")
    print(f"{'─' * 60}")
    for r in report.results:
        print(f"  {r.question_id}: {r.question[:50]}")
        print(f"       keyword_coverage : {r.keyword_coverage:.2f}")
        print(f"       answer_relevance : {r.answer_relevance:.2f}")
        if r.faithfulness is not None:
            print(f"       faithfulness     : {r.faithfulness:.2f}")
        snippet = r.answer[:80].replace("\n", " ")
        print(f"       answer (snippet) : {snippet}...")
    print()


def main():
    import os

    parser = argparse.ArgumentParser(description="Kubebot Evaluation Suite")
    parser.add_argument("--retrieval", action="store_true", help="Run retrieval eval")
    parser.add_argument("--answer", action="store_true", help="Run answer eval")
    parser.add_argument("--all", action="store_true", help="Run all evals")
    parser.add_argument("--faithfulness", action="store_true", help="Include LLM faithfulness scoring")
    parser.add_argument("-k", type=int, default=3, help="Number of documents to retrieve (default: 3)")
    parser.add_argument("--base-url", default=None, help="Kubebot API base URL")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show per-question details")
    parser.add_argument("--json", action="store_true", help="Output results as JSON")
    args = parser.parse_args()

    base_url = args.base_url or os.getenv("KUBEBOT_BASE_URL", DEFAULT_BASE_URL)

    if not (args.retrieval or args.answer or args.all):
        parser.print_help()
        sys.exit(1)

    results: dict[str, Any] = {}

    if args.retrieval or args.all:
        print(f"Running retrieval eval (k={args.k}) against {base_url}...")
        retrieval_fn = _make_retrieval_fn(base_url)
        retrieval_report = evaluate_retrieval(retrieval_fn, k=args.k)
        results["retrieval"] = retrieval_report.summary()
        if not args.json:
            _print_report("Retrieval Metrics", retrieval_report.summary())
            if args.verbose:
                _print_retrieval_details(retrieval_report)

    if args.answer or args.all:
        print(f"Running answer eval against {base_url}...")
        answer_fn = _make_answer_fn(base_url)
        answer_report = evaluate_answers(
            answer_fn, run_faithfulness=args.faithfulness
        )
        results["answer"] = answer_report.summary()
        if not args.json:
            _print_report("Answer Quality Metrics", answer_report.summary())
            if args.verbose:
                _print_answer_details(answer_report)

    if args.json:
        print(json.dumps(results, indent=2))

    # Exit with non-zero if retrieval hit rate is below threshold
    if "retrieval" in results and results["retrieval"]["hit@k"] < 0.5:
        print("⚠  Retrieval hit@k below 0.50 threshold")
        sys.exit(1)


if __name__ == "__main__":
    main()
