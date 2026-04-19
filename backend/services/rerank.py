import os
from models import Source, UserQuery


class CrossEncoderReranker:
    """Reranks retrieval results using a cross-encoder model.

    Uses sentence-transformers CrossEncoder to score (query, passage) pairs
    and reorder results by relevance.  This adds a semantic reranking step
    on top of the pgvector cosine-similarity first stage, giving markedly
    better precision at small k.
    """

    def __init__(
        self,
        model_name: str | None = None,
        device: str | None = None,
    ):
        from sentence_transformers import CrossEncoder

        self.model_name = model_name or os.getenv(
            "RERANK_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2"
        )
        self.device = device or os.getenv("RERANK_DEVICE", "cpu")
        self._model = CrossEncoder(self.model_name, device=self.device)

    def rerank(
        self, query: str, sources: list[Source], top_k: int | None = None
    ) -> list[Source]:
        """Score each source against *query* and return them sorted by relevance.

        Parameters
        ----------
        query:
            The user's natural-language question.
        sources:
            Candidate sources returned by the first-stage retriever.
        top_k:
            If given, return only the top-k results after reranking.
            ``None`` means return all sources, reordered.
        """
        if not sources:
            return sources

        pairs = [(query, src.relevant_info) for src in sources]
        scores = self._model.predict(pairs)

        scored = sorted(
            zip(scores, sources), key=lambda t: t[0], reverse=True
        )

        reranked = [src for _, src in scored]
        if top_k is not None:
            reranked = reranked[:top_k]
        return reranked


# ---------------------------------------------------------------------------
# Module-level singleton, lazily initialised
# ---------------------------------------------------------------------------
_reranker: CrossEncoderReranker | None = None


def _is_rerank_enabled() -> bool:
    return os.getenv("RERANK_ENABLED", "true").lower() in ("1", "true", "yes")


def get_reranker() -> CrossEncoderReranker | None:
    """Return the module-level reranker (lazy init), or ``None`` if disabled."""
    global _reranker
    if not _is_rerank_enabled():
        return None
    if _reranker is None:
        _reranker = CrossEncoderReranker()
    return _reranker


def rerank_sources(
    query: UserQuery, sources: list[Source], top_k: int | None = None
) -> list[Source]:
    """Convenience wrapper: reranks *sources* if reranking is enabled."""
    reranker = get_reranker()
    if reranker is None:
        return sources if top_k is None else sources[:top_k]
    return reranker.rerank(query.question, sources, top_k=top_k)
