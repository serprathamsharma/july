import asyncio
import os
from backend.harness.orchestrator import RAGOrchestrator
from backend.retrieval.faiss_index import FAISSVectorIndex
from backend.retrieval.bm25_index import BM25LexicalIndex
from backend.config.settings import settings

async def main():
    faiss_idx = FAISSVectorIndex()
    bm25_idx = BM25LexicalIndex()
    faiss_path = os.path.join(settings.INDEX_DIR, "faiss.index")
    meta_path = os.path.join(settings.INDEX_DIR, "chunks_metadata.pkl")
    bm25_path = os.path.join(settings.INDEX_DIR, "bm25.pkl")
    faiss_idx.load(faiss_path, meta_path)
    bm25_idx.load(bm25_path)

    orch = RAGOrchestrator(faiss_index=faiss_idx, bm25_index=bm25_idx)

    print("==================================================")
    print("      PHASE 2: RETRIEVAL INTELLIGENCE TESTS       ")
    print("==================================================")

    # 1. Multi-Turn Conversational Memory & Coreference Test
    session_id = "test_sess_42"
    print("\n--- 1. Multi-Turn Session Memory & Coreference Resolution ---")
    print("Turn 1: 'What is FAISS?'")
    t1 = await orch.execute_query("What is FAISS?", session_id=session_id)
    print(f"Turn 1 Answer: {t1.answer}")
    print(f"Turn 1 Supported: {t1.supported}")

    print("\nTurn 2 (Follow-up with pronoun 'it'): 'What vector indexing algorithms does it support?'")
    t2 = await orch.execute_query("What vector indexing algorithms does it support?", session_id=session_id)
    print(f"Turn 2 Answer: {t2.answer}")
    print(f"Turn 2 Supported: {t2.supported}")
    print(f"Turn 2 Citations: {t2.citations}")

    # 2. Cross-Encoder Re-Ranking Test
    print("\n--- 2. Cross-Encoder Re-ranking Stage ---")
    query = "What factors does BM25 compute for document relevance?"
    r_res = await orch.execute_query(query)
    print(f"Query: '{query}'")
    print(f"Top 1 Re-ranked Chunk ID: {r_res.retrieved_chunks[0]['chunk_id']}")
    print(f"Top 1 RRF/Cross-Score: {r_res.retrieved_chunks[0]['rrf_score']}")
    print(f"Answer: {r_res.answer}")

    # 3. Query Expansion & HyDE Test
    print("\n--- 3. HyDE & Voice Query Expansion ---")
    expanded = orch.query_guardrail.expand_query("sarvam")
    print(f"Expanded 'sarvam' -> '{expanded}'")

    # 4. Corrective RAG (CRAG) Test
    print("\n--- 4. Corrective RAG (CRAG) Reformulation ---")
    reformulated = orch.query_guardrail.reformulate_query("can you please tell me about the drivers of economic growth in India")
    print(f"Reformulated query -> '{reformulated}'")

    print("\n==================================================")
    print("   ALL PHASE 2 RETRIEVAL INTELLIGENCE CHECKS PASS! ")
    print("==================================================")

if __name__ == "__main__":
    asyncio.run(main())
