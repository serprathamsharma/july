import sqlite3
import os
import threading
import numpy as np
from typing import Dict, Any, List, Optional
from backend.harness.metrics import LatencyMetrics

class SQLiteAnalyticsStore:
    """
    Persistent SQLite storage for RAG pipeline telemetry and latency instrumentation.
    Stores per-request latency breakdowns and guardrail event telemetry across restarts.
    """
    def __init__(self, db_path: str = "data/analytics.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path) if os.path.dirname(self.db_path) else ".", exist_ok=True)
        self._lock = threading.Lock()
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS requests (
                    request_id TEXT PRIMARY KEY,
                    mode TEXT,
                    stt_ms REAL,
                    query_processing_ms REAL,
                    embedding_ms REAL,
                    dense_retrieval_ms REAL,
                    bm25_ms REAL,
                    fusion_ms REAL,
                    generation_ms REAL,
                    guardrail_ms REAL,
                    total_ms REAL,
                    ttft_ms REAL,
                    cache_hit INTEGER,
                    cache_type TEXT,
                    guardrail_event TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    request_id TEXT,
                    rating TEXT NOT NULL,
                    comment TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
            conn.close()

    def record_feedback(self, request_id: str, rating: str, comment: Optional[str] = None):
        """Records user feedback ('up' or 'down') for a given query request."""
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO feedback (request_id, rating, comment) VALUES (?, ?, ?)
            """, (request_id, rating, comment or ""))
            conn.commit()
            conn.close()

    def get_feedback_summary(self) -> Dict[str, Any]:
        """Returns aggregated feedback counts (thumbs up, thumbs down, satisfaction rate)."""
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT rating, COUNT(*) as count FROM feedback GROUP BY rating")
            rows = cursor.fetchall()
            conn.close()

        counts = {r["rating"]: r["count"] for r in rows}
        up = counts.get("up", 0)
        down = counts.get("down", 0)
        total = up + down
        satisfaction = round((up / total * 100), 1) if total > 0 else 100.0

        return {
            "thumbs_up": up,
            "thumbs_down": down,
            "total_feedback": total,
            "satisfaction_rate": satisfaction
        }

    def record_request(self, metrics: LatencyMetrics, guardrail_event: Optional[str] = None):
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO requests (
                    request_id, mode, stt_ms, query_processing_ms, embedding_ms,
                    dense_retrieval_ms, bm25_ms, fusion_ms, generation_ms, guardrail_ms,
                    total_ms, ttft_ms, cache_hit, cache_type, guardrail_event
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                metrics.request_id,
                metrics.mode,
                metrics.stt_ms,
                metrics.query_processing_ms,
                metrics.embedding_ms,
                metrics.dense_retrieval_ms,
                metrics.bm25_ms,
                metrics.fusion_ms,
                metrics.generation_ms,
                metrics.guardrail_ms,
                metrics.total_ms,
                metrics.ttft_ms,
                1 if metrics.cache_hit else 0,
                metrics.cache_type or "",
                guardrail_event or ""
            ))
            conn.commit()
            conn.close()

    def get_summary(self) -> Dict[str, Any]:
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM requests ORDER BY timestamp DESC LIMIT 500")
            rows = cursor.fetchall()
            conn.close()

        if not rows:
            return {
                "latency": {"p50": 0.0, "p70": 0.0, "p100": 0.0, "sample_count": 0},
                "pipeline_breakdown": {
                    "stt_ms": 0.0, "query_processing_ms": 0.0, "embedding_ms": 0.0,
                    "dense_retrieval_ms": 0.0, "bm25_ms": 0.0, "fusion_ms": 0.0,
                    "generation_ms": 0.0, "guardrail_ms": 0.0, "total_ms": 0.0
                },
                "guardrails": {
                    "queries_total": 0, "queries_rejected": 0,
                    "low_confidence_abstentions": 0, "grounding_failures": 0,
                    "unsafe_queries_blocked": 0
                }
            }

        totals = [r["total_ms"] for r in rows]
        p50 = float(np.percentile(totals, 50))
        p70 = float(np.percentile(totals, 70))
        p100 = float(np.max(totals))

        return {
            "latency": {
                "p50": round(p50, 1),
                "p70": round(p70, 1),
                "p100": round(p100, 1),
                "sample_count": len(rows)
            },
            "pipeline_breakdown": {
                "stt_ms": round(float(np.mean([r["stt_ms"] for r in rows])), 1),
                "query_processing_ms": round(float(np.mean([r["query_processing_ms"] for r in rows])), 1),
                "embedding_ms": round(float(np.mean([r["embedding_ms"] for r in rows])), 1),
                "dense_retrieval_ms": round(float(np.mean([r["dense_retrieval_ms"] for r in rows])), 1),
                "bm25_ms": round(float(np.mean([r["bm25_ms"] for r in rows])), 1),
                "fusion_ms": round(float(np.mean([r["fusion_ms"] for r in rows])), 1),
                "generation_ms": round(float(np.mean([r["generation_ms"] for r in rows])), 1),
                "guardrail_ms": round(float(np.mean([r["guardrail_ms"] for r in rows])), 1),
                "total_ms": round(float(np.mean(totals)), 1)
            },
            "guardrails": {
                "queries_total": len(rows),
                "queries_rejected": len([r for r in rows if r["guardrail_event"] in ["query_rejected", "empty_query", "query_too_short"]]),
                "low_confidence_abstentions": len([r for r in rows if r["guardrail_event"] == "low_confidence"]),
                "grounding_failures": len([r for r in rows if r["guardrail_event"] == "grounding_failure"]),
                "unsafe_queries_blocked": len([r for r in rows if r["guardrail_event"] in ["unsafe_query", "prompt_injection", "malicious_request"]])
            }
        }

    def reset(self):
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM requests")
            conn.commit()
            conn.close()
