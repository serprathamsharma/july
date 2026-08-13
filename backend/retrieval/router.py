import re
from typing import List
from pydantic import BaseModel

class QueryStrategy(BaseModel):
    category: str  # factual | semantic | entity | ambiguous | short
    w_dense: float
    w_bm25: float
    preferred_chunk_types: List[str]
    top_k: int = 5

class AdaptiveRetrievalRouter:
    """
    Examines query characteristics (length, entities, question words, quote exact matches)
    and dynamically selects hybrid parameters and target chunk representations.
    """
    def route_query(self, query: str) -> QueryStrategy:
        clean_q = query.strip()
        words = clean_q.split()
        word_count = len(words)
        has_quotes = '"' in clean_q or "'" in clean_q
        has_digits = any(char.isdigit() for char in clean_q)

        # 1. Very short query (< 3 words)
        if word_count <= 2:
            return QueryStrategy(
                category="short",
                w_dense=0.40,
                w_bm25=0.60,
                preferred_chunk_types=["sentence", "paragraph"],
                top_k=5
            )

        # 2. Exact match / Quote / Proper Nouns / Numbers / Entities
        if has_quotes or has_digits or re.search(r'\b(who|where|when|what year|how much|how many|code|id)\b', clean_q, re.IGNORECASE):
            return QueryStrategy(
                category="factual",
                w_dense=0.35,
                w_bm25=0.65,
                preferred_chunk_types=["sentence", "paragraph"],
                top_k=5
            )

        # 3. Conceptual / Explanatory ("why", "how does", "explain", "describe")
        if re.search(r'\b(why|how|explain|describe|difference|overview|summary|cause|effect)\b', clean_q, re.IGNORECASE):
            return QueryStrategy(
                category="semantic",
                w_dense=0.70,
                w_bm25=0.30,
                preferred_chunk_types=["semantic", "paragraph"],
                top_k=5
            )

        # 4. General / Ambiguous Default
        return QueryStrategy(
            category="ambiguous",
            w_dense=0.50,
            w_bm25=0.50,
            preferred_chunk_types=["sentence", "paragraph", "semantic"],
            top_k=5
        )
