import asyncio
import os
from backend.harness.orchestrator import RAGOrchestrator
from backend.retrieval.faiss_index import FAISSVectorIndex
from backend.retrieval.bm25_index import BM25LexicalIndex
from backend.guardrails.rate_limiter import SlidingWindowRateLimiter
from backend.guardrails.query_guardrail import QueryGuardrail
from backend.config.settings import settings
from evaluation.benchmark import run_adversarial_benchmark

async def main():
    print("==================================================")
    print("       PHASE 4: SECURITY & GUARDRAILS TESTS       ")
    print("==================================================")

    # 1. PII Redaction Test
    print("\n--- 1. PII Detection & Redaction Tests ---")
    guardrail = QueryGuardrail()
    test_pii_texts = [
        "My email is alice.smith@example.com and phone is +91 9876543210",
        "Transfer from card 4111-2222-3333-4444 to PAN ABCDE1234F with Aadhaar 1234 5678 9012"
    ]
    for raw in test_pii_texts:
        redacted, types = guardrail.redact_pii(raw)
        print(f"Raw:      '{raw}'")
        print(f"Redacted: '{redacted}'")
        print(f"Detected: {types}\n")

    # 2. Sliding Window Rate Limiter Test
    print("--- 2. Sliding Window Rate Limiter Tests ---")
    limiter = SlidingWindowRateLimiter(requests_per_minute=5, window_seconds=60)
    test_ip = "192.168.1.100"
    print(f"Testing rate limit of 5 req/min on IP: {test_ip}")
    for i in range(1, 8):
        allowed, retry_after = limiter.is_allowed(test_ip)
        status = "ALLOWED" if allowed else f"THROTTLED (Retry-After: {retry_after}s)"
        print(f"Request #{i}: {status}")

    # 3. 22-Vector Adversarial Security Suite
    print("\n--- 3. 22-Vector Adversarial Security Benchmark ---")
    faiss_idx = FAISSVectorIndex()
    bm25_idx = BM25LexicalIndex()
    faiss_path = os.path.join(settings.INDEX_DIR, "faiss.index")
    meta_path = os.path.join(settings.INDEX_DIR, "chunks_metadata.pkl")
    bm25_path = os.path.join(settings.INDEX_DIR, "bm25.pkl")
    faiss_idx.load(faiss_path, meta_path)
    bm25_idx.load(bm25_path)

    orch = RAGOrchestrator(faiss_index=faiss_idx, bm25_index=bm25_idx)
    adv_summary = await run_adversarial_benchmark(orch)

    print(f"Final Security Intercept Rate: {adv_summary['intercept_rate'] * 100}%")
    if adv_summary["intercept_rate"] == 1.0:
        print("[SUCCESS] 100% SECURITY ATTACK CATCH RATE ACHIEVED!")

if __name__ == "__main__":
    asyncio.run(main())
