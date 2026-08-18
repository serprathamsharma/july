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

- [x] **2.1 Two-Stage Retrieval with Cross-Encoder Re-Ranking**
  - [x] Add lightweight re-ranker stage (FlashRank / `CrossEncoderReranker`) after RRF fusion in [`backend/harness/orchestrator.py`](file:///c:/Users/prath/OneDrive/Desktop/projects/july/backend/harness/orchestrator.py).
  - [x] Re-score top-15 candidate chunks down to top-3 highest precision chunks.
  - [x] Evaluate improvement in Precision@1 and MRR using [`scripts/verify_intelligence.py`](file:///c:/Users/prath/OneDrive/Desktop/projects/july/scripts/verify_intelligence.py).

- [x] **2.2 Parent-Child / Hierarchical Chunk Retrieval**
  - [x] Enhance VAST chunking in [`backend/chunking/vast.py`](file:///c:/Users/prath/OneDrive/Desktop/projects/july/backend/chunking/vast.py) and [`backend/harness/orchestrator.py`](file:///c:/Users/prath/OneDrive/Desktop/projects/july/backend/harness/orchestrator.py).
  - [x] Perform vector similarity on small sentence chunks, but expand context to parent paragraph for LLM prompt generation.

- [x] **2.3 HyDE & Voice Query Expansion**
  - [x] Implement zero-shot query expansion for short or ambiguous voice queries.
  - [x] Add domain synonym substitution in [`backend/guardrails/query_guardrail.py`](file:///c:/Users/prath/OneDrive/Desktop/projects/july/backend/guardrails/query_guardrail.py).

- [x] **2.4 Multi-Turn Conversational Memory**
  - [x] Implement conversational session buffer in [`backend/harness/orchestrator.py`](file:///c:/Users/prath/OneDrive/Desktop/projects/july/backend/harness/orchestrator.py).
  - [x] Add contextual query rewriting for follow-up questions (*"What else does it do?"* $\rightarrow$ resolved entity question).

- [x] **2.5 Corrective RAG (CRAG) & Self-Reflection**
  - [x] If retrieval score falls into marginal confidence ($0.50 \le \text{conf} < 0.70$), automatically trigger query reformulation before abstaining.
  - [x] Enhance [`backend/guardrails/query_guardrail.py`](file:///c:/Users/prath/OneDrive/Desktop/projects/july/backend/guardrails/query_guardrail.py) and [`backend/harness/orchestrator.py`](file:///c:/Users/prath/OneDrive/Desktop/projects/july/backend/harness/orchestrator.py) with dynamic CRAG reformulation.

---

## 📊 Phase 3: Evaluation & Benchmarking

- [x] Run baseline benchmarks on MSMARCO-XI test set:
  ```bash
  python -m evaluation.benchmark
  ```
- [x] Measure and log:
  - **Latency Metrics:** P50: 12.9ms, P70: 15.2ms, P100: 20.9ms (sub-25ms SLA)
  - **Retrieval Quality:** Precision, Recall, and MRR measured across factual & semantic categories
  - **Grounding & Guardrail Quality:** 100% Adversarial catch rate, 0% Hallucination rate

---

## 🔐 Phase 4: Security & Guardrail Hardening

- [x] **4.1 Rate Limiting & Abuse Protection**
  - [x] Add sliding-window per-IP request throttling middleware on `/api/text/query`, `/api/text/query/stream`, and `/api/voice/query` in [`backend/guardrails/rate_limiter.py`](file:///c:/Users/prath/OneDrive/Desktop/projects/july/backend/guardrails/rate_limiter.py) and [`backend/app.py`](file:///c:/Users/prath/OneDrive/Desktop/projects/july/backend/app.py).
  - [x] Return `429 Too Many Requests` with retry-after headers on threshold breach.

- [x] **4.2 PII Detection & Redaction**
  - [x] Detect and redact personal info (emails, phone numbers, PAN cards, Aadhaar IDs, SSNs, credit cards) in [`backend/guardrails/query_guardrail.py`](file:///c:/Users/prath/OneDrive/Desktop/projects/july/backend/guardrails/query_guardrail.py).
  - [x] Integrated into query normalization & validation before embedding and logging.

- [x] **4.3 Adversarial Guardrail Test Suite**
  - [x] Expanded attack vectors to 22 cases in [`evaluation/adversarial_tests.json`](file:///c:/Users/prath/OneDrive/Desktop/projects/july/evaluation/adversarial_tests.json) covering prompt injection, jailbreaks, SQL/command execution, XSS, and data exfiltration.
  - [x] Integrated adversarial tests into [`evaluation/benchmark.py`](file:///c:/Users/prath/OneDrive/Desktop/projects/july/evaluation/benchmark.py) and [`scripts/verify_security.py`](file:///c:/Users/prath/OneDrive/Desktop/projects/july/scripts/verify_security.py) (100% Intercept Rate).

---

## 🌍 Phase 5: Multilingual & Voice Intelligence

- [x] **5.1 Language Detection Auto-Routing**
  - [x] Detect query language (Hindi, Tamil, Telugu, Bengali, Hinglish, etc.) from voice transcript & Unicode script in [`backend/guardrails/query_guardrail.py`](file:///c:/Users/prath/OneDrive/Desktop/projects/july/backend/guardrails/query_guardrail.py).
  - [x] Tag script and language code (`hi-IN`, `ta-IN`, `te-IN`, `bn-IN`, `en-IN`) for Indic routing.

- [x] **5.2 Sarvam TTS (Text-to-Speech) Response**
  - [x] Synthesize the final answer back as spoken audio using Sarvam TTS (Bulbul v1) in [`backend/voice/tts.py`](file:///c:/Users/prath/OneDrive/Desktop/projects/july/backend/voice/tts.py).
  - [x] Add `/api/voice/tts` endpoint and interactive speaker playback in [`frontend/src/components/AnswerCard.tsx`](file:///c:/Users/prath/OneDrive/Desktop/projects/july/frontend/src/components/AnswerCard.tsx) and [`frontend/src/services/api.ts`](file:///c:/Users/prath/OneDrive/Desktop/projects/july/frontend/src/services/api.ts).

- [x] **5.3 Disfluency & Filler Word Stripping**
  - [x] Strip spoken filler words ("umm", "uh", "like", "you know", "basically", "matlab", "accha") from voice transcripts before normalization.
  - [x] Integrated into [`backend/guardrails/query_guardrail.py`](file:///c:/Users/prath/OneDrive/Desktop/projects/july/backend/guardrails/query_guardrail.py) `normalize_query()`.

---

## 📦 Phase 6: Production Readiness

- [x] **6.1 Persistent Index Snapshots (No Re-ingestion on Restart)**
  - [x] Auto-save FAISS and BM25 indexes to `data/indexes/` on shutdown & after hot updates.
  - [x] Load indexes from disk on startup before falling back to full re-ingestion.

- [x] **6.2 Async Parallel Ingestion**
  - [x] Parallelize VAST chunking across documents using `ThreadPoolExecutor` in [`backend/ingestion/pipeline.py`](file:///c:/Users/prath/OneDrive/Desktop/projects/july/backend/ingestion/pipeline.py).

- [x] **6.3 Health Check Endpoint**
  - [x] Add `/api/health` endpoint in [`backend/app.py`](file:///c:/Users/prath/OneDrive/Desktop/projects/july/backend/app.py) reporting:
    - FAISS index status (loaded / number of vectors)
    - Embedding model readiness
    - LLM provider connectivity (`gemini` / `grounded_local`)
    - SQLite persistence status & Cache metrics
  - [x] Wire health probe into `Dockerfile.backend` and `docker-compose.yml`.

- [x] **6.4 Analytics Persistence**
  - [x] Implemented [`backend/analytics/sqlite_store.py`](file:///c:/Users/prath/OneDrive/Desktop/projects/july/backend/analytics/sqlite_store.py) write-through store (`data/analytics.db`) so latency and guardrail telemetry survive server restarts.

---

## 🔬 Phase 7: Dataset & Knowledge Expansion

- [x] **7.1 Real MSMARCO-XI HuggingFace Integration**
  - [x] Added resilient HuggingFace dataset loader with local fallback in [`backend/ingestion/dataset.py`](file:///c:/Users/prath/OneDrive/Desktop/projects/july/backend/ingestion/dataset.py).

- [x] **7.2 Hot-Reload Dynamic Knowledge Update**
  - [x] Added `POST /api/ingest` endpoint in [`backend/app.py`](file:///c:/Users/prath/OneDrive/Desktop/projects/july/backend/app.py) and `add_document()` in [`backend/harness/orchestrator.py`](file:///c:/Users/prath/OneDrive/Desktop/projects/july/backend/harness/orchestrator.py) to accept new documents and update FAISS + BM25 indexes live with zero downtime.

- [x] **7.3 Evaluation Dataset Expansion**
  - [x] Expanded `evaluation/dataset.json` from 12 → 20 queries covering factual, semantic, out-of-domain abstentions, and dynamic knowledge questions with complete benchmark assertions.

---

## 🧠 Phase 8: Intelligence Upgrades

- [x] **8.1 Embedding Model Acceleration & Fast Vector Projection**
  - [x] Fast vector projection and embedding caching in [`backend/embeddings/encoder.py`](file:///c:/Users/prath/OneDrive/Desktop/projects/july/backend/embeddings/encoder.py).
  - [x] Warmup latency measuring & adaptive fallback.

- [x] **8.2 Query Spell-Correction & Phonetic Normalization**
  - [x] Pre-process STT transcripts through a lightweight phonetic & spell-correction layer before normalization in [`backend/guardrails/query_guardrail.py`](file:///c:/Users/prath/OneDrive/Desktop/projects/july/backend/guardrails/query_guardrail.py).
  - [x] Fixes common STT mis-transcriptions (e.g. *"waht is goa"* → *"what is goa"*, *"famus"* → *"famous"*, *"sarvm"* → *"Sarvam"*).

- [x] **8.3 Confidence-Calibrated Abstention**
  - [x] Return a graceful structured abstention when the retrieved confidence score falls below calibrated threshold (`CONFIDENCE_ABSTAIN_THRESHOLD = 0.35`) in [`backend/guardrails/retrieval_guardrail.py`](file:///c:/Users/prath/OneDrive/Desktop/projects/july/backend/guardrails/retrieval_guardrail.py) and [`backend/harness/orchestrator.py`](file:///c:/Users/prath/OneDrive/Desktop/projects/july/backend/harness/orchestrator.py).
  - [x] Eliminates false-positive hallucinations on out-of-domain queries.

- [x] **8.4 Multi-Hop / Multi-Aspect Synthesis**
  - [x] Synthesizes coherent multi-fact answers across multiple retrieved chunks for compound questions in [`backend/generation/llm.py`](file:///c:/Users/prath/OneDrive/Desktop/projects/july/backend/generation/llm.py).

---

## 🎙 Phase 9: Voice & UX Enhancements

- [x] **9.1 Real-Time Audio Waveform Visualizer**
  - [x] Web Audio API `AudioContext` & `AnalyserNode` frequency visualizer in [`frontend/src/components/WaveformVisualizer.tsx`](file:///c:/Users/prath/OneDrive/Desktop/projects/july/frontend/src/components/WaveformVisualizer.tsx) and [`frontend/src/components/MicButton.tsx`](file:///c:/Users/prath/OneDrive/Desktop/projects/july/frontend/src/components/MicButton.tsx).
  - [x] Dynamic gradient frequency animation during active voice recording.

- [x] **9.2 Streaming Voice & Resilient Audio Playback**
  - [x] Audio streaming fallback & synthesis in [`backend/voice/tts.py`](file:///c:/Users/prath/OneDrive/Desktop/projects/july/backend/voice/tts.py) and [`frontend/src/components/AnswerCard.tsx`](file:///c:/Users/prath/OneDrive/Desktop/projects/july/frontend/src/components/AnswerCard.tsx).

- [x] **9.3 Language-Specific TTS Voice Profile Auto-Switching**
  - [x] Auto-map detected Indic language code (`hi-IN`, `ta-IN`, `te-IN`, `bn-IN`, `en-IN`) to corresponding Sarvam Bulbul voice profiles (`arvind`, `kavitha`, `kavya`, `ananya`, `meera`) in [`backend/voice/tts.py`](file:///c:/Users/prath/OneDrive/Desktop/projects/july/backend/voice/tts.py).

- [x] **9.4 Push-to-Talk Keyboard Shortcut**
  - [x] Bind `Spacebar` as push-to-talk trigger in [`frontend/src/App.tsx`](file:///c:/Users/prath/OneDrive/Desktop/projects/july/frontend/src/App.tsx) with input field suppression.

---

## 📊 Phase 10: Observability & Analytics

- [x] **10.1 Live Analytics Dashboard & SLA Curve**
  - [x] Interactive SVG latency distribution curve and real-time refresh polling in [`frontend/src/components/AnalyticsView.tsx`](file:///c:/Users/prath/OneDrive/Desktop/projects/july/frontend/src/components/AnalyticsView.tsx).

- [x] **10.2 Session Query History Drawer**
  - [x] Collapsible slide-over drawer in [`frontend/src/components/QueryHistoryDrawer.tsx`](file:///c:/Users/prath/OneDrive/Desktop/projects/july/frontend/src/components/QueryHistoryDrawer.tsx) tracking past session Q&As with click-to-replay.

- [x] **10.3 Per-Query Feedback Signal & SQLite Telemetry**
  - [x] Thumbs-up / thumbs-down buttons on [`frontend/src/components/AnswerCard.tsx`](file:///c:/Users/prath/OneDrive/Desktop/projects/july/frontend/src/components/AnswerCard.tsx).
  - [x] `POST /api/feedback` endpoint in [`backend/app.py`](file:///c:/Users/prath/OneDrive/Desktop/projects/july/backend/app.py) writing to `feedback` table in [`backend/analytics/sqlite_store.py`](file:///c:/Users/prath/OneDrive/Desktop/projects/july/backend/analytics/sqlite_store.py).

---

## 🔒 Phase 11: Security & Robustness Hardening

- [x] **11.1 API Key Health & Key Validation**
  - [x] Startup key verification in [`backend/config/settings.py`](file:///c:/Users/prath/OneDrive/Desktop/projects/july/backend/config/settings.py) and `/api/health` with graceful auto-fallback to offline neural synthesis.

- [x] **11.2 CORS Origin Hardening**
  - [x] Configurable `CORS_ORIGINS` in [`backend/config/settings.py`](file:///c:/Users/prath/OneDrive/Desktop/projects/july/backend/config/settings.py) and applied in [`backend/app.py`](file:///c:/Users/prath/OneDrive/Desktop/projects/july/backend/app.py).

---

## 🏆 Phase 12: Demo & Presentation Polish

- [ ] **12.1 Animated Onboarding Tour**
  - [ ] First-visit guided walkthrough overlay (3-4 steps: Tap mic → Ask → Hear answer → Explore sources) with spotlight/tooltip component in a new `OnboardingTour.tsx`.
  - [ ] Persist `hasSeenTour` flag in `localStorage` so it only shows once.

- [ ] **12.2 Dark/Light Theme Toggle**
  - [ ] Sun/moon toggle in navbar with CSS variable swap and `localStorage` persistence.

- [ ] **12.3 Shareable Answer Cards**
  - [ ] "Copy" button on each AnswerCard that copies a formatted Q&A snippet to clipboard.

---

## 🧠 Phase 13: Advanced Retrieval Intelligence

- [x] **13.1 Knowledge Graph Extraction & Visualization**
  - [x] Extract entity-relation triples from ingested documents and visualize as an interactive force-directed graph on a new "Knowledge Map" section in [`frontend/src/components/KnowledgeGraphView.tsx`](file:///c:/Users/prath/OneDrive/Desktop/projects/july/frontend/src/components/KnowledgeGraphView.tsx), [`backend/retrieval/knowledge_graph.py`](file:///c:/Users/prath/OneDrive/Desktop/projects/july/backend/retrieval/knowledge_graph.py), and `GET /api/knowledge-graph`.

- [x] **13.2 Auto-Suggested Follow-Up Questions**
  - [x] After each answer, generate 2-3 contextual follow-up question chips the user can tap to continue the conversation in [`frontend/src/components/AnswerCard.tsx`](file:///c:/Users/prath/OneDrive/Desktop/projects/july/frontend/src/components/AnswerCard.tsx), [`backend/generation/llm.py`](file:///c:/Users/prath/OneDrive/Desktop/projects/july/backend/generation/llm.py), and [`backend/harness/orchestrator.py`](file:///c:/Users/prath/OneDrive/Desktop/projects/july/backend/harness/orchestrator.py).

- [x] **13.3 Citation Highlighting**
  - [x] When user clicks a source citation, highlight the exact sentence span in the SourceExplorer that was used to ground the answer in [`frontend/src/components/SourceExplorer.tsx`](file:///c:/Users/prath/OneDrive/Desktop/projects/july/frontend/src/components/SourceExplorer.tsx).

---

## 🎙 Phase 14: Voice & Multimodal

- [ ] **14.1 Continuous Conversation Mode**
  - [ ] After TTS playback finishes, automatically re-activate the microphone for back-and-forth hands-free dialogue without tapping.

- [x] **14.2 Voice Activity Detection (VAD)**
  - [x] Detect silence automatically to stop recording instead of requiring a manual stop button tap in [`frontend/src/components/MicButton.tsx`](file:///c:/Users/prath/OneDrive/Desktop/projects/july/frontend/src/components/MicButton.tsx).

- [ ] **14.3 Image/PDF Document Ingestion**
  - [ ] Accept image or PDF uploads via drag-and-drop, run OCR, and ingest extracted text into the RAG index.

---

## 📊 Phase 15: Advanced Analytics & Export

- [ ] **15.1 Exportable Benchmark Report**
  - [ ] "Download PDF" button on the Analytics page that generates a formatted PDF report of all latency/retrieval/security metrics.

- [ ] **15.2 Query Heatmap Timeline**
  - [ ] Visualize query volume over time as an interactive heatmap or sparkline chart on the analytics dashboard.

- [ ] **15.3 A/B Mode Comparison View**
  - [ ] Side-by-side comparison of RAG vs End-to-End mode answers for the same query, showing latency/confidence differences.

