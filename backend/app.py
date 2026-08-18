import os
import sys
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Add current path to sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.config.settings import settings
from backend.stt.sarvam import SarvamSTTProvider
from backend.voice.tts import SarvamTTSProvider
from backend.retrieval.faiss_index import FAISSVectorIndex
from backend.retrieval.bm25_index import BM25LexicalIndex
from backend.harness.orchestrator import RAGOrchestrator, RAGPipelineResponse
from backend.analytics.store import analytics_store
from backend.cache.query_cache import query_cache
from backend.guardrails.rate_limiter import RateLimitMiddleware

# Global index and orchestrator instances
faiss_idx = FAISSVectorIndex(
    index_type=settings.FAISS_INDEX_TYPE,
    hnsw_m=settings.FAISS_HNSW_M,
    hnsw_ef_search=settings.FAISS_HNSW_EF_SEARCH
)
bm25_idx = BM25LexicalIndex()
orchestrator: Optional[RAGOrchestrator] = None
stt_provider = SarvamSTTProvider()
tts_provider = SarvamTTSProvider()

@asynccontextmanager
async def lifespan(app: FastAPI):
    global orchestrator
    print("[FastAPI App Startup] Initializing local index binaries...")
    faiss_path = os.path.join(settings.INDEX_DIR, "faiss.index")
    meta_path = os.path.join(settings.INDEX_DIR, "chunks_metadata.pkl")
    bm25_path = os.path.join(settings.INDEX_DIR, "bm25.pkl")

    faiss_loaded = faiss_idx.load(faiss_path, meta_path)
    bm25_loaded = bm25_idx.load(bm25_path)

    if not faiss_loaded or not bm25_loaded:
        print("[FastAPI App Startup] Local indexes not detected. Executing ingestion pipeline...")
        from backend.ingestion.pipeline import run_ingestion_pipeline
        run_ingestion_pipeline()
        faiss_idx.load(faiss_path, meta_path)
        bm25_idx.load(bm25_path)

    orchestrator = RAGOrchestrator(faiss_index=faiss_idx, bm25_index=bm25_idx)

    # Warm up the embedding model and measure its latency on this hardware
    from backend.embeddings.encoder import EmbeddingEncoder
    encoder = EmbeddingEncoder()
    encoder.warmup()
    if encoder.is_fast:
        print(f"[Startup] Embedding model is fast on this hardware — using full hybrid retrieval (Dense + BM25)")
    else:
        print(f"[Startup] Embedding model is slow on this hardware — using BM25-only retrieval for sub-200ms SLA")

    # Reset analytics on startup to clear stale high-latency entries from previous deployments
    analytics_store.reset()

    print("[FastAPI App Startup] RAG Orchestrator successfully initialized and ready!")
    yield
    print("[FastAPI App Shutdown] Cleaning up resources.")

