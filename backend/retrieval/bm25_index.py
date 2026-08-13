import os
import pickle
import re
import time
import numpy as np
from typing import List, Tuple
from rank_bm25 import BM25Okapi
from backend.chunking.vast import ChunkMetadata

class BM25LexicalIndex:
    """
    BM25 Lexical Index wrapper supporting tokenized text search across VAST chunks.
    """
    def __init__(self):
        self.bm25: BM25Okapi = None
        self.chunks: List[ChunkMetadata] = []

    def _tokenize(self, text: str) -> List[str]:
        # Lowercase and split words
        words = re.findall(r'\w+', text.lower())
        return words

    def build_index(self, chunks: List[ChunkMetadata]):
        self.chunks = chunks
        corpus = [self._tokenize(c.text) for c in chunks]
        self.bm25 = BM25Okapi(corpus)
        print(f"[BM25LexicalIndex] Built BM25 index over {len(chunks)} chunks.")

    def search(self, query: str, k: int = 10) -> List[Tuple[ChunkMetadata, float, int]]:
        """
        Search top k chunks using BM25.
        Returns List of (ChunkMetadata, bm25_score, rank)
        """
        if not self.bm25 or not self.chunks:
            return []

        tokenized_query = self._tokenize(query)
        if not tokenized_query:
            return []

        scores = self.bm25.get_scores(tokenized_query)
        top_n_indices = np.argsort(scores)[::-1][:k]

        results = []
        for rank, idx in enumerate(top_n_indices):
            score = float(scores[idx])
            if score > 0:
                results.append((self.chunks[idx], score, rank + 1))

        return results

    def save(self, filepath: str):
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'wb') as f:
            pickle.dump({'bm25': self.bm25, 'chunks': self.chunks}, f)
        print(f"[BM25LexicalIndex] Saved BM25 index to {filepath}")

    def load(self, filepath: str) -> bool:
        if not os.path.exists(filepath):
            return False
        with open(filepath, 'rb') as f:
            data = pickle.load(f)
            self.bm25 = data['bm25']
            self.chunks = data['chunks']
        print(f"[BM25LexicalIndex] Loaded BM25 index over {len(self.chunks)} chunks from {filepath}")
        return True
