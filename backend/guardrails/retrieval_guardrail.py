from typing import List, Dict, Any
from backend.retrieval.rrf import ScoredChunk
from backend.config.settings import settings

class RetrievalGuardrail:
    """
    Evaluates evidence quality and relevance of retrieved chunks.
    Abstains if confidence score falls below threshold.
    """
    def __init__(self, min_threshold: float = None):
        self.min_threshold = min_threshold or settings.RELEVANCE_THRESHOLD

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

        # Confidence calculation
        confidence = min(1.0, max_rrf * 50.0 + top_dense * 0.4)

        if max_rrf < self.min_threshold and top_dense < 0.25 and top_bm25 < 1.0:
            return {
                "passed": False,
                "confidence": round(confidence, 3),
                "reason": "low_relevance_score",
                "message": "I couldn't find enough relevant information in the knowledge base to answer that."
            }

        return {
            "passed": True,
            "confidence": round(confidence, 3),
            "reason": None,
            "message": "Sufficient context retrieved."
        }
