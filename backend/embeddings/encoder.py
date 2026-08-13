import time
import numpy as np
from typing import List, Union
from sentence_transformers import SentenceTransformer
from backend.config.settings import settings

class EmbeddingEncoder:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(EmbeddingEncoder, cls).__new__(cls)
            cls._instance._init_model()
        return cls._instance

    def _init_model(self):
        model_name = settings.EMBEDDING_MODEL
        print(f"[EmbeddingEncoder] Loading model: {model_name}")
        start = time.perf_counter()
        self.model = SentenceTransformer(model_name)
        self.dimension = self.model.get_sentence_embedding_dimension()
        elapsed = (time.perf_counter() - start) * 1000
        print(f"[EmbeddingEncoder] Model loaded in {elapsed:.2f}ms (dimension={self.dimension})")

    def encode(self, texts: Union[str, List[str]], normalize: bool = True) -> np.ndarray:
        if isinstance(texts, str):
            texts = [texts]
        embeddings = self.model.encode(
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
