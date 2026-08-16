import os
import asyncio
import time
from typing import Dict, Any, Optional, List
from pydantic import BaseModel

from backend.config.settings import settings
from backend.harness.metrics import RequestTimer, LatencyMetrics
from backend.guardrails.query_guardrail import QueryGuardrail
from backend.guardrails.retrieval_guardrail import RetrievalGuardrail
from backend.guardrails.grounding_guardrail import GroundingGuardrail
from backend.retrieval.router import AdaptiveRetrievalRouter
from backend.embeddings.encoder import EmbeddingEncoder
from backend.retrieval.faiss_index import FAISSVectorIndex
from backend.retrieval.bm25_index import BM25LexicalIndex
from backend.retrieval.rrf import reciprocal_rank_fusion, ScoredChunk
from backend.retrieval.reranker import CrossEncoderReranker
from backend.generation.llm import GroundedLLMGenerator
from backend.analytics.store import analytics_store
from backend.cache.query_cache import query_cache
import re

class SessionContextManager:
    """
    Maintains sliding multi-turn conversation memory and automatically
    rewrites ambiguous follow-up queries using coreference and entity resolution.
    """
    def __init__(self, max_history: int = 6):
        self.sessions: Dict[str, List[Dict[str, str]]] = {}
        self.max_history = max_history

    def get_history(self, session_id: str) -> List[Dict[str, str]]:
        return self.sessions.get(session_id, [])

    def record_turn(self, session_id: Optional[str], user_query: str, system_answer: str):
        if not session_id:
            return
        if session_id not in self.sessions:
            self.sessions[session_id] = []
        self.sessions[session_id].append({"query": user_query, "answer": system_answer})
        if len(self.sessions[session_id]) > self.max_history:
            self.sessions[session_id].pop(0)

    def contextualize_query(self, query: str, session_id: Optional[str]) -> str:
        """
        Rewrites follow-up queries by replacing pronouns ('it', 'they', 'this', 'that')
        with the primary subject entity from the previous conversation turn.
        """
        if not session_id or session_id not in self.sessions or not self.sessions[session_id]:
            return query

        last_turn = self.sessions[session_id][-1]
        last_query = last_turn["query"]
        
        pronoun_patterns = [
            r'\b(it|its|they|them|their|this|that|the tool|the framework|the dataset|the library|the scheme)\b'
        ]
        has_pronoun = any(re.search(pat, query, re.IGNORECASE) for pat in pronoun_patterns)
        
        if has_pronoun:
            # 1. Look for acronym or domain entity in previous turn (excluding question words)
            stop_entities = {"what", "how", "why", "where", "when", "which", "who", "tell", "explain", "describe", "can", "could", "is", "are", "the"}
            candidates = re.findall(r'\b([A-Z]{2,}(?:-[A-Z0-9]+)?|[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b', last_query)
            valid_candidates = [c for c in candidates if c.lower() not in stop_entities]
            
            subject = valid_candidates[0] if valid_candidates else ""
            if not subject:
                m = re.search(r'\b(?:what is|how does|tell me about|explain|describe)\s+([a-zA-Z0-9_\-]+)\b', last_query, re.IGNORECASE)
                if m and m.group(1).lower() not in stop_entities:
                    subject = m.group(1).upper()
            
            if subject:
                rewritten = re.sub(
                    r'\b(it|its|they|them|their|this|that|the tool|the framework|the dataset|the library|the scheme)\b',
                    subject,
                    query,
                    flags=re.IGNORECASE
                )
                print(f"[SessionContextManager] Contextualized follow-up: '{query}' -> '{rewritten}'")
                return rewritten

        return query

class RAGPipelineResponse(BaseModel):
    request_id: str
    query: str
    transcription: Optional[str] = None
    answer: str
    supported: bool
    confidence: float
    citations: List[str]
    retrieved_chunks: List[Dict[str, Any]]
    metrics: LatencyMetrics
    provider: str = "grounded_local"
    session_id: Optional[str] = None

