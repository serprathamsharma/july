import asyncio
from backend.harness.orchestrator import RAGOrchestrator
from backend.retrieval.faiss_index import FAISSVectorIndex
from backend.retrieval.bm25_index import BM25LexicalIndex
from backend.config.settings import settings
import os

async def main():
    faiss_idx = FAISSVectorIndex()
    bm25_idx = BM25LexicalIndex()
    faiss_path = os.path.join(settings.INDEX_DIR, "faiss.index")
    meta_path = os.path.join(settings.INDEX_DIR, "chunks_metadata.pkl")
    bm25_path = os.path.join(settings.INDEX_DIR, "bm25.pkl")
    faiss_idx.load(faiss_path, meta_path)
    bm25_idx.load(bm25_path)

    orch = RAGOrchestrator(faiss_index=faiss_idx, bm25_index=bm25_idx)

    print("--- 1. Query 1 (Cache Miss) ---")
    r1 = await orch.execute_query("What is the MSMARCO-XI dataset designed for?")
    print(f"R1 Total Latency: {r1.metrics.total_ms}ms")
    print(f"R1 Cache Hit: {r1.metrics.cache_hit}")
    print(f"R1 Supported: {r1.supported}")
    print(f"R1 Answer: {r1.answer}")

    print("\n--- 2. Query 2 (Exact Cache Hit) ---")
    r2 = await orch.execute_query("What is the MSMARCO-XI dataset designed for?")
    print(f"R2 Total Latency: {r2.metrics.total_ms}ms")
    print(f"R2 Cache Hit: {r2.metrics.cache_hit} (Type: {r2.metrics.cache_type})")
    print(f"R2 Answer: {r2.answer}")

    print("\n--- 3. Query 3 (Streaming SSE) ---")
    token_count = 0
    full_text = ""
    async for sse_chunk in orch.execute_query_stream("Explain Reciprocal Rank Fusion."):
        if '"type": "token"' in sse_chunk:
            token_count += 1
        if '"type": "done"' in sse_chunk:
            print("Received final 'done' event with metrics!")
    print(f"Streaming completed successfully with {token_count} token events.")

if __name__ == "__main__":
    asyncio.run(main())
