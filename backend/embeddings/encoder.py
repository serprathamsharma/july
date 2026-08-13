import time
import numpy as np
from typing import List, Union
from backend.config.settings import settings

class EmbeddingEncoder:
    _instance = None
    _model = None
    _is_warmed_up = False
    _avg_encode_ms = 0.0

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(EmbeddingEncoder, cls).__new__(cls)
        return cls._instance

    def _ensure_model(self):
        """Lazy-load the model on first use."""
        if EmbeddingEncoder._model is None:
            from sentence_transformers import SentenceTransformer
            model_name = settings.EMBEDDING_MODEL
            print(f"[EmbeddingEncoder] Loading model: {model_name}")
            start = time.perf_counter()
            EmbeddingEncoder._model = SentenceTransformer(model_name)
            elapsed = (time.perf_counter() - start) * 1000
            self.dimension = EmbeddingEncoder._model.get_sentence_embedding_dimension()
            print(f"[EmbeddingEncoder] Model loaded in {elapsed:.0f}ms (dimension={self.dimension})")

    def warmup(self):
        """
        Pre-load the model and run a dummy encode to warm up the JIT/ONNX runtime.
        Call this once at startup so the first real query doesn't pay the cold-start cost.
        """
        self._ensure_model()
        # Run 3 warmup encodes to stabilize CPU caches and threading
        start = time.perf_counter()
        for _ in range(3):
            EmbeddingEncoder._model.encode(
                ["warmup sentence for embedding model"],
                convert_to_numpy=True,
                show_progress_bar=False,
                normalize_embeddings=True
            )
        avg_ms = ((time.perf_counter() - start) * 1000) / 3
        EmbeddingEncoder._avg_encode_ms = avg_ms
        EmbeddingEncoder._is_warmed_up = True
        self.dimension = EmbeddingEncoder._model.get_sentence_embedding_dimension()
        print(f"[EmbeddingEncoder] Warmup complete. Avg encode latency: {avg_ms:.1f}ms")

    @property
    def is_fast(self) -> bool:
        """Returns True if the model can encode queries in under 100ms (warmed up on this hardware)."""
        return EmbeddingEncoder._is_warmed_up and EmbeddingEncoder._avg_encode_ms < 100

    def encode(self, texts: Union[str, List[str]], normalize: bool = True) -> np.ndarray:
        self._ensure_model()
        if isinstance(texts, str):
            texts = [texts]
        embeddings = EmbeddingEncoder._model.encode(
            texts,
            convert_to_numpy=True,
            show_progress_bar=False,
            batch_size=32,
            normalize_embeddings=normalize
        )
        return embeddings.astype(np.float32)

    def benchmark_latency(self, num_trials: int = 10) -> float:
        sample_queries = ["What is voice retrieval-augmented generation?", "How does FAISS vector search work?", "Tell me about MSMARCO XI dataset."]
        start = time.perf_counter()
        for _ in range(num_trials):
            for q in sample_queries:
                self.encode(q)
        duration_ms = ((time.perf_counter() - start) * 1000) / (num_trials * len(sample_queries))
        print(f"[EmbeddingEncoder Benchmark] Average query embedding latency: {duration_ms:.2f}ms")
        return duration_ms
