"""Answer-quality evaluation: measures whether the generated answer
is faithful to the retrieved context and covers expected topics.

Metrics produced:
  - keyword_coverage : fraction of expected keywords present in the answer
  - answer_relevance : 1.0 if the answer is non-empty and contains at
                       least one expected keyword, else 0.0
  - faithfulness     : (optional, requires OpenAI) LLM-as-judge score 0-1
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

GOLDEN_PATH = Path(__file__).parent / "golden_dataset.json"


@dataclass
class AnswerResult:
    """Result for a single question."""
    question_id: str
    question: str
    expected_keywords: list[str]
    answer: str
    keyword_coverage: float = 0.0
    answer_relevance: float = 0.0
    faithfulness: float | None = None


@dataclass
class AnswerReport:
    """Aggregate metrics across all questions."""
    results: list[AnswerResult] = field(default_factory=list)

    @property
    def mean_keyword_coverage(self) -> float:
        if not self.results:
            return 0.0
        return sum(r.keyword_coverage for r in self.results) / len(self.results)

    @property
    def mean_answer_relevance(self) -> float:
        if not self.results:
            return 0.0
        return sum(r.answer_relevance for r in self.results) / len(self.results)

    @property
    def mean_faithfulness(self) -> float | None:
        scored = [r for r in self.results if r.faithfulness is not None]
        if not scored:
            return None
        return sum(r.faithfulness for r in scored) / len(scored)

    def summary(self) -> dict:
        s: dict = {
            "total_questions": len(self.results),
            "mean_keyword_coverage": round(self.mean_keyword_coverage, 4),
            "mean_answer_relevance": round(self.mean_answer_relevance, 4),
        }
        mf = self.mean_faithfulness
        if mf is not None:
            s["mean_faithfulness"] = round(mf, 4)
        return s


def load_golden_dataset(path: Path | None = None) -> list[dict]:
    path = path or GOLDEN_PATH
    with open(path) as f:
        return json.load(f)


def _keyword_coverage(answer: str, keywords: list[str]) -> float:
    if not keywords:
        return 1.0
    answer_lower = answer.lower()
    hits = sum(1 for kw in keywords if kw.lower() in answer_lower)
    return hits / len(keywords)


def _answer_relevance(answer: str, keywords: list[str]) -> float:
    if not answer.strip():
        return 0.0
    answer_lower = answer.lower()
    return 1.0 if any(kw.lower() in answer_lower for kw in keywords) else 0.0


# ── LLM-as-judge faithfulness (optional) ──────────────────────────────

FAITHFULNESS_PROMPT = """You are an evaluation judge. Given a question, retrieved context, and an answer, rate how faithful the answer is to the provided context.

A faithful answer only contains information that can be derived from the context. Penalize hallucinated facts.

Question: {question}

Context: {context}

Answer: {answer}

Respond with ONLY a JSON object: {{"score": <float 0.0-1.0>, "reason": "<brief explanation>"}}"""


def _llm_faithfulness(
    question: str, context: str, answer: str
) -> float | None:
    """Call OpenAI to judge faithfulness. Returns None if unavailable."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None

    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "user",
                    "content": FAITHFULNESS_PROMPT.format(
                        question=question, context=context, answer=answer
                    ),
                }
            ],
            temperature=0.0,
        )
        text = response.choices[0].message.content or ""
        match = re.search(r'"score"\s*:\s*(\d+\.?\d*)', text)
        if match:
            return min(max(float(match.group(1)), 0.0), 1.0)
    except Exception:
        pass
    return None


# ── Public API ────────────────────────────────────────────────────────

AnswerFn = Callable[[str], tuple[str, str]]
"""(question) -> (answer_text, context_text)"""


def evaluate_answers(
    answer_fn: AnswerFn,
    dataset_path: Path | None = None,
    run_faithfulness: bool = False,
) -> AnswerReport:
    """Run answer-quality eval over the golden dataset.

    Args:
        answer_fn: callable that takes a question string and returns
                   (answer_text, context_text).
        dataset_path: override path to golden dataset JSON.
        run_faithfulness: if True, use LLM-as-judge for faithfulness scoring
                         (requires OPENAI_API_KEY).
    """
    dataset = load_golden_dataset(dataset_path)
    report = AnswerReport()

    for item in dataset:
        answer_text, context_text = answer_fn(item["question"])
        kw_cov = _keyword_coverage(answer_text, item["expected_keywords"])
        relevance = _answer_relevance(answer_text, item["expected_keywords"])

        faith = None
        if run_faithfulness:
            faith = _llm_faithfulness(item["question"], context_text, answer_text)

        report.results.append(
            AnswerResult(
                question_id=item["id"],
                question=item["question"],
                expected_keywords=item["expected_keywords"],
                answer=answer_text,
                keyword_coverage=kw_cov,
                answer_relevance=relevance,
                faithfulness=faith,
            )
        )

    return report
