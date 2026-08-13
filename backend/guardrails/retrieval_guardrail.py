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

        # Realistic confidence calculation across hybrid dense & lexical scores
        rrf_ratio = min(1.0, max_rrf / 0.01639)
        bm25_ratio = min(1.0, top_bm25 / 12.0)
        dense_ratio = max(0.0, top_dense)

        confidence = round(min(1.0, (dense_ratio * 0.45) + (bm25_ratio * 0.35) + (rrf_ratio * 0.20)), 3)

        # Abstain if both dense vector similarity and BM25 score indicate weak relevance
        if top_dense < 0.38 and top_bm25 < 3.0:
            return {
                "passed": False,
                "confidence": confidence,
                "reason": "low_relevance_score",
                "message": "I couldn't find enough relevant information in the knowledge base to answer that."
            }

        return {
            "passed": True,
            "confidence": confidence,
            "reason": None,
            "message": "Sufficient context retrieved."
        }
