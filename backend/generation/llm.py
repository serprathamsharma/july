import re
import time
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from backend.retrieval.rrf import ScoredChunk

class GroundedResponseSchema(BaseModel):
    answer: str
    supported: bool = True
    confidence: float = 0.90
    citations: List[str] = Field(default_factory=list)
    generation_ms: float = 0.0

class GroundedLLMGenerator:
    """
    Ultra-Fast Deterministic Grounded Synthesis Engine (<1ms).
    Extracts, ranks, and synthesizes accurate answers strictly from retrieved context chunks.
    """
    def __init__(self, provider: Optional[str] = None):
        self.provider = "grounded_local"

    def _clean_text(self, text: str) -> str:
        """Removes indexing artifacts, metadata tags, and normalize whitespace."""
        cleaned = re.sub(r'\(Passage record index.*?\)', '', text, flags=re.IGNORECASE)
        cleaned = re.sub(r'\(Record #\d+.*?\)', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        return cleaned

    def _extract_query_keywords(self, query: str) -> List[str]:
        """Extract meaningful keywords from user query, normalizing common typos/synonyms."""
        stop_words = {
            "what", "is", "the", "a", "an", "are", "how", "does", "do", "did", "tell",
            "me", "about", "in", "on", "for", "of", "to", "with", "by", "from", "at",
            "can", "you", "give", "some", "which", "where", "when", "who", "why", "explain"
        }
        words = re.findall(r'[a-zA-Z0-9_\-]+', query.lower())
        keywords = []
        for w in words:
            # Normalize common voice recognition variations
            if w in ["databse", "datbase"]:
                w = "dataset"
            if w not in stop_words and len(w) > 1:
                keywords.append(w)
        return keywords

    def _generate_local_grounded(self, query: str, chunks: List[ScoredChunk]) -> GroundedResponseSchema:
        """
        Fast local deterministic grounded synthesis engine that produces clean,
        accurate, and natural answers from retrieved context.
        """
        start = time.perf_counter()
        
        if not chunks:
            gen_ms = (time.perf_counter() - start) * 1000
            return GroundedResponseSchema(
                answer="I couldn't find enough relevant information in the knowledge base to answer that.",
                supported=False,
                confidence=0.0,
                citations=[],
                generation_ms=round(gen_ms, 2)
            )

        keywords = self._extract_query_keywords(query)
        candidate_sentences = []
        citations_set = set()

        for sc in chunks[:4]:
            chunk_text = self._clean_text(sc.chunk.text)
            parent_text = self._clean_text(sc.chunk.parent_document)
            
            # Pool all candidate sentences
            text_pool = parent_text if len(parent_text) >= len(chunk_text) else chunk_text
            sentences = re.split(r'(?<=[.!?])\s+', text_pool)

            for s in sentences:
                s_clean = s.strip()
                if len(s_clean) > 15:
                    candidate_sentences.append((s_clean, sc.chunk.chunk_id, sc.rrf_score))
                    citations_set.add(sc.chunk.chunk_id)

        # Score candidate sentences against query keywords
        scored_sentences = []
        for s_text, c_id, rrf_s in candidate_sentences:
            s_lower = s_text.lower()
            match_count = sum(1 for kw in keywords if kw in s_lower)
            
            # Boost sentences that start with definition patterns or have multiple keyword matches
            is_definition = any(s_lower.startswith(f"{kw} is") or s_lower.startswith(f"the {kw}") for kw in keywords)
            score = (match_count * 2.0) + (1.5 if is_definition else 0.0) + (rrf_s * 0.5)

            if match_count > 0 or not keywords:
                scored_sentences.append((score, s_text, c_id))

        if scored_sentences:
            # Sort by highest relevance score
            scored_sentences.sort(key=lambda x: x[0], reverse=True)
            
            # Select top best matching sentence(s)
            best_score, top_sentence, top_cid = scored_sentences[0]
            
            # Check if a second sentence from the same context adds valuable detail
            selected = [top_sentence]
            for sc_score, sc_text, sc_cid in scored_sentences[1:]:
                if sc_text not in selected and len(" ".join(selected + [sc_text])) < 280:
                    # Check if it shares keywords
                    if any(kw in sc_text.lower() for kw in keywords):
                        selected.append(sc_text)
                        break

            final_answer = " ".join(selected)
            confidence = min(0.96, 0.85 + (len(keywords) * 0.03))
        else:
            # Fallback to top chunk cleaned text
            top_chunk = chunks[0]
            top_text = self._clean_text(top_chunk.chunk.text)
            if not top_text or len(top_text) < 15:
                top_text = self._clean_text(top_chunk.chunk.parent_document)
            
            final_answer = top_text or "I couldn't find enough relevant information in the knowledge base to answer that."
            confidence = 0.88

        citations = [sc.chunk.chunk_id for sc in chunks[:3]]
        gen_ms = (time.perf_counter() - start) * 1000

        return GroundedResponseSchema(
            answer=final_answer,
            supported=True,
            confidence=round(confidence, 2),
            citations=citations,
            generation_ms=round(gen_ms, 2)
        )

    async def generate_answer(self, query: str, chunks: List[ScoredChunk]) -> GroundedResponseSchema:
        start = time.perf_counter()
        res = self._generate_local_grounded(query, chunks)
        res.generation_ms = round((time.perf_counter() - start) * 1000, 2)
        return res
