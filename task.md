# HH Goa 2026 — Voice RAG Enhancement Task Tracker

This document tracks engineering tasks, architecture optimizations, and intelligence upgrades for the **HH Goa 2026 Voice-Enabled RAG System**.

---

## 🚀 Phase 1: Speed & Latency Optimizations (Sub-50ms SLA)

- [x] **1.1 Server-Sent Events (SSE) / WebSocket Streaming**
  - [x] Add `/api/query/stream` endpoint in [`backend/app.py`](file:///c:/Users/prath/OneDrive/Desktop/projects/july/backend/app.py) using FastAPI `StreamingResponse`.
  - [x] Integrate generator token streaming in [`backend/generation/llm.py`](file:///c:/Users/prath/OneDrive/Desktop/projects/july/backend/generation/llm.py).
  - [x] Update frontend audio & text handlers in [`frontend/src/App.tsx`](file:///c:/Users/prath/OneDrive/Desktop/projects/july/frontend/src/App.tsx) to consume SSE streams.
  - [x] Measure Time-To-First-Token (TTFT < 150ms).

- [x] **1.2 High-Performance Semantic & Exact Query Caching**
  - [x] Implement in-memory LRU exact hash cache (`<1ms` hit latency).
  - [x] Implement vector cosine similarity cache for synonymous queries ($\ge 0.96$ threshold, `<5ms` hit latency).
  - [x] Add cache hit/miss instrumentation into [`backend/harness/metrics.py`](file:///c:/Users/prath/OneDrive/Desktop/projects/july/backend/harness/metrics.py).

- [ ] **1.3 Embedding Model Quantization & Acceleration**
  - [ ] Benchmark ONNX Runtime with INT8 quantization for `sentence-transformers` models (`fastembed` or ONNX provider).
  - [ ] Optimize cold-start loading time in [`backend/embeddings/encoder.py`](file:///c:/Users/prath/OneDrive/Desktop/projects/july/backend/embeddings/encoder.py).

- [x] **1.4 FAISS HNSW Scaled Indexing**
  - [x] Add support for `IndexHNSWFlat` alongside `IndexFlatIP` in [`backend/retrieval/faiss_index.py`](file:///c:/Users/prath/OneDrive/Desktop/projects/july/backend/retrieval/faiss_index.py).
  - [x] Tune $M$ (connectivity) and `efSearch` parameters for millisecond retrieval at scale ($100\text{k}+$ passages).

---

## 🧠 Phase 2: Retrieval Intelligence & Grounding Upgrades

- [ ] **2.1 Two-Stage Retrieval with Cross-Encoder Re-Ranking**
  - [ ] Add lightweight re-ranker stage (FlashRank / `bge-reranker-small`) after RRF fusion in [`backend/harness/orchestrator.py`](file:///c:/Users/prath/OneDrive/Desktop/projects/july/backend/harness/orchestrator.py).
  - [ ] Re-score top-15 candidate chunks down to top-3 highest precision chunks.
  - [ ] Evaluate improvement in Precision@1 and MRR using [`evaluation/benchmark.py`](file:///c:/Users/prath/OneDrive/Desktop/projects/july/evaluation/benchmark.py).

- [ ] **2.2 Parent-Child / Hierarchical Chunk Retrieval**
  - [ ] Enhance VAST chunking in [`backend/ingestion/chunker.py`](file:///c:/Users/prath/OneDrive/Desktop/projects/july/backend/ingestion/chunker.py) to store parent document & section IDs with sentence chunks.
  - [ ] Perform vector similarity on small sentence chunks, but expand context to parent paragraph for LLM prompt generation.

- [ ] **2.3 HyDE & Voice Query Expansion**
  - [ ] Implement zero-shot query expansion for short or ambiguous voice queries.
  - [ ] Add domain synonym substitution in [`backend/guardrails/query_guardrail.py`](file:///c:/Users/prath/OneDrive/Desktop/projects/july/backend/guardrails/query_guardrail.py).

- [ ] **2.4 Multi-Turn Conversational Memory**
  - [ ] Implement conversational session buffer in [`backend/harness/orchestrator.py`](file:///c:/Users/prath/OneDrive/Desktop/projects/july/backend/harness/orchestrator.py).
  - [ ] Add contextual query rewriting for follow-up questions (*"What else does it do?"* $\rightarrow$ resolved entity question).

- [ ] **2.5 Corrective RAG (CRAG) & Self-Reflection**
  - [ ] If retrieval score falls into marginal confidence ($0.50 \le \text{conf} < 0.70$), automatically trigger query reformulation before abstaining.
  - [ ] Enhance [`backend/guardrails/retrieval_guardrail.py`](file:///c:/Users/prath/OneDrive/Desktop/projects/july/backend/guardrails/retrieval_guardrail.py) with dynamic thresholding.

---

## 📊 Phase 3: Evaluation & Benchmarking

- [ ] Run baseline benchmarks on MSMARCO-XI test set:
  ```bash
  python -m evaluation.benchmark
  ```
- [ ] Measure and log:
  - **Latency Metrics:** P50, P70, P99, and TTFT
  - **Retrieval Quality:** Recall@k, Precision@k, MRR
  - **Grounding & Guardrail Quality:** 0% Hallucination rate, 100% Adversarial catch rate

---

## 🔐 Phase 4: Security & Guardrail Hardening

- [ ] **4.1 Rate Limiting & Abuse Protection**
  - [ ] Add per-IP request throttling middleware on `/api/query` in [`backend/app.py`](file:///c:/Users/prath/OneDrive/Desktop/projects/july/backend/app.py).
  - [ ] Return `429 Too Many Requests` with retry-after headers on threshold breach.

- [ ] **4.2 PII Detection & Redaction**
  - [ ] Detect and redact personal info (names, phone numbers, emails) from voice transcripts before embedding or logging.
  - [ ] Integrate into [`backend/guardrails/query_guardrail.py`](file:///c:/Users/prath/OneDrive/Desktop/projects/july/backend/guardrails/query_guardrail.py) as a pre-validation step.

- [ ] **4.3 Adversarial Guardrail Test Suite**
  - [ ] Expand `evaluation/dataset.json` adversarial cases from 2 → 20+ covering: prompt injection, jailbreaks, off-topic, PII leakage, and script injection.
  - [ ] Add a dedicated `evaluation/adversarial_tests.json` with pass/fail assertions.
  - [ ] Integrate adversarial tests into [`evaluation/benchmark.py`](file:///c:/Users/prath/OneDrive/Desktop/projects/july/evaluation/benchmark.py) with a separate report section.

---

## 🌍 Phase 5: Multilingual & Voice Intelligence

- [ ] **5.1 Language Detection Auto-Routing**
  - [ ] Detect query language (Hindi, Tamil, Telugu, etc.) from STT transcript.
  - [ ] Route to language-specific embedding model or prompt template instead of defaulting to English.

- [ ] **5.2 Sarvam TTS (Text-to-Speech) Response**
  - [ ] Synthesize the final answer back as spoken audio in the user's query language.
  - [ ] Stream TTS audio chunks from backend to frontend audio player in [`frontend/src/App.tsx`](file:///c:/Users/prath/OneDrive/Desktop/projects/july/frontend/src/App.tsx).

- [ ] **5.3 Disfluency & Filler Word Stripping**
  - [ ] Strip spoken filler words ("umm", "uh", "like", "you know", "so") from STT transcripts before normalization.
  - [ ] Add patterns to [`backend/guardrails/query_guardrail.py`](file:///c:/Users/prath/OneDrive/Desktop/projects/july/backend/guardrails/query_guardrail.py) `normalize_query()`.

---

## 📦 Phase 6: Production Readiness

- [ ] **6.1 Persistent Index Snapshots (No Re-ingestion on Restart)**
  - [ ] Auto-save FAISS and BM25 indexes to `data/indexes/` on shutdown.
  - [ ] Load indexes from disk on startup before falling back to full re-ingestion.

- [ ] **6.2 Async Parallel Ingestion**
  - [ ] Parallelize VAST chunking across documents using `asyncio.gather` or `ProcessPoolExecutor` in [`backend/ingestion/pipeline.py`](file:///c:/Users/prath/OneDrive/Desktop/projects/july/backend/ingestion/pipeline.py).

- [ ] **6.3 Health Check Endpoint**
  - [ ] Add `/api/health` endpoint in [`backend/app.py`](file:///c:/Users/prath/OneDrive/Desktop/projects/july/backend/app.py) reporting:
    - FAISS index status (loaded / number of vectors)
    - Embedding model readiness
    - LLM provider connectivity (`gemini` / `grounded_local`)
  - [ ] Wire health probe into `Dockerfile.backend` and `docker-compose.yml`.

- [ ] **6.4 Analytics Persistence**
  - [ ] Replace in-memory `analytics_store` with a SQLite or Redis write-through store so latency data survives server restarts.

---

## 🔬 Phase 7: Dataset & Knowledge Expansion

- [ ] **7.1 Real MSMARCO-XI HuggingFace Integration**
  - [ ] Wire up `load_msmarco_xi_dataset("ai4bharat/MSMARCO-XI")` in [`backend/ingestion/dataset.py`](file:///c:/Users/prath/OneDrive/Desktop/projects/july/backend/ingestion/dataset.py) for real corpus retrieval testing.
  - [ ] Verify `doc_id`, `text`, and `language` field mappings against the actual HuggingFace schema.

- [ ] **7.2 Hot-Reload Dynamic Knowledge Update**
  - [ ] Add `POST /api/ingest` endpoint to accept new documents and update the FAISS + BM25 indexes at runtime without restarting the server.

- [ ] **7.3 Evaluation Dataset Expansion**
  - [ ] Grow `evaluation/dataset.json` from 12 → 50+ queries covering:
    - Multi-hop reasoning queries
    - Paraphrase variants of existing factual queries
    - Negation queries ("What does FAISS *not* support?")
    - Ambiguous single-word queries ("India?", "Goa?")
    - Cross-language queries (Hindi/Tamil questions about English docs)
