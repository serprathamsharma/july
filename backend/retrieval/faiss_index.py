import os
import pickle
import time
import faiss
import numpy as np
from typing import List, Dict, Any, Tuple
from backend.chunking.vast import ChunkMetadata

class FAISSVectorIndex:
    """
    FAISS Dense Vector Index wrapper with inner-product (cosine similarity)
    and chunk metadata mapping.
    """
    def __init__(self, dimension: int = 384):
        self.dimension = dimension
        self.index = faiss.IndexFlatIP(dimension)
        self.chunks: List[ChunkMetadata] = []

    def add_chunks(self, chunks: List[ChunkMetadata], embeddings: np.ndarray):
        if len(chunks) != len(embeddings):
            raise ValueError(f"Mismatch between chunks count ({len(chunks)}) and embeddings count ({len(embeddings)})")
        
        # Ensure L2 normalized vectors for Cosine Similarity via Inner Product
        faiss.normalize_L2(embeddings)
        self.index.add(embeddings)
        self.chunks.extend(chunks)

    def search(self, query_vector: np.ndarray, k: int = 10) -> List[Tuple[ChunkMetadata, float, int]]:
        """
        Search top k closest chunks.
        Returns List of (ChunkMetadata, score, rank)
        """
        start = time.perf_counter()
        if self.index.ntotal == 0:
            return []

        if query_vector.ndim == 1:
            query_vector = np.expand_dims(query_vector, axis=0)

        # Clone and normalize
        q_vec = query_vector.copy().astype(np.float32)
        faiss.normalize_L2(q_vec)

        scores, indices = self.index.search(q_vec, min(k, self.index.ntotal))
        
        results = []
        for rank, (score, idx) in enumerate(zip(scores[0], indices[0])):
            if idx >= 0 and idx < len(self.chunks):
                results.append((self.chunks[idx], float(score), rank + 1))

        return results

    def save(self, index_path: str, metadata_path: str):
        os.makedirs(os.path.dirname(index_path), exist_ok=True)
        faiss.write_index(self.index, index_path)
        with open(metadata_path, 'wb') as f:
            pickle.dump(self.chunks, f)
        print(f"[FAISSVectorIndex] Saved index with {self.index.ntotal} vectors to {index_path}")

    def load(self, index_path: str, metadata_path: str) -> bool:
        if not os.path.exists(index_path) or not os.path.exists(metadata_path):
            return False
        
        self.index = faiss.read_index(index_path)
        with open(metadata_path, 'rb') as f:
            self.chunks = pickle.load(f)
        print(f"[FAISSVectorIndex] Loaded index with {self.index.ntotal} vectors from {index_path}")
        return True
