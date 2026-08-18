import re
from typing import List, Dict, Any
from backend.retrieval.rrf import ScoredChunk

class GroundingGuardrail:
    """
    Verifies that the generated answer is strictly grounded in the retrieved chunks.
    """
    def verify_grounding(self, answer: str, context_chunks: List[ScoredChunk]) -> Dict[str, Any]:
        if not answer or not context_chunks:
            return {"grounded": False, "reason": "empty_answer_or_context", "grounding_score": 0.0}

        if "couldn't find enough relevant information" in answer.lower() or "not enough context" in answer.lower():
            # Honest abstention is grounded
            return {"grounded": True, "reason": "honest_abstention", "grounding_score": 1.0}

        # Combine all source text (including parent document provenance from VAST hierarchical chunking)
        context_corpus_parts = []
        for sc in context_chunks:
            if sc.chunk.parent_document:
                context_corpus_parts.append(sc.chunk.parent_document.lower())
            context_corpus_parts.append(sc.chunk.text.lower())
        context_corpus = " ".join(context_corpus_parts)
        context_words = set(re.findall(r'\w+', context_corpus))

        # Extract answer words
        answer_words = re.findall(r'\w+', answer.lower())
        stop_words = {"the", "a", "an", "is", "are", "was", "were", "of", "and", "in", "to", "for", "with", "on", "that", "this", "it", "by", "as", "at", "be", "from", "according"}
        key_answer_words = [w for w in answer_words if w not in stop_words and len(w) > 2]

        if not key_answer_words:
            return {"grounded": True, "reason": "short_common_answer", "grounding_score": 1.0}

        # Match key words in context
        matches = [w for w in key_answer_words if w in context_words]
        grounding_score = len(matches) / len(key_answer_words)

        if grounding_score < 0.40:
            return {
                "grounded": False,
                "reason": "hallucination_detected",
                "grounding_score": round(grounding_score, 3),
                "message": "Generated answer contains facts unverified by retrieved context."
            }

        return {
            "grounded": True,
            "reason": None,
            "grounding_score": round(grounding_score, 3),
            "message": "Answer verified against context."
        }
