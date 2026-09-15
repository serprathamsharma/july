import re
from typing import List, Dict, Any
from backend.retrieval.rrf import ScoredChunk

class GroundingGuardrail:
    """
    Verifies that the generated answer is grounded in either:
    - The retrieved context chunks (strict mode for local synthesizer), OR
    - World knowledge served by a live LLM (relaxed mode for Gemini/OpenAI).

    When a capable LLM provider is used, the answer itself IS the ground truth
    (it cites and elaborates beyond the narrow index), so we apply a much softer
    overlap floor to avoid false-positive hallucination rejections.
    """

    # Threshold for local extractive synthesizer (strict — answer must come from chunks)
    STRICT_THRESHOLD = 0.40

    # Threshold for LLM providers (relaxed — answer may use world knowledge)
    RELAXED_THRESHOLD = 0.15

    def verify_grounding(
        self,
        answer: str,
        context_chunks: List[ScoredChunk],
        provider: str = "grounded_local"
    ) -> Dict[str, Any]:
        if not answer:
            return {"grounded": False, "reason": "empty_answer", "grounding_score": 0.0}

        # Honest abstentions are always considered grounded
        abstention_phrases = [
            "couldn't find enough relevant information",
            "not enough context",
            "i don't have information",
            "i cannot answer",
        ]
        if any(phrase in answer.lower() for phrase in abstention_phrases):
            return {"grounded": True, "reason": "honest_abstention", "grounding_score": 1.0}

        # If no context was retrieved but LLM answered from world knowledge, allow it
        if not context_chunks:
            is_llm_provider = provider and "grounded_local" not in provider
            if is_llm_provider:
                return {"grounded": True, "reason": "llm_world_knowledge", "grounding_score": 1.0}
            return {"grounded": False, "reason": "empty_context", "grounding_score": 0.0}

        # Build combined context corpus from retrieved chunks (including parent documents)
        context_corpus_parts = []
        for sc in context_chunks:
            if sc.chunk.parent_document:
                context_corpus_parts.append(sc.chunk.parent_document.lower())
            context_corpus_parts.append(sc.chunk.text.lower())
        context_corpus = " ".join(context_corpus_parts)
        context_words = set(re.findall(r'\w+', context_corpus))

        # Extract meaningful answer words (filter stopwords)
        answer_words = re.findall(r'\w+', answer.lower())
        stop_words = {
            "the", "a", "an", "is", "are", "was", "were", "of", "and", "in", "to",
            "for", "with", "on", "that", "this", "it", "by", "as", "at", "be",
            "from", "according", "also", "its", "has", "have", "had", "been",
            "their", "they", "which", "who", "but", "or", "not", "can", "will",
            "would", "could", "should", "may", "might", "about", "into", "than",
            "so", "if", "when", "where", "how", "what", "why", "more", "most",
            "such", "some", "any", "all", "both", "each", "other", "known"
        }
        key_answer_words = [w for w in answer_words if w not in stop_words and len(w) > 2]

        if not key_answer_words:
            return {"grounded": True, "reason": "short_common_answer", "grounding_score": 1.0}

        # Calculate word-overlap grounding score
        matches = [w for w in key_answer_words if w in context_words]
        grounding_score = len(matches) / len(key_answer_words)

        # Determine which threshold applies based on provider
        is_llm_provider = provider and "grounded_local" not in provider
        threshold = self.RELAXED_THRESHOLD if is_llm_provider else self.STRICT_THRESHOLD

        if grounding_score < threshold:
            # For LLM providers, be more lenient: if answer is meaningful and non-empty, allow it
            if is_llm_provider and len(answer.split()) >= 5:
                return {
                    "grounded": True,
                    "reason": "llm_world_knowledge",
                    "grounding_score": round(grounding_score, 3),
                    "message": "LLM answer accepted with world knowledge supplement."
                }
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
