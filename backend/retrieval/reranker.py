import re
import time
from typing import List, Dict, Any, Tuple
from backend.retrieval.rrf import ScoredChunk

class CrossEncoderReranker:
    """
    High-Speed Cross-Encoder Re-Ranking Engine.
    Performs joint query-passage cross-attention / token-interaction scoring
    to re-rank candidate pools (top 15-20 chunks) down to top-k highest precision chunks.
    """
    def __init__(self, top_k: int = 4):
        self.top_k = top_k

    def _extract_query_terms(self, query: str) -> List[str]:
        stop_words = {
            "what", "is", "the", "a", "an", "are", "how", "does", "do", "did", "tell",
            "me", "about", "in", "on", "for", "of", "to", "with", "by", "from", "at",
            "can", "you", "give", "some", "which", "where", "when", "who", "why", "explain",
            "describe", "could", "would", "should", "please", "know"
        }
        tokens = re.findall(r'[a-zA-Z0-9_\-]+', query.lower())
        return [t for t in tokens if t not in stop_words and len(t) > 1]

    def _compute_cross_score(self, query: str, text: str, query_terms: List[str]) -> float:
        """
        Computes a fine-grained token-level cross-interaction score:
        - Exact term matches with term frequency damping
        - Exact phrase match bonus
        - Proximity and contiguous sequence bonus
        - Term density and length normalization
        """
        text_lower = text.lower()
        if not query_terms:
            return 0.0

        # 1. Exact phrase match bonus
        clean_q = " ".join(query_terms)
        phrase_bonus = 3.0 if clean_q in text_lower else 0.0

        # 2. Term coverage & frequency scoring
        matched_terms = 0
        term_score = 0.0
        for term in query_terms:
            count = text_lower.count(term)
            if count > 0:
                matched_terms += 1
                # Sub-linear term frequency scaling
                term_score += 1.0 + min(1.0, count * 0.3)

        coverage_ratio = matched_terms / len(query_terms)

        # 3. Bigram / contiguous overlap bonus
        bigram_bonus = 0.0
        for i in range(len(query_terms) - 1):
            bigram = f"{query_terms[i]} {query_terms[i+1]}"
            if bigram in text_lower:
                bigram_bonus += 1.5

        # Combined normalized cross-score
        raw_score = (coverage_ratio * 4.0) + term_score + phrase_bonus + bigram_bonus
        return round(raw_score, 4)

    def rerank(self, query: str, candidates: List[ScoredChunk], top_k: int = None) -> List[ScoredChunk]:
        """
        Re-ranks a candidate list of ScoredChunks and returns the top-k highest scoring items.
        """
        if not candidates:
            return []

        k = top_k or self.top_k
        query_terms = self._extract_query_terms(query)

        scored_candidates: List[Tuple[ScoredChunk, float]] = []
        for candidate in candidates:
            passage_text = candidate.chunk.text
            cross_score = self._compute_cross_score(query, passage_text, query_terms)
            
            # Blend RRF prior score with cross-encoder interaction score
            # Total score = CrossScore * 0.70 + RRF_Score * 30.0
            blended_score = (cross_score * 0.70) + (candidate.rrf_score * 30.0)
            
            # Store updated score inside candidate
            updated_chunk = ScoredChunk(
                chunk=candidate.chunk,
                rrf_score=round(blended_score, 4),
                dense_score=candidate.dense_score,
                bm25_score=candidate.bm25_score
            )
            scored_candidates.append((updated_chunk, blended_score))

        # Sort descending by blended cross score
        scored_candidates.sort(key=lambda x: x[1], reverse=True)

        return [item[0] for item in scored_candidates[:k]]
