import os
import time
from typing import Dict, Any, List
from backend.config.settings import settings
from backend.ingestion.dataset import load_msmarco_xi_dataset
from backend.chunking.vast import VASTChunker, ChunkMetadata
from backend.embeddings.encoder import EmbeddingEncoder
from backend.retrieval.faiss_index import FAISSVectorIndex
from backend.retrieval.bm25_index import BM25LexicalIndex
from backend.analytics.store import analytics_store

def run_ingestion_pipeline(
    dataset_name: str = None,
    max_docs: int = None,
    index_dir: str = None
) -> Dict[str, Any]:
    dataset_name = dataset_name or settings.DATASET_NAME
    max_docs = max_docs or settings.MAX_INGEST_DOCUMENTS
    index_dir = index_dir or settings.INDEX_DIR

    os.makedirs(index_dir, exist_ok=True)
    start_total = time.perf_counter()

    print("==================================================")
    print("      HH GOA 2026 — VAST INGESTION PIPELINE       ")
    print("==================================================")
    print(f"1. Loading dataset: {dataset_name} (limit={max_docs})...")
    documents = load_msmarco_xi_dataset(dataset_name, max_docs)

    print("\n2. Executing VAST Multi-Strategy Chunking...")
    chunker = VASTChunker(target_semantic_words=120, overlap_words=25)
    all_chunks: List[ChunkMetadata] = []
    chunk_counts = {"sentence": 0, "paragraph": 0, "semantic": 0}

    for doc in documents:
        res = chunker.process_document(doc["document_id"], doc["text"], doc.get("language", "en"))
        all_chunks.extend(res["all"])
        chunk_counts["sentence"] += len(res["sentence"])
        chunk_counts["paragraph"] += len(res["paragraph"])
        chunk_counts["semantic"] += len(res["semantic"])

    print(f"   Created {len(all_chunks)} total chunks:")
    print(f"   - Sentence chunks:  {chunk_counts['sentence']}")
    print(f"   - Paragraph chunks: {chunk_counts['paragraph']}")
    print(f"   - Semantic chunks:  {chunk_counts['semantic']}")

    print("\n3. Generating Dense Embeddings...")
    encoder = EmbeddingEncoder()
    chunk_texts = [c.text for c in all_chunks]
    t_emb_start = time.perf_counter()
    embeddings = encoder.encode(chunk_texts)
    emb_duration = (time.perf_counter() - t_emb_start) * 1000
    print(f"   Encoded {len(embeddings)} vectors in {emb_duration:.2f}ms")

    print("\n4. Building FAISS Dense Index...")
    faiss_idx = FAISSVectorIndex(dimension=encoder.dimension)
    faiss_idx.add_chunks(all_chunks, embeddings)
    faiss_path = os.path.join(index_dir, "faiss.index")
    meta_path = os.path.join(index_dir, "chunks_metadata.pkl")
    faiss_idx.save(faiss_path, meta_path)

    print("\n5. Building BM25 Lexical Index...")
    bm25_idx = BM25LexicalIndex()
    bm25_idx.build_index(all_chunks)
    bm25_path = os.path.join(index_dir, "bm25.pkl")
    bm25_idx.save(bm25_path)

    # Update analytics store metadata
    analytics_store.indexed_documents = len(documents)
    analytics_store.indexed_chunks = len(all_chunks)

    total_duration = (time.perf_counter() - start_total)
    print("\n==================================================")
    print(f"   Ingestion Pipeline Completed in {total_duration:.2f}s!")
    print("==================================================")

    return {
        "status": "success",
        "documents_processed": len(documents),
        "chunks_created": len(all_chunks),
        "chunk_breakdown": chunk_counts,
        "index_directory": index_dir,
        "duration_seconds": round(total_duration, 2)
    }

if __name__ == "__main__":
    run_ingestion_pipeline()
