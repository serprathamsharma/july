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
from backend.generation.llm import GroundedLLMGenerator
from backend.analytics.store import analytics_store
from backend.cache.query_cache import query_cache

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
        self.query_guardrail = QueryGuardrail()
        self.retrieval_guardrail = RetrievalGuardrail()
        self.grounding_guardrail = GroundingGuardrail()
        self.llm_generator = GroundedLLMGenerator()

    async def execute_query(self, query: str, stt_ms: float = 0.0, mode: str = "RAG") -> RAGPipelineResponse:
        timer = RequestTimer(mode=mode)
        timer.metrics.stt_ms = round(stt_ms, 2)

        # Stage 1: Query Preprocessing, Normalization & Validation
        timer.start_step()
        q_val = self.query_guardrail.validate_query(query)
        timer.stop_step("query_processing_ms")
        
        # Use normalized query for retrieval and cache key
        normalized_query = self.query_guardrail.normalize_query(query)

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
                metrics=final_metrics
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

        # Stage 5: Score Fusion (RRF)
        t_fus_start = time.perf_counter()
        fused_chunks = reciprocal_rank_fusion(
            dense_results=dense_results,
            bm25_results=bm25_results,
            w_dense=strategy.w_dense,
            w_bm25=strategy.w_bm25,
            top_k=strategy.top_k
        )
        timer.metrics.fusion_ms = round((time.perf_counter() - t_fus_start) * 1000, 2)

        # Stage 6: Retrieval Guardrail (Evidence Relevance Check)
        t_guard_start = time.perf_counter()
        r_eval = self.retrieval_guardrail.evaluate_retrieval(fused_chunks)
        guard_ms = (time.perf_counter() - t_guard_start) * 1000

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
                metrics=final_metrics
            )

        # Stage 7: Grounded LLM Generation
        t_gen_start = time.perf_counter()
        llm_resp = await self.llm_generator.generate_answer(query, fused_chunks)
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
                metrics=final_metrics
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
            query=query,
            answer=llm_resp.answer,
            supported=llm_resp.supported,
            confidence=round(llm_resp.confidence, 3),
            citations=llm_resp.citations,
            retrieved_chunks=chunks_payload,
            metrics=final_metrics,
            provider=llm_resp.provider
        )

    async def execute_query_stream(self, query: str, stt_ms: float = 0.0, mode: str = "RAG"):
        """
        Async generator yielding SSE events:
        - {"type": "stage", "stage": "query_processing", "detail": "..."}
        - {"type": "token", "token": "..."}
        - {"type": "done", "response": RAGPipelineResponse}
        """
        import json
        timer = RequestTimer(mode=mode)
        timer.metrics.stt_ms = round(stt_ms, 2)

        # Stage 1: Validation
        timer.start_step()
        q_val = self.query_guardrail.validate_query(query)
        timer.stop_step("query_processing_ms")
        normalized_query = self.query_guardrail.normalize_query(query)

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
                metrics=final_metrics
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

        # Stage 5: RRF Fusion
        t_fus_start = time.perf_counter()
        fused_chunks = reciprocal_rank_fusion(
            dense_results=dense_results,
            bm25_results=bm25_results,
            w_dense=strategy.w_dense,
            w_bm25=strategy.w_bm25,
            top_k=strategy.top_k
        )
        timer.metrics.fusion_ms = round((time.perf_counter() - t_fus_start) * 1000, 2)

        # Stage 6: Retrieval Guardrail
        t_guard_start = time.perf_counter()
        r_eval = self.retrieval_guardrail.evaluate_retrieval(fused_chunks)
        guard_ms = (time.perf_counter() - t_guard_start) * 1000

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
                metrics=final_metrics
            )
            yield f"data: {json.dumps({'type': 'done', 'response': resp.model_dump()})}\n\n"
            return

        # Stage 7: Streaming Generation
        yield f"data: {json.dumps({'type': 'stage', 'stage': 'generating', 'detail': 'Generating grounded synthesis...'})}\n\n"
        t_gen_start = time.perf_counter()
        first_token = True
        llm_resp = None

        async for event_type, payload in self.llm_generator.generate_answer_stream(query, fused_chunks):
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
            query=query,
            answer=llm_resp.answer if llm_resp else "",
            supported=llm_resp.supported if llm_resp else False,
            confidence=round(llm_resp.confidence, 3) if llm_resp else 0.0,
            citations=llm_resp.citations if llm_resp else [],
            retrieved_chunks=chunks_payload,
            metrics=final_metrics,
            provider=llm_resp.provider if llm_resp else "grounded_local"
        )
        yield f"data: {json.dumps({'type': 'done', 'response': resp.model_dump()})}\n\n"

