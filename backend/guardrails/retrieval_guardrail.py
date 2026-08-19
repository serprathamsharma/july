from typing import List, Dict, Any
from backend.retrieval.rrf import ScoredChunk
from backend.config.settings import settings

class RetrievalGuardrail:
    """
    Evaluates evidence quality and relevance of retrieved chunks.
    Allows relevant matches through and only abstains if zero relevant signals are retrieved.
    """
    def __init__(self, min_threshold: float = None, min_confidence: float = None):
        self.min_threshold = min_threshold or settings.RELEVANCE_THRESHOLD
        self.min_confidence = min_confidence if min_confidence is not None else settings.CONFIDENCE_ABSTAIN_THRESHOLD

    def evaluate_retrieval(self, retrieved_chunks: List[ScoredChunk]) -> Dict[str, Any]:
        if not retrieved_chunks:
            return {
                "passed": False,
                "confidence": 0.0,
                "reason": "no_chunks_retrieved",
                "message": "I couldn't find enough relevant information in the knowledge base to answer that."
            }

        top_chunk = retrieved_chunks[0]
        max_rrf = top_chunk.rrf_score
        top_dense = top_chunk.dense_score
        top_bm25 = top_chunk.bm25_score

        # Robust confidence calculation across hybrid dense & lexical channels
        rrf_ratio = min(1.0, max_rrf / 0.01639) if max_rrf > 0 else 0.0
        bm25_ratio = min(1.0, top_bm25 / 4.0) if top_bm25 > 0 else 0.0
        dense_ratio = min(1.0, max(0.0, top_dense))

        if top_dense > 0:
            confidence = round(min(1.0, (dense_ratio * 0.45) + (bm25_ratio * 0.35) + (rrf_ratio * 0.20)), 3)
        else:
            confidence = round(min(1.0, (bm25_ratio * 0.70) + (rrf_ratio * 0.30)), 3)

        # Only abstain on complete lack of relevant keyword or semantic matches
        if (top_bm25 <= 0.0 and top_dense <= 0.0) or (top_bm25 < 0.1 and top_dense < 0.1 and max_rrf < 0.001):
            return {
                "passed": False,
                "confidence": max(0.1, confidence),
                "reason": "low_relevance_score",
                "message": "I couldn't find enough relevant information in the knowledge base to answer that."
            }

        return {
            "passed": True,
            "confidence": max(0.80, confidence),
            "reason": None,
            "message": "Sufficient context retrieved."
        }
