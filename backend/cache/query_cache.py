import time
import threading
from typing import Dict, Any, Optional, Tuple, List
import numpy as np

class CachedEntry:
    def __init__(self, query: str, embedding: Optional[np.ndarray], response_data: Dict[str, Any], ttl_seconds: int = 3600):
        self.query = query
        self.embedding = embedding
        self.response_data = response_data
        self.created_at = time.time()
        self.expires_at = self.created_at + ttl_seconds
        self.hit_count = 0

    def is_expired(self) -> bool:
        return time.time() > self.expires_at


class QueryCache:
    """
    Two-Tier In-Memory Cache for Voice/Text RAG Pipeline:
    - Tier 1: Exact Hash Cache (O(1) normalized string lookup, < 1ms)
    - Tier 2: Semantic Vector Cache (Cosine similarity over cached query embeddings, < 5ms)
    """
    def __init__(
        self,
        max_entries: int = 1000,
        semantic_threshold: float = 0.96,
        ttl_seconds: int = 3600
    ):
        self.max_entries = max_entries
        self.semantic_threshold = semantic_threshold
        self.ttl_seconds = ttl_seconds
        self._exact_map: Dict[str, CachedEntry] = {}
        self._lock = threading.Lock()
        self.hits_exact = 0
        self.hits_semantic = 0
        self.misses = 0

    def _normalize_key(self, query: str) -> str:
        return " ".join(query.strip().lower().split())

    def get(
        self,
        query: str,
        query_embedding: Optional[np.ndarray] = None
    ) -> Optional[Tuple[Dict[str, Any], str]]:
        """
        Check for a cached response.
        Returns (response_data_dict, hit_type) where hit_type is 'exact' or 'semantic'.
        """
        key = self._normalize_key(query)
        if not key:
            return None

        with self._lock:
            # 1. Tier 1: Exact Match
            if key in self._exact_map:
                entry = self._exact_map[key]
                if entry.is_expired():
                    del self._exact_map[key]
                else:
                    entry.hit_count += 1
                    self.hits_exact += 1
                    return (entry.response_data.copy(), "exact")

            # 2. Tier 2: Semantic Vector Match
            if query_embedding is not None and len(self._exact_map) > 0:
                q_vec = np.array(query_embedding, dtype=np.float32)
                norm_q = np.linalg.norm(q_vec)
                if norm_q > 0:
                    q_vec_norm = q_vec / norm_q
                    best_score = -1.0
                    best_entry: Optional[CachedEntry] = None

                    for entry in list(self._exact_map.values()):
                        if entry.is_expired() or entry.embedding is None:
                            continue
                        e_vec = np.array(entry.embedding, dtype=np.float32)
                        norm_e = np.linalg.norm(e_vec)
                        if norm_e > 0:
                            sim = float(np.dot(q_vec_norm, e_vec / norm_e))
                            if sim > best_score:
                                best_score = sim
                                best_entry = entry

                    if best_entry and best_score >= self.semantic_threshold:
                        best_entry.hit_count += 1
                        self.hits_semantic += 1
                        return (best_entry.response_data.copy(), "semantic")

            self.misses += 1
            return None

    def put(
        self,
        query: str,
        response_data: Dict[str, Any],
        query_embedding: Optional[np.ndarray] = None
    ):
        """Stores a query and its grounded response in the cache."""
        key = self._normalize_key(query)
        if not key or not response_data:
            return

        with self._lock:
            # Evict expired entries or LRU if reaching capacity
            if len(self._exact_map) >= self.max_entries:
                expired_keys = [k for k, v in self._exact_map.items() if v.is_expired()]
                for k in expired_keys:
                    del self._exact_map[k]

                if len(self._exact_map) >= self.max_entries:
                    # Evict least frequently used entry
                    min_k = min(self._exact_map.keys(), key=lambda k: self._exact_map[k].hit_count)
                    del self._exact_map[min_k]

            self._exact_map[key] = CachedEntry(
                query=query,
                embedding=query_embedding,
                response_data=response_data,
                ttl_seconds=self.ttl_seconds
            )

    def clear(self):
        with self._lock:
            self._exact_map.clear()
            self.hits_exact = 0
            self.hits_semantic = 0
            self.misses = 0

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            total_lookups = self.hits_exact + self.hits_semantic + self.misses
            hit_rate = (self.hits_exact + self.hits_semantic) / total_lookups if total_lookups > 0 else 0.0
            return {
                "cached_entries": len(self._exact_map),
                "hits_exact": self.hits_exact,
                "hits_semantic": self.hits_semantic,
                "misses": self.misses,
                "hit_rate": round(hit_rate * 100, 1)
            }

# Global singleton query cache
query_cache = QueryCache()
