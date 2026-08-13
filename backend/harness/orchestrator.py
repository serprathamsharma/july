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

        # Stage 1: Query Preprocessing & Validation
        timer.start_step()
        q_val = self.query_guardrail.validate_query(query)
        timer.stop_step("query_processing_ms")

        if not q_val["valid"]:
            timer.stop_step("guardrail_ms")
            final_metrics = timer.finalize()
            analytics_store.record_request(final_metrics, guardrail_event="query_rejected")
            return RAGPipelineResponse(
                request_id=timer.request_id,
                query=query,
                answer=q_val["message"],
                supported=False,
                confidence=0.0,
                citations=[],
                retrieved_chunks=[],
                metrics=final_metrics
            )

        # Stage 2: Routing Strategy
        strategy = self.router.route_query(query)

        # Stage 3: Embedding Generation
        timer.start_step()
        q_emb = self.encoder.encode(query)
        timer.stop_step("embedding_ms")

        # Stage 4: Concurrent Parallel Retrieval (Dense + BM25)
        t_ret_start = time.perf_counter()
        
        async def run_dense():
            d_start = time.perf_counter()
            res = self.faiss_index.search(q_emb, k=strategy.top_k * 2)
            d_ms = (time.perf_counter() - d_start) * 1000
            return res, d_ms

        async def run_bm25():
            b_start = time.perf_counter()
            res = self.bm25_index.search(query, k=strategy.top_k * 2)
            b_ms = (time.perf_counter() - b_start) * 1000
            return res, b_ms

        (dense_results, dense_ms), (bm25_results, bm25_ms) = await asyncio.gather(
            run_dense(),
            run_bm25()
        )

        timer.metrics.dense_retrieval_ms = round(dense_ms, 2)
        timer.metrics.bm25_ms = round(bm25_ms, 2)

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

        return RAGPipelineResponse(
            request_id=timer.request_id,
            query=query,
            answer=llm_resp.answer,
            supported=llm_resp.supported,
            confidence=round(llm_resp.confidence, 3),
            citations=llm_resp.citations,
            retrieved_chunks=chunks_payload,
            metrics=final_metrics
        )
