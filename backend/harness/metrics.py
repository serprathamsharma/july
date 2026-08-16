import time
import uuid
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

class LatencyMetrics(BaseModel):
    request_id: str
    stt_ms: float = 0.0
    query_processing_ms: float = 0.0
    embedding_ms: float = 0.0
    dense_retrieval_ms: float = 0.0
    bm25_ms: float = 0.0
    fusion_ms: float = 0.0
    generation_ms: float = 0.0
    guardrail_ms: float = 0.0
    ttft_ms: float = 0.0
    cache_hit: bool = False
    cache_type: Optional[str] = None  # None | "exact" | "semantic"
    total_ms: float = 0.0
    mode: str = "RAG"  # RAG or End-to-End

class RequestTimer:
    def __init__(self, mode: str = "RAG"):
        self.request_id = f"req_{uuid.uuid4().hex[:8]}"
        self.metrics = LatencyMetrics(request_id=self.request_id, mode=mode)
        self.start_time = time.perf_counter()
        self._step_start = self.start_time

    def start_step(self):
        self._step_start = time.perf_counter()

    def stop_step(self, step_name: str) -> float:
        elapsed = (time.perf_counter() - self._step_start) * 1000
        if hasattr(self.metrics, step_name):
            setattr(self.metrics, step_name, round(elapsed, 2))
        return elapsed

    def finalize(self) -> LatencyMetrics:
        self.metrics.total_ms = round((time.perf_counter() - self.start_time) * 1000, 2)
        return self.metrics
