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

        # Conversational & Utility Direct Intent Handling
        lower_q = cleaned.lower()
        if re.search(r'\b(what|whats|what\'s)?\s*(is)?\s*(the)?\s*(current)?\s*(date|day|today)\b', lower_q):
            import datetime
            now_str = datetime.datetime.now().strftime("%A, %B %d, %Y")
            return {
                "valid": False,
                "supported": True,
                "confidence": 1.0,
                "reason": "direct_utility_query",
                "message": f"Today's date is {now_str}."
            }

        if re.search(r'\b(what|whats|what\'s)?\s*(is)?\s*(the)?\s*(current)?\s*time\b', lower_q):
            import datetime
            time_str = datetime.datetime.now().strftime("%I:%M %p")
            return {
                "valid": False,
                "supported": True,
                "confidence": 1.0,
                "reason": "direct_utility_query",
                "message": f"The current time is {time_str}."
            }

        if re.search(r'^(hi|hello|hey|who are you|what is july)\b', lower_q):
            return {
                "valid": False,
                "supported": True,
                "confidence": 1.0,
                "reason": "greeting_query",
                "message": "Hello! I am July, a sub-200ms voice-enabled grounded RAG platform. How can I help you today?"
            }

        return {"valid": True, "reason": None, "message": "OK"}