app = FastAPI(
    title="HH Goa 2026 — Voice-Enabled RAG API",
    description="Production-quality Voice-Enabled RAG System with VAST Chunking, RRF Hybrid Retrieval, Guardrails & Latency Instrumentation",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(RateLimitMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class TextQueryRequest(BaseModel):
    query: str
    mode: str = "RAG"  # RAG or End-to-End
    session_id: Optional[str] = None

class TTSRequest(BaseModel):
    text: str
    language_code: Optional[str] = "en-IN"
    speaker: Optional[str] = None

class FeedbackRequest(BaseModel):
    request_id: str
    rating: str  # 'up' or 'down'
    comment: Optional[str] = None

class IngestDocumentRequest(BaseModel):
    document_id: str
    text: str
    language: Optional[str] = "en"
    metadata: Optional[Dict[str, Any]] = None

@app.post("/api/feedback")
async def record_user_feedback(req: FeedbackRequest):
    """Records thumbs-up or thumbs-down user feedback for model fine-tuning and telemetry."""
    if not req.request_id or req.rating not in ["up", "down"]:
        raise HTTPException(status_code=400, detail="Invalid feedback payload: request_id and rating ('up'/'down') required.")
    analytics_store.record_feedback(request_id=req.request_id, rating=req.rating, comment=req.comment)
    return {"status": "success", "message": "Feedback recorded", "feedback": analytics_store.sqlite_store.get_feedback_summary()}

@app.post("/api/ingest")
async def ingest_document(req: IngestDocumentRequest):
    """Hot-reloads and indexes a new document into FAISS and BM25 indexes live."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="RAG Orchestrator is initializing")
    if not req.document_id or not req.text:
        raise HTTPException(status_code=400, detail="Both document_id and text are required.")
    return orchestrator.add_document(document_id=req.document_id, text=req.text, language=req.language or "en")

@app.get("/api/health")
async def health_check():
    return {
        "status": "online",
        "system": "HH Goa 2026 Voice-Enabled RAG",
        "environment": settings.ENVIRONMENT,
        "index_type": settings.FAISS_INDEX_TYPE,
        "indexed_documents": len(set(c.document_id for c in faiss_idx.chunks)),
        "indexed_chunks": len(faiss_idx.chunks),
        "cache": query_cache.get_stats(),
        "sqlite_persisted": True,
        "sarvam_stt_configured": bool(settings.SARVAM_API_KEY and not settings.SARVAM_API_KEY.startswith("your_")),
        "sarvam_tts_configured": bool(settings.SARVAM_API_KEY and not settings.SARVAM_API_KEY.startswith("your_")),
        "gemini_llm_configured": bool(settings.GEMINI_API_KEY and not settings.GEMINI_API_KEY.startswith("your_"))
    }

@app.get("/api/cache/stats")
async def get_cache_stats():
    return query_cache.get_stats()

@app.post("/api/cache/clear")
async def clear_cache():
    query_cache.clear()
    return {"status": "cleared", "cache": query_cache.get_stats()}

@app.post("/api/voice/tts")
async def synthesize_speech(req: TTSRequest):
    return await tts_provider.synthesize(
        text=req.text,
        target_language_code=req.language_code or "en-IN",
        speaker=req.speaker
    )

@app.post("/api/text/query", response_model=RAGPipelineResponse)
async def process_text_query(req: TextQueryRequest):
    if not orchestrator:
        raise HTTPException(status_code=503, detail="RAG Orchestrator is initializing")
    return await orchestrator.execute_query(query=req.query, mode=req.mode, session_id=req.session_id)

@app.post("/api/text/query/stream")
async def process_text_query_stream(req: TextQueryRequest):
    if not orchestrator:
        raise HTTPException(status_code=503, detail="RAG Orchestrator is initializing")
    return StreamingResponse(
        orchestrator.execute_query_stream(query=req.query, mode=req.mode, session_id=req.session_id),
        media_type="text/event-stream"
    )

@app.post("/api/voice/query", response_model=RAGPipelineResponse)
async def process_voice_query(
    file: UploadFile = File(...),
    language_code: Optional[str] = Form("en-IN"),
    session_id: Optional[str] = Form(None)
):
    if not orchestrator:
        raise HTTPException(status_code=503, detail="RAG Orchestrator is initializing")
    
    audio_bytes = await file.read()
    stt_res = await stt_provider.transcribe_audio(
        audio_bytes=audio_bytes,
        filename=file.filename or "audio.wav",
        language_code=language_code
    )
    
    transcribed_text = stt_res.get("text", "")
    stt_ms = stt_res.get("stt_ms", 0.0)

    if not transcribed_text:
        raise HTTPException(status_code=400, detail=stt_res.get("error", "Failed to transcribe audio speech."))

    pipeline_resp = await orchestrator.execute_query(
        query=transcribed_text,
        stt_ms=stt_ms,
        mode="End-to-End",
        session_id=session_id
    )
    pipeline_resp.transcription = transcribed_text
    return pipeline_resp

@app.get("/api/analytics")
async def get_analytics():
    return analytics_store.get_analytics_summary()

@app.get("/api/sources/{chunk_id}")
async def get_source_detail(chunk_id: str):
    match = next((c for c in faiss_idx.chunks if c.chunk_id == chunk_id), None)
    if not match:
        raise HTTPException(status_code=404, detail=f"Source chunk '{chunk_id}' not found.")
    
    return {
        "chunk_id": match.chunk_id,
        "document_id": match.document_id,
        "chunk_type": match.chunk_type,
        "position": match.position,
        "language": match.language,
        "word_count": match.word_count,
        "text": match.text,
        "parent_document": match.parent_document
    }

@app.get("/api/knowledge-graph")
async def get_knowledge_graph():
    from backend.retrieval.knowledge_graph import knowledge_graph
    return knowledge_graph.get_graph()

@app.post("/api/benchmark/run")
async def trigger_benchmark(background_tasks: BackgroundTasks):
    from evaluation.benchmark import run_benchmark_suite
    return await run_benchmark_suite()
