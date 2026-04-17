from __future__ import annotations

from dataclasses import dataclass

from api.models import Product
from api.repos.product_repo import ProductRepo
from api.services.openai_compat import OpenAICompatClient


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(y * y for y in b) ** 0.5
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def _keyword_score(query: str, product: Product) -> float:
    q = (query or "").strip().lower()
    if not q:
        return 0.0
    hay = " ".join(
        [
            product.title or "",
            product.sku or "",
            product.description or "",
            " ".join(product.tags or []),
        ]
    ).lower()
    tokens = [t for t in q.replace(",", " ").replace("，", " ").split() if t]
    if not tokens:
        return 0.0
    hit = sum(1 for t in tokens if t in hay)
    return hit / max(len(tokens), 1)


@dataclass(frozen=True)
class RetrievalResult:
    product: Product
    score: float
    score_keyword: float
    score_vector: float


@dataclass
class HybridRetriever:
    llm: OpenAICompatClient
    repo: ProductRepo

    async def retrieve(self, query: str, top_n: int) -> list[RetrievalResult]:
        products = self.repo.list_active_products_basic()
        query_emb = await self.llm.embed(query)
        id_to_emb = dict(self.repo.list_products_with_embeddings())

        scored: list[RetrievalResult] = []
        for p in products:
            kw = _keyword_score(query, p)
            emb = id_to_emb.get(p.id)
            vec = _cosine(query_emb, emb) if emb else 0.0
            score = 0.55 * vec + 0.45 * kw
            scored.append(
                RetrievalResult(product=p, score=score, score_keyword=kw, score_vector=vec)
            )

        scored.sort(key=lambda r: r.score, reverse=True)
        return scored[:top_n]

