import re
from typing import Dict, Any

class QueryGuardrail:
    """
    Validates input queries before triggering retrieval pipeline.
    Catches off-topic, empty, or malicious/unsafe requests.
    """
    UNSAFE_PATTERNS = [
        r'\b(ignore previous instructions|drop table|system prompt|override safety|jailbreak)\b'
    ]

    def validate_query(self, query: str) -> Dict[str, Any]:
        cleaned = query.strip()

        if not cleaned:
            return {
                "valid": False,
                "reason": "empty_query",
                "message": "Query cannot be empty. Please ask a valid question."
            }

        if len(cleaned) < 2:
            return {
                "valid": False,
                "reason": "query_too_short",
                "message": "Query is too short. Please provide a clear question."
            }

        # Check unsafe patterns
        for pattern in self.UNSAFE_PATTERNS:
            if re.search(pattern, cleaned, re.IGNORECASE):
                return {
                    "valid": False,
                    "reason": "unsafe_query",
                    "message": "This query violated security policies and cannot be processed."
                }

        return {"valid": True, "reason": None, "message": "OK"}
