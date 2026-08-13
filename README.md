# HH Goa 2026 — Voice-Enabled RAG System

A production-quality, high-speed, voice-enabled Retrieval-Augmented Generation (RAG) system built for the **HH Goa 2026** challenge. The system combines multi-strategy adaptive chunking (**VAST**), hybrid FAISS vector + BM25 lexical retrieval using Reciprocal Rank Fusion (**RRF**), multi-layer guardrails, Sarvam Speech-to-Text, and a dark glassmorphic frontend UI with sub-50ms query processing and real-time latency analytics.

---

## Technical Architecture Overview

```mermaid
flowchart TD
    User([User Voice / Text]) --> UI[React + Vite Frontend]
    UI -->|Audio Blob / Web Audio| STT[Sarvam STT Provider]
    STT -->|Transcript| Harness[RAG Harness / Orchestrator]
    UI -->|Text Query| Harness
    
    subgraph Harness [Orchestration Lifecycle & Latency Instrumentation]
        VAL[1. Query Guardrails & Validation] --> ROUTE[2. Adaptive Retrieval Router]
        
        subgraph Hybrid_Retrieval [Parallel Retrieval Engine]
            ROUTE -->|Dense Path| DENSE[FAISS Vector Search]
            ROUTE -->|Lexical Path| BM25[BM25 Search]
        end
        
        DENSE --> RRF[3. Reciprocal Rank Fusion - RRF]
        BM25 --> RRF
        
        RRF --> CVAL[4. Context Validation & Retrieval Guardrail]
        CVAL -->|Valid Evidence| LLM[5. Grounded LLM Generator]
        CVAL -->|Low Confidence| ABSTAIN[Abstain Refusal Response]
        
        LLM --> GVAL[6. Grounding Guardrail]
        GVAL -->|Supported| RESP[7. Structured Response JSON]
        GVAL -->|Hallucination Detected| ABSTAIN
    end
    
    RESP --> UI
    ABSTAIN --> UI
```

---

## Key System Features

- **Sarvam AI STT & Fallbacks**: High-accuracy Speech-to-Text with automatic Web Speech / local transcription fallback.
- **VAST Chunking**: Variable Adaptive Semantic Text Chunking generating Sentence, Paragraph, and Semantic sliding window views with document provenance.
- **Parallel Hybrid Search & RRF**: Parallel FAISS dense vector search and BM25 lexical search merged via Reciprocal Rank Fusion ($\text{RRF Score}(d) = \sum \frac{w_m}{k + \text{rank}_m(d)}$).
- **Multi-Layer Guardrails**: Query security, context sufficiency thresholding (honest abstention), and LLM answer grounding verifiers.
- **Instrumentation & Glassmorphic UI**: Dynamic P50/P70/P100 latency percentiles with interactive audio visualizer and source citation inspector.

---

## Directory Layout

```text
july/
├── backend/            # FastAPI app, VAST chunking, FAISS + BM25 RRF engine, guardrails
├── evaluation/         # Benchmark harness & test query dataset (Recall@k, MRR, latency)
├── frontend/           # React + Vite + Tailwind dark glassmorphic UI dashboard
├── scripts/            # Ingestion pipeline & benchmark runner scripts
├── data/               # Local FAISS vector & BM25 binary indexes
├── docker-compose.yml  # Container orchestration setup
├── requirements.txt    # Python dependencies
└── README.md
```

---

## Quick Start

### 1. Environment Setup
```bash
cp .env.example .env
# Set optional SARVAM_API_KEY & GEMINI_API_KEY (operates in zero-API fallback mode if omitted)
```

### 2. Install & Build Indexes
```bash
# Python Backend Setup
python -m venv venv
.\venv\Scripts\activate # On Linux/macOS: source venv/bin/activate
pip install -r requirements.txt

# Run Ingestion & Index Builder (FAISS + BM25)
python scripts/ingest_data.py
```

### 3. Run Development Servers
```bash
# Terminal 1: Backend API
uvicorn backend.app:app --host 0.0.0.0 --port 8000

# Terminal 2: Frontend UI
cd frontend && npm install && npm run dev
```
> Open `http://localhost:5173` for the UI dashboard or `http://localhost:8000/docs` for API specs.

---

## Docker Compose

```bash
docker-compose up --build
```
Access Frontend at `http://localhost:5173` and Backend at `http://localhost:8000`.

---

## API Endpoints

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `GET /api/health` | `GET` | System health check & index stats |
| `POST /api/text/query` | `POST` | Process text query through RAG pipeline |
| `POST /api/voice/query` | `POST` | Transcribe voice via Sarvam STT & execute RAG |
| `GET /api/analytics` | `GET` | Fetch live P50, P70, P100 latency percentiles |
| `GET /api/sources/{chunk_id}` | `GET` | Inspect chunk provenance & parent context |
| `POST /api/benchmark/run` | `POST` | Trigger evaluation benchmark suite |

---

## Benchmarks & License

Run evaluation suite:
```bash
python scripts/run_benchmark.py
```
Measures **Recall@1**, **Recall@5**, **MRR**, **Groundedness**, and **P50/P70/P100** latency metrics over `evaluation/dataset.json`.

Built for **HH Goa 2026**.