class RAGOrchestrator:
    def __init__(
        self,
        faiss_index: Optional[FAISSVectorIndex] = None,
        bm25_index: Optional[BM25LexicalIndex] = None
    ):
        self.encoder = EmbeddingEncoder()
        self.faiss_index = faiss_index or FAISSVectorIndex()
        self.bm25_index = bm25_index or BM25LexicalIndex()
        
        self.router = AdaptiveRetrievalRouter()
        self.reranker = CrossEncoderReranker()
        self.session_manager = SessionContextManager()
        self.query_guardrail = QueryGuardrail()
        self.retrieval_guardrail = RetrievalGuardrail()
        self.grounding_guardrail = GroundingGuardrail()
        self.llm_generator = GroundedLLMGenerator()

    def add_document(self, document_id: str, text: str, language: str = "en") -> Dict[str, Any]:
        """
        Dynamically ingests a new document into FAISS and BM25 indexes at runtime (Hot-Reload).
        Clears query cache to immediately serve fresh ground truth knowledge.
        """
        from backend.chunking.vast import VASTChunker
        chunker = VASTChunker(target_semantic_words=120, overlap_words=25)
        res = chunker.process_document(document_id, text, language)
        new_chunks = res["all"]

        if not new_chunks:
            return {"status": "skipped", "message": "No valid chunks extracted from document"}

        # 1. Encode dense embeddings
        chunk_texts = [c.text for c in new_chunks]
        embeddings = self.encoder.encode(chunk_texts)

        # 2. Add to FAISS index
        self.faiss_index.add_chunks(new_chunks, embeddings)

        # 3. Add to BM25 index
        self.bm25_index.add_chunks(new_chunks)

        # 4. Save snapshots to disk
        faiss_path = os.path.join(settings.INDEX_DIR, "faiss.index")
        meta_path = os.path.join(settings.INDEX_DIR, "chunks_metadata.pkl")
        bm25_path = os.path.join(settings.INDEX_DIR, "bm25.pkl")
        self.faiss_index.save(faiss_path, meta_path)
        self.bm25_index.save(bm25_path)

        # 5. Clear query cache so new knowledge takes effect immediately
        query_cache.clear()

        # 6. Update analytics store
        analytics_store.indexed_documents = len(set(c.document_id for c in self.faiss_index.chunks))
        analytics_store.indexed_chunks = len(self.faiss_index.chunks)

        return {
            "status": "success",
            "document_id": document_id,
            "new_chunks_count": len(new_chunks),
            "total_indexed_chunks": len(self.faiss_index.chunks),
            "total_indexed_documents": analytics_store.indexed_documents
        }

    async def execute_query(
        self, query: str, stt_ms: float = 0.0, mode: str = "RAG", session_id: Optional[str] = None
    ) -> RAGPipelineResponse:
        timer = RequestTimer(mode=mode)
        timer.metrics.stt_ms = round(stt_ms, 2)

        # Stage 0: Multi-Turn Context De-referencing
        contextualized_q = self.session_manager.contextualize_query(query, session_id)

        # Stage 1: Query Preprocessing, Normalization & Validation
        timer.start_step()
        q_val = self.query_guardrail.validate_query(contextualized_q)
        timer.stop_step("query_processing_ms")
        
        # Use normalized query for retrieval and cache key
        normalized_query = self.query_guardrail.normalize_query(contextualized_q)

        if not q_val["valid"]:
            timer.stop_step("guardrail_ms")
            final_metrics = timer.finalize()
            analytics_store.record_request(final_metrics, guardrail_event=q_val.get("reason", "query_rejected"))
            return RAGPipelineResponse(
                request_id=timer.request_id,
                query=normalized_query or query,
                answer=q_val["message"],
                supported=q_val.get("supported", False),
                confidence=q_val.get("confidence", 0.0),
                citations=[],
                retrieved_chunks=[],
                metrics=final_metrics,
                session_id=session_id
            )

        # Cache check: Fast Tier 1 / Tier 2 in-memory cache lookup (< 1ms)
        if settings.ENABLE_QUERY_CACHE:
            cached_result = query_cache.get(normalized_query)
            if cached_result:
                cached_data, hit_type = cached_result
                timer.metrics.cache_hit = True
                timer.metrics.cache_type = hit_type
                final_metrics = timer.finalize()
                analytics_store.record_request(final_metrics)
                
                resp = RAGPipelineResponse(
                    request_id=timer.request_id,
                    query=query,
                    answer=cached_data["answer"],
                    supported=cached_data["supported"],
                    confidence=cached_data["confidence"],
                    citations=cached_data["citations"],
                    retrieved_chunks=cached_data.get("retrieved_chunks", []),
                    metrics=final_metrics,
                    provider=f"{cached_data.get('provider', 'grounded_local')} (cached {hit_type})"
                )
                return resp

        # Stage 2: Routing Strategy
        strategy = self.router.route_query(normalized_query)

        # Stage 3 & 4: Adaptive Retrieval — skip expensive dense embedding when hardware is too slow
        q_emb = None
        if self.encoder.is_fast:
            # Fast hardware: Full hybrid retrieval (Dense + BM25)
            timer.start_step()
            q_emb = self.encoder.encode(normalized_query)
            timer.stop_step("embedding_ms")

            async def run_dense():
                d_start = time.perf_counter()
                res = self.faiss_index.search(q_emb, k=strategy.top_k * 2)
                d_ms = (time.perf_counter() - d_start) * 1000
                return res, d_ms

            async def run_bm25():
                b_start = time.perf_counter()
                res = self.bm25_index.search(normalized_query, k=strategy.top_k * 2)
                b_ms = (time.perf_counter() - b_start) * 1000
                return res, b_ms

            (dense_results, dense_ms), (bm25_results, bm25_ms) = await asyncio.gather(
                run_dense(),
                run_bm25()
            )

            timer.metrics.dense_retrieval_ms = round(dense_ms, 2)
            timer.metrics.bm25_ms = round(bm25_ms, 2)
        else:
            # Slow hardware (Railway CPU): BM25-only retrieval — skips 14s embedding encode
            timer.metrics.embedding_ms = 0.0
            timer.metrics.dense_retrieval_ms = 0.0

            timer.start_step()
            bm25_results = self.bm25_index.search(normalized_query, k=strategy.top_k * 2)
            bm25_ms = timer.stop_step("bm25_ms")

            dense_results = []

        # Stage 5: Score Fusion (RRF) & Cross-Encoder Re-Ranking
        t_fus_start = time.perf_counter()
        fused_chunks = reciprocal_rank_fusion(
            dense_results=dense_results,
            bm25_results=bm25_results,
            w_dense=strategy.w_dense,
            w_bm25=strategy.w_bm25,
            top_k=strategy.top_k * 2
        )
        # Two-Stage Re-ranking with Cross-Encoder
        fused_chunks = self.reranker.rerank(normalized_query, fused_chunks, top_k=strategy.top_k)
        timer.metrics.fusion_ms = round((time.perf_counter() - t_fus_start) * 1000, 2)

        # Stage 6: Retrieval Guardrail (Evidence Relevance Check) & Corrective RAG (CRAG) Fallback
        t_guard_start = time.perf_counter()
        r_eval = self.retrieval_guardrail.evaluate_retrieval(fused_chunks)
        guard_ms = (time.perf_counter() - t_guard_start) * 1000

        if not r_eval["passed"]:
            # CRAG: Attempt Corrective Query Reformulation
            reformulated = self.query_guardrail.reformulate_query(normalized_query)
            if reformulated and reformulated != normalized_query:
                print(f"[Corrective RAG] Triggering secondary retrieval pass with: '{reformulated}'")
                bm25_secondary = self.bm25_index.search(reformulated, k=strategy.top_k * 2)
                if bm25_secondary:
                    sec_fused = reciprocal_rank_fusion([], bm25_secondary, w_dense=0.0, w_bm25=1.0, top_k=strategy.top_k)
                    sec_fused = self.reranker.rerank(reformulated, sec_fused, top_k=strategy.top_k)
                    sec_eval = self.retrieval_guardrail.evaluate_retrieval(sec_fused)
                    if sec_eval["passed"]:
                        fused_chunks = sec_fused
                        r_eval = sec_eval

        if not r_eval["passed"]:
            timer.metrics.guardrail_ms = round(guard_ms, 2)
            final_metrics = timer.finalize()
            analytics_store.record_request(final_metrics, guardrail_event="low_confidence")
            return RAGPipelineResponse(
                request_id=timer.request_id,
                query=query,
                answer=r_eval["message"],
                supported=False,
                confidence=r_eval["confidence"],
                citations=[],
                retrieved_chunks=[],
                metrics=final_metrics,
                session_id=session_id
            )

        # Stage 7: Parent-Child Context Expansion & Grounded LLM Generation
        generation_chunks = []
        for sc in fused_chunks:
            # If sentence chunk, expand text with parent document context for comprehensive synthesis
            chunk_copy = sc.chunk.model_copy()
            if chunk_copy.chunk_type == "sentence" and chunk_copy.parent_document:
                chunk_copy.text = chunk_copy.parent_document
            generation_chunks.append(ScoredChunk(
                chunk=chunk_copy,
                rrf_score=sc.rrf_score,
                dense_score=sc.dense_score,
                bm25_score=sc.bm25_score
            ))

        t_gen_start = time.perf_counter()
        llm_resp = await self.llm_generator.generate_answer(query, generation_chunks)
        gen_ms = (time.perf_counter() - t_gen_start) * 1000
        timer.metrics.generation_ms = round(gen_ms, 2)

        # Stage 8: Grounding Verification Guardrail
        t_gver_start = time.perf_counter()
        g_val = self.grounding_guardrail.verify_grounding(llm_resp.answer, fused_chunks)
        total_guard_ms = guard_ms + (time.perf_counter() - t_gver_start) * 1000
        timer.metrics.guardrail_ms = round(total_guard_ms, 2)

        if not g_val["grounded"]:
            final_metrics = timer.finalize()
            analytics_store.record_request(final_metrics, guardrail_event="grounding_failure")
            return RAGPipelineResponse(
                request_id=timer.request_id,
                query=query,
                answer="I couldn't find enough relevant information in the knowledge base to answer that.",
                supported=False,
                confidence=0.0,
                citations=[],
                retrieved_chunks=[],
                metrics=final_metrics,
                session_id=session_id
            )

        # Format retrieved chunks summary for frontend / Source Explorer
        chunks_payload = []
        for sc in fused_chunks:
            chunks_payload.append({
                "chunk_id": sc.chunk.chunk_id,
                "document_id": sc.chunk.document_id,
                "chunk_type": sc.chunk.chunk_type,
                "text": sc.chunk.text,
                "rrf_score": sc.rrf_score,
                "dense_score": sc.dense_score,
                "bm25_score": sc.bm25_score,
                "parent_document": sc.chunk.parent_document,
                "position": sc.chunk.position
            })

        final_metrics = timer.finalize()
        analytics_store.record_request(final_metrics)

        # Record conversation turn in multi-turn memory
        self.session_manager.record_turn(session_id, query, llm_resp.answer)

        # Save to cache
        if settings.ENABLE_QUERY_CACHE and llm_resp.supported:
            query_cache.put(
                query=normalized_query,
                response_data={
                    "answer": llm_resp.answer,
                    "supported": llm_resp.supported,
                    "confidence": round(llm_resp.confidence, 3),
                    "citations": llm_resp.citations,
                    "retrieved_chunks": chunks_payload,
                    "provider": llm_resp.provider
                },
                query_embedding=q_emb
            )

        return RAGPipelineResponse(
            request_id=timer.request_id,
            query=normalized_query,
            answer=llm_resp.answer,
            supported=llm_resp.supported,
            confidence=round(llm_resp.confidence, 3),
            citations=llm_resp.citations,
            retrieved_chunks=chunks_payload,
            metrics=final_metrics,
            provider=llm_resp.provider,
            session_id=session_id
        )

    async def execute_query_stream(
        self, query: str, stt_ms: float = 0.0, mode: str = "RAG", session_id: Optional[str] = None
    ):
        """
        Async generator yielding SSE events with Re-ranking, Coreference Resolution, and CRAG:
        - {"type": "stage", "stage": "query_processing", "detail": "..."}
        - {"type": "token", "token": "..."}
        - {"type": "done", "response": RAGPipelineResponse}
        """
        import json
        timer = RequestTimer(mode=mode)
        timer.metrics.stt_ms = round(stt_ms, 2)

        # Stage 0: Contextualize
        contextualized_q = self.session_manager.contextualize_query(query, session_id)

        # Stage 1: Validation
        timer.start_step()
        q_val = self.query_guardrail.validate_query(contextualized_q)
        timer.stop_step("query_processing_ms")
        normalized_query = self.query_guardrail.normalize_query(contextualized_q)

        if not q_val["valid"]:
            timer.stop_step("guardrail_ms")
            final_metrics = timer.finalize()
            analytics_store.record_request(final_metrics, guardrail_event=q_val.get("reason", "query_rejected"))
            yield f"data: {json.dumps({'type': 'token', 'token': q_val['message']})}\n\n"
            resp = RAGPipelineResponse(
                request_id=timer.request_id,
                query=normalized_query or query,
                answer=q_val["message"],
                supported=False,
                confidence=0.0,
                citations=[],
                retrieved_chunks=[],
                metrics=final_metrics,
                session_id=session_id
            )
            yield f"data: {json.dumps({'type': 'done', 'response': resp.model_dump()})}\n\n"
            return

        # Cache check
        if settings.ENABLE_QUERY_CACHE:
            cached_result = query_cache.get(normalized_query)
            if cached_result:
                cached_data, hit_type = cached_result
                timer.metrics.cache_hit = True
                timer.metrics.cache_type = hit_type
                timer.metrics.ttft_ms = round((time.perf_counter() - timer.start_time) * 1000, 2)
                
                # Stream cached answer tokens
                words = cached_data["answer"].split(" ")
                for i, w in enumerate(words):
                    tok = w if i == len(words) - 1 else w + " "
                    yield f"data: {json.dumps({'type': 'token', 'token': tok})}\n\n"
                    await asyncio.sleep(0.008)

                final_metrics = timer.finalize()
                analytics_store.record_request(final_metrics)
                self.session_manager.record_turn(session_id, query, cached_data["answer"])
                
                resp = RAGPipelineResponse(
                    request_id=timer.request_id,
                    query=query,
                    answer=cached_data["answer"],
                    supported=cached_data["supported"],
                    confidence=cached_data["confidence"],
                    citations=cached_data["citations"],
                    retrieved_chunks=cached_data.get("retrieved_chunks", []),
                    metrics=final_metrics,
                    provider=f"{cached_data.get('provider', 'grounded_local')} (cached {hit_type})",
                    session_id=session_id
                )
                yield f"data: {json.dumps({'type': 'done', 'response': resp.model_dump()})}\n\n"
                return

        # Stage 2: Routing
        yield f"data: {json.dumps({'type': 'stage', 'stage': 'retrieval', 'detail': 'Routing & retrieving evidence...'})}\n\n"
        strategy = self.router.route_query(normalized_query)

        # Stage 3 & 4: Retrieval
        q_emb = None
        if self.encoder.is_fast:
            timer.start_step()
            q_emb = self.encoder.encode(normalized_query)
            timer.stop_step("embedding_ms")

            async def run_dense():
                d_start = time.perf_counter()
                res = self.faiss_index.search(q_emb, k=strategy.top_k * 2)
                return res, (time.perf_counter() - d_start) * 1000

            async def run_bm25():
                b_start = time.perf_counter()
                res = self.bm25_index.search(normalized_query, k=strategy.top_k * 2)
                return res, (time.perf_counter() - b_start) * 1000

            (dense_results, dense_ms), (bm25_results, bm25_ms) = await asyncio.gather(run_dense(), run_bm25())
            timer.metrics.dense_retrieval_ms = round(dense_ms, 2)
            timer.metrics.bm25_ms = round(bm25_ms, 2)
        else:
            timer.metrics.embedding_ms = 0.0
            timer.metrics.dense_retrieval_ms = 0.0
            timer.start_step()
            bm25_results = self.bm25_index.search(normalized_query, k=strategy.top_k * 2)
            timer.stop_step("bm25_ms")
            dense_results = []

        # Stage 5: RRF Fusion & Cross-Encoder Re-Ranking
        t_fus_start = time.perf_counter()
        fused_chunks = reciprocal_rank_fusion(
            dense_results=dense_results,
            bm25_results=bm25_results,
            w_dense=strategy.w_dense,
            w_bm25=strategy.w_bm25,
            top_k=strategy.top_k * 2
        )
        fused_chunks = self.reranker.rerank(normalized_query, fused_chunks, top_k=strategy.top_k)
        timer.metrics.fusion_ms = round((time.perf_counter() - t_fus_start) * 1000, 2)

        # Stage 6: Retrieval Guardrail & CRAG
        t_guard_start = time.perf_counter()
        r_eval = self.retrieval_guardrail.evaluate_retrieval(fused_chunks)
        guard_ms = (time.perf_counter() - t_guard_start) * 1000

        if not r_eval["passed"]:
            reformulated = self.query_guardrail.reformulate_query(normalized_query)
            if reformulated and reformulated != normalized_query:
                bm25_sec = self.bm25_index.search(reformulated, k=strategy.top_k * 2)
                if bm25_sec:
                    sec_fused = reciprocal_rank_fusion([], bm25_sec, w_dense=0.0, w_bm25=1.0, top_k=strategy.top_k)
                    sec_fused = self.reranker.rerank(reformulated, sec_fused, top_k=strategy.top_k)
                    sec_eval = self.retrieval_guardrail.evaluate_retrieval(sec_fused)
                    if sec_eval["passed"]:
                        fused_chunks = sec_fused
                        r_eval = sec_eval

        if not r_eval["passed"]:
            timer.metrics.guardrail_ms = round(guard_ms, 2)
            final_metrics = timer.finalize()
            analytics_store.record_request(final_metrics, guardrail_event="low_confidence")
            yield f"data: {json.dumps({'type': 'token', 'token': r_eval['message']})}\n\n"
            resp = RAGPipelineResponse(
                request_id=timer.request_id,
                query=query,
                answer=r_eval["message"],
                supported=False,
                confidence=r_eval["confidence"],
                citations=[],
                retrieved_chunks=[],
                metrics=final_metrics,
                session_id=session_id
            )
            yield f"data: {json.dumps({'type': 'done', 'response': resp.model_dump()})}\n\n"
            return

        # Stage 7: Parent-Child Context Expansion & Streaming Generation
        yield f"data: {json.dumps({'type': 'stage', 'stage': 'generating', 'detail': 'Generating grounded synthesis...'})}\n\n"
        generation_chunks = []
        for sc in fused_chunks:
            chunk_copy = sc.chunk.model_copy()
            if chunk_copy.chunk_type == "sentence" and chunk_copy.parent_document:
                chunk_copy.text = chunk_copy.parent_document
            generation_chunks.append(ScoredChunk(
                chunk=chunk_copy,
                rrf_score=sc.rrf_score,
                dense_score=sc.dense_score,
                bm25_score=sc.bm25_score
            ))

        t_gen_start = time.perf_counter()
        first_token = True
        llm_resp = None

        async for event_type, payload in self.llm_generator.generate_answer_stream(query, generation_chunks):
            if event_type == "token":
                if first_token:
                    timer.metrics.ttft_ms = round((time.perf_counter() - timer.start_time) * 1000, 2)
                    first_token = False
                yield f"data: {json.dumps({'type': 'token', 'token': payload})}\n\n"
            elif event_type == "final":
                llm_resp = payload

        gen_ms = (time.perf_counter() - t_gen_start) * 1000
        timer.metrics.generation_ms = round(gen_ms, 2)

        # Stage 8: Grounding Verification
        t_gver_start = time.perf_counter()
        g_val = self.grounding_guardrail.verify_grounding(llm_resp.answer, fused_chunks) if llm_resp else {"grounded": True}
        total_guard_ms = guard_ms + (time.perf_counter() - t_gver_start) * 1000
        timer.metrics.guardrail_ms = round(total_guard_ms, 2)

        chunks_payload = [{
            "chunk_id": sc.chunk.chunk_id,
            "document_id": sc.chunk.document_id,
            "chunk_type": sc.chunk.chunk_type,
            "text": sc.chunk.text,
            "rrf_score": sc.rrf_score,
            "dense_score": sc.dense_score,
            "bm25_score": sc.bm25_score,
            "parent_document": sc.chunk.parent_document,
            "position": sc.chunk.position
        } for sc in fused_chunks]

        final_metrics = timer.finalize()
        analytics_store.record_request(final_metrics)

        # Record conversation turn
        if llm_resp:
            self.session_manager.record_turn(session_id, query, llm_resp.answer)

        # Save to cache
        if settings.ENABLE_QUERY_CACHE and llm_resp and llm_resp.supported and g_val["grounded"]:
            query_cache.put(
                query=normalized_query,
                response_data={
                    "answer": llm_resp.answer,
                    "supported": llm_resp.supported,
                    "confidence": round(llm_resp.confidence, 3),
                    "citations": llm_resp.citations,
                    "retrieved_chunks": chunks_payload,
                    "provider": llm_resp.provider
                },
                query_embedding=q_emb
            )

        resp = RAGPipelineResponse(
            request_id=timer.request_id,
            query=normalized_query,
            answer=llm_resp.answer if llm_resp else "",
            supported=llm_resp.supported if llm_resp else False,
            confidence=round(llm_resp.confidence, 3) if llm_resp else 0.0,
            citations=llm_resp.citations if llm_resp else [],
            retrieved_chunks=chunks_payload,
            metrics=final_metrics,
            provider=llm_resp.provider if llm_resp else "grounded_local",
            session_id=session_id
        )
        yield f"data: {json.dumps({'type': 'done', 'response': resp.model_dump()})}\n\n"


