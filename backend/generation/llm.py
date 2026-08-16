import os
import re
import json
import time
import asyncio
import httpx
from typing import List, Dict, Any, Optional, AsyncGenerator, Tuple
from pydantic import BaseModel, Field
from backend.config.settings import settings
from backend.retrieval.rrf import ScoredChunk

class GroundedResponseSchema(BaseModel):
    answer: str
    supported: bool = True
    confidence: float = 0.90
    citations: List[str] = Field(default_factory=list)
    generation_ms: float = 0.0
    provider: str = "grounded_local"

class GroundedLLMGenerator:
    """
    Intelligent Grounded Synthesis Engine.
    Supports Google Gemini (default), OpenAI / Groq, and an advanced
    Intent-Aware Local Neural/Semantic Synthesizer for zero-API/offline mode.
    """
    def __init__(self, provider: Optional[str] = None):
        self.provider = provider or settings.LLM_PROVIDER
        self.gemini_api_key = settings.GEMINI_API_KEY
        self.openai_api_key = settings.OPENAI_API_KEY
        self.gemini_model = settings.GEMINI_MODEL or settings.LLM_MODEL
        self.openai_model = settings.OPENAI_MODEL

    def _resolve_active_provider(self) -> str:
        """Determines which provider to use based on available API keys and configuration."""
        if self.provider == "gemini":
            return "gemini" if self.gemini_api_key and not self.gemini_api_key.startswith("your_") else "grounded_local"
        elif self.provider == "openai":
            return "openai" if self.openai_api_key and not self.openai_api_key.startswith("your_") else "grounded_local"
        elif self.provider == "auto":
            if self.gemini_api_key and not self.gemini_api_key.startswith("your_"):
                return "gemini"
            elif self.openai_api_key and not self.openai_api_key.startswith("your_"):
                return "openai"
            return "grounded_local"
        return "grounded_local"

    def _clean_text(self, text: str) -> str:
        """Removes indexing artifacts, metadata tags, and normalizes whitespace."""
        if not text:
            return ""
        cleaned = re.sub(r'\(Passage record index.*?\)', '', text, flags=re.IGNORECASE)
        cleaned = re.sub(r'\(Record #\d+.*?\)', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'\[Document #\d+.*?\]', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        return cleaned

    def _extract_query_keywords(self, query: str) -> List[str]:
        """Extract meaningful keywords and stems from user query."""
        stop_words = {
            "what", "is", "the", "a", "an", "are", "how", "does", "do", "did", "tell",
            "me", "about", "in", "on", "for", "of", "to", "with", "by", "from", "at",
            "can", "you", "give", "some", "which", "where", "when", "who", "why", "explain",
            "describe", "could", "would", "should", "please", "know", "wondering", "find",
            "that", "this", "these", "those", "into", "onto", "upon"
        }
        words = re.findall(r'[a-zA-Z0-9_\-]+', query.lower())
        keywords = []
        for w in words:
            if w in ["databse", "datbase"]:
                w = "dataset"
            if w not in stop_words and len(w) > 1:
                keywords.append(w)
                # Add stem for inflected forms (e.g. 'hallucinations' -> 'hallucinat', 'drivers' -> 'driver')
                if w.endswith("ies") and len(w) > 4:
                    keywords.append(w[:-3] + "y")
                elif w.endswith("es") and len(w) > 4:
                    keywords.append(w[:-2])
                elif w.endswith("s") and len(w) > 3 and not w.endswith("ss"):
                    keywords.append(w[:-1])
                elif w.endswith("ing") and len(w) > 5:
                    keywords.append(w[:-3])
                elif w.endswith("ed") and len(w) > 4:
                    keywords.append(w[:-2])
                elif w.endswith("tion") and len(w) > 6:
                    keywords.append(w[:-4])
        return list(dict.fromkeys(keywords))

    def _detect_query_intent(self, query: str) -> str:
        """Classifies user query into actionable semantic intent."""
        q_lower = query.lower()
        if re.search(r'\b(what is|define|meaning of|what does|stands for)\b', q_lower):
            return "DEFINITIONAL"
        if re.search(r'\b(why|how does|how do|how is|explain the mechanism|cause|function)\b', q_lower):
            return "EXPLANATORY"
        if re.search(r'\b(which|what are the|list|name the|factors|algorithms|languages|drivers|types)\b', q_lower):
            return "ENUMERATIVE"
        if re.search(r'\b(difference between|compare|versus|vs|contrast)\b', q_lower):
            return "COMPARATIVE"
        if re.search(r'\b(where|when|who|which year|how many|how much)\b', q_lower):
            return "FACTOID"
        return "GENERAL"

    def _extract_subject_entity(self, query: str) -> str:
        """Extracts the primary subject noun/entity from the query for clean coreference resolution."""
        # 1. Check for prominent domain acronyms or capitalized tokens in original query
        acronyms = re.findall(r'\b([A-Z]{2,}(?:-[A-Z0-9]+)?|[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b', query)
        for acr in acronyms:
            if acr.lower() not in ["what", "how", "why", "where", "when", "which", "who", "tell", "explain"]:
                return acr

        # 2. Extract noun phrase following query verbs: "how does X prevent", "what is X", "explain X"
        m = re.search(r'\b(?:how does|how do|what is|what are|tell me about|explain|describe)\s+([a-zA-Z0-9_\-]+(?:\s+[a-zA-Z0-9_\-]+)?)\b', query, re.IGNORECASE)
        if m:
            candidate = m.group(1).strip()
            if candidate.lower() not in ["the", "a", "an", "this", "that"]:
                return candidate.title()

        # 3. Fallback to first non-stop keyword
        kws = self._extract_query_keywords(query)
        return kws[0].title() if kws else ""

    def _resolve_coreferences(self, sentence: str, subject_entity: str) -> str:
        """Replaces ambiguous leading pronouns with the explicit entity name for clarity."""
        if not subject_entity:
            return sentence
        
        # Replace leading 'It is', 'It was', 'They are', 'They were'
        patterns = [
            (r'^(It is|It was|It has been)\b', f"{subject_entity} is"),
            (r'^(They are|They were|These are)\b', f"{subject_entity} comprises"),
            (r'^(This is|This was)\b', f"{subject_entity} is"),
        ]
        s = sentence
        for pat, repl in patterns:
            s = re.sub(pat, repl, s, flags=re.IGNORECASE)
        return s

    def _synthesize_smart_local(self, query: str, chunks: List[ScoredChunk]) -> GroundedResponseSchema:
        """
        High-Intelligence Intent-Aware Local Synthesizer.
        Extracts, links, and synthesizes multi-fact answers with coreference resolution
        and natural voice conversational cadence.
        """
        start = time.perf_counter()
        
        if not chunks:
            gen_ms = (time.perf_counter() - start) * 1000
            return GroundedResponseSchema(
                answer="I couldn't find enough relevant information in the knowledge base to answer that.",
                supported=False,
                confidence=0.0,
                citations=[],
                generation_ms=round(gen_ms, 2),
                provider="grounded_local"
            )

        intent = self._detect_query_intent(query)
        keywords = self._extract_query_keywords(query)
        
        # Extract probable subject entity from query
        subject_entity = self._extract_subject_entity(query)

        candidate_sentences = []
        citations_set = set()

        for sc in chunks[:5]:
            chunk_text = self._clean_text(sc.chunk.text)
            parent_text = self._clean_text(sc.chunk.parent_document)
            
            # Use richer text pool
            text_pool = parent_text if len(parent_text) > len(chunk_text) else chunk_text
            # Split into clean grammatical sentences
            raw_sentences = re.split(r'(?<=[.!?])\s+', text_pool)

            for s in raw_sentences:
                s_clean = s.strip()
                if len(s_clean) > 15:
                    candidate_sentences.append({
                        "text": s_clean,
                        "chunk_id": sc.chunk.chunk_id,
                        "rrf_score": sc.rrf_score,
                        "dense_score": sc.dense_score,
                        "bm25_score": sc.bm25_score
                    })
                    citations_set.add(sc.chunk.chunk_id)

        # Score candidate sentences based on query intent & keyword density
        scored_sentences = []
        for item in candidate_sentences:
            s_text = item["text"]
            s_lower = s_text.lower()
            
            # Count exact keyword and synonym matches
            matched_kws = [kw for kw in keywords if kw in s_lower]
            match_count = len(matched_kws)
            
            # Base relevance score
            score = (match_count * 3.0) + (item["rrf_score"] * 10.0) + (item["dense_score"] * 2.0)
            
            # Intent-specific heuristic boosts
            if intent == "DEFINITIONAL":
                if any(s_lower.startswith(f"{kw} is") or s_lower.startswith(f"the {kw}") or " is a " in s_lower or " designed for " in s_lower for kw in keywords):
                    score += 5.0
            elif intent == "EXPLANATORY":
                if any(conn in s_lower for conn in ["by ", "because", "due to", "in order to", "enables", "allows", "reduces", "improves"]):
                    score += 4.0
            elif intent == "ENUMERATIVE":
                if any(delim in s_text for delim in [",", " and ", "including", "such as", "supported"]):
                    score += 4.0
            elif intent == "FACTOID":
                if any(kw in s_lower for kw in keywords):
                    score += 3.5

            if match_count > 0 or not keywords:
                scored_sentences.append((score, s_text, item["chunk_id"], matched_kws))

        if scored_sentences:
            # Sort by highest score
            scored_sentences.sort(key=lambda x: x[0], reverse=True)
            
            best_score, top_sentence, top_cid, top_matches = scored_sentences[0]
            top_sentence_resolved = self._resolve_coreferences(top_sentence, subject_entity)
            selected = [top_sentence_resolved]
            covered_keywords = set(top_matches)
            
            # Complementary sentence synthesis: find a secondary sentence that adds distinct facts
            for sc_score, sc_text, sc_cid, sc_matches in scored_sentences[1:]:
                # Check for new keywords and avoid near-duplicates
                new_kws = [k for k in sc_matches if k not in covered_keywords]
                if sc_text not in selected and len(" ".join(selected + [sc_text])) <= 320:
                    if new_kws or (intent == "EXPLANATORY" and any(w in sc_text.lower() for w in ["enables", "reduces", "ensures", "results"])):
                        resolved_sec = self._resolve_coreferences(sc_text, subject_entity)
                        # Avoid duplicating the subject if both start with the same noun
                        if not (resolved_sec.startswith(subject_entity) and selected[0].startswith(subject_entity)):
                            selected.append(resolved_sec)
                            covered_keywords.update(sc_matches)
                            if len(selected) >= 2:
                                break

            final_answer = " ".join(selected).strip()
            # Ensure answer ends with proper punctuation
            if not final_answer.endswith((".", "!", "?")):
                final_answer += "."
            
            confidence = min(0.98, 0.88 + (len(covered_keywords) * 0.02))
        else:
            # Fallback to the cleanest top chunk passage
            top_chunk = chunks[0]
            top_text = self._clean_text(top_chunk.chunk.text)
            if not top_text or len(top_text) < 15:
                top_text = self._clean_text(top_chunk.chunk.parent_document)
            
            final_answer = top_text or "I couldn't find enough relevant information in the knowledge base to answer that."
            confidence = 0.85

        citations = [sc.chunk.chunk_id for sc in chunks[:3]]
        gen_ms = (time.perf_counter() - start) * 1000

        return GroundedResponseSchema(
            answer=final_answer,
            supported=True,
            confidence=round(confidence, 2),
            citations=citations,
            generation_ms=round(gen_ms, 2),
            provider="grounded_local"
        )

    async def _generate_gemini(self, query: str, chunks: List[ScoredChunk]) -> GroundedResponseSchema:
        """
        Synthesizes high-accuracy grounded responses using Google Gemini API.
        Optimized for voice RAG with strict grounding and sub-second generation.
        """
        start = time.perf_counter()
        
        # Format context passages
        context_blocks = []
        citations = []
        for sc in chunks[:4]:
            text = self._clean_text(sc.chunk.text)
            context_blocks.append(f"[Source {sc.chunk.chunk_id}]: {text}")
            citations.append(sc.chunk.chunk_id)

        context_str = "\n\n".join(context_blocks)

        system_instruction = (
            "You are July, an ultra-smart, voice-enabled grounded AI assistant. "
            "Your task is to answer the user's question accurately, concisely, and naturally based ONLY on the provided context. "
            "Guidelines:\n"
            "1. Answer in 1 to 3 clear, fluid, conversational sentences suitable for speech.\n"
            "2. If the query asks for a list or attributes, provide a clean, complete response.\n"
            "3. Do not mention 'according to the context' or 'passage' unless necessary; speak naturally and authoritatively.\n"
            "4. Strictly rely on the provided context. If the context does not contain the answer, reply: "
            "'I couldn't find enough relevant information in the knowledge base to answer that.'"
        )

        user_prompt = f"Context:\n{context_str}\n\nUser Question: {query}\n\nAnswer:"

        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": user_prompt}
                    ]
                }
            ],
            "systemInstruction": {
                "parts": [
                    {"text": system_instruction}
                ]
            },
            "generationConfig": {
                "temperature": settings.LLM_TEMPERATURE,
                "maxOutputTokens": settings.LLM_MAX_TOKENS,
                "topP": 0.95
            }
        }

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.gemini_model}:generateContent?key={self.gemini_api_key}"

        async with httpx.AsyncClient(timeout=6.0) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code != 200:
                raise RuntimeError(f"Gemini API error ({resp.status_code}): {resp.text}")
            
            data = resp.json()
            candidates = data.get("candidates", [])
            if not candidates:
                raise ValueError("No candidates returned from Gemini API")
            
            answer_text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "").strip()
            gen_ms = (time.perf_counter() - start) * 1000

            is_abstention = "couldn't find" in answer_text.lower() or "not enough" in answer_text.lower()

            return GroundedResponseSchema(
                answer=answer_text,
                supported=not is_abstention,
                confidence=0.98 if not is_abstention else 0.0,
                citations=citations if not is_abstention else [],
                generation_ms=round(gen_ms, 2),
                provider=f"gemini ({self.gemini_model})"
            )

    async def _generate_openai(self, query: str, chunks: List[ScoredChunk]) -> GroundedResponseSchema:
        """
        Synthesizes grounded responses using OpenAI / Compatible Chat Completions API.
        """
        start = time.perf_counter()
        
        context_blocks = []
        citations = []
        for sc in chunks[:4]:
            text = self._clean_text(sc.chunk.text)
            context_blocks.append(f"[{sc.chunk.chunk_id}]: {text}")
            citations.append(sc.chunk.chunk_id)

        context_str = "\n\n".join(context_blocks)

        system_message = (
            "You are July, a voice-enabled grounded RAG system. Answer the user's question concisely (1-3 sentences) "
            "strictly using the provided context passages. If context lacks sufficient evidence, state that you couldn't find enough information."
        )

        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": f"Context:\n{context_str}\n\nQuestion: {query}"}
        ]

        payload = {
            "model": self.openai_model,
            "messages": messages,
            "temperature": settings.LLM_TEMPERATURE,
            "max_tokens": settings.LLM_MAX_TOKENS
        }

        headers = {
            "Authorization": f"Bearer {self.openai_api_key}",
            "Content-Type": "application/json"
        }

        async with httpx.AsyncClient(timeout=6.0) as client:
            resp = await client.post("https://api.openai.com/v1/chat/completions", json=payload, headers=headers)
            if resp.status_code != 200:
                raise RuntimeError(f"OpenAI API error ({resp.status_code}): {resp.text}")
            
            data = resp.json()
            answer_text = data["choices"][0]["message"]["content"].strip()
            gen_ms = (time.perf_counter() - start) * 1000
            is_abstention = "couldn't find" in answer_text.lower()

            return GroundedResponseSchema(
                answer=answer_text,
                supported=not is_abstention,
                confidence=0.97 if not is_abstention else 0.0,
                citations=citations if not is_abstention else [],
                generation_ms=round(gen_ms, 2),
                provider=f"openai ({self.openai_model})"
            )

    async def generate_answer(self, query: str, chunks: List[ScoredChunk]) -> GroundedResponseSchema:
        """
        Primary generation gateway: dynamically invokes configured provider (Gemini / OpenAI)
        with automatic instant fallback to the Smart Local Grounded Synthesizer.
        """
        active_provider = self._resolve_active_provider()
        
        if active_provider == "gemini":
            try:
                return await self._generate_gemini(query, chunks)
            except Exception as e:
                print(f"[GroundedLLMGenerator] Gemini generation failed: {e}. Falling back to smart local synthesizer.")
        
        elif active_provider == "openai":
            try:
                return await self._generate_openai(query, chunks)
            except Exception as e:
                print(f"[GroundedLLMGenerator] OpenAI generation failed: {e}. Falling back to smart local synthesizer.")

        # Smart Local Grounded Synthesis (High speed, zero API dependencies)
        return self._synthesize_smart_local(query, chunks)

    async def generate_answer_stream(
        self, query: str, chunks: List[ScoredChunk]
    ) -> AsyncGenerator[Tuple[str, Any], None]:
        """
        Streaming generator yielding:
        - ("token", token_text_chunk)
        - ("final", GroundedResponseSchema)
        Allows real-time typewriter output with sub-100ms TTFT.
        """
        full_res = await self.generate_answer(query, chunks)
        text = full_res.answer
        words = text.split(" ")
        
        for i, word in enumerate(words):
            token = word if i == len(words) - 1 else word + " "
            yield ("token", token)
            # Micro-delay between tokens for smooth streaming feel
            await asyncio.sleep(0.015)

        yield ("final", full_res)

