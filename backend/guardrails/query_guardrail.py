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

    def normalize_query(self, query: str) -> str:
        """
        Collapses spelled-out letters (e.g. 'm s m a r c o' -> 'MSMARCO'),
        strips conversational preamble/fillers, and normalizes domain acronyms.
        """
        if not query:
            return ""
        
        normalized = query.strip()

        # 1. Strip conversational preamble / filler phrases
        preambles = [
            r'^(can\s+you\s+(please\s+)?(tell\s+me|explain|give\s+me|clarify)\s+(about\s+)?)\b',
            r'^(could\s+you\s+(please\s+)?(tell\s+me|explain|clarify)\s+(about\s+)?)\b',
            r'^(i\s+(would\s+like|want)\s+to\s+(know|learn|understand)\s+(about\s+)?)\b',
            r'^(do\s+you\s+know\s+(about\s+)?)\b',
            r'^(please\s+(tell\s+me|explain|give\s+me)\s+(about\s+)?)\b',
            r'^(what\s+do\s+you\s+know\s+about\s+)\b',
            r'^(tell\s+me\s+about\s+)\b',
        ]
        for p in preambles:
            normalized = re.sub(p, '', normalized, flags=re.IGNORECASE).strip()

        # 2. Collapse spelled-out sequences: 'm s m a r c o' -> 'msmarco', 'f a i s s' -> 'faiss'
        normalized = re.sub(r'\b([a-zA-Z]\s+){2,}[a-zA-Z]\b', lambda m: re.sub(r'\s+', '', m.group(0)), normalized)
        # 3. Handle dot-separated letters: 'm.s.m.a.r.c.o' -> 'msmarco'
        normalized = re.sub(r'\b([a-zA-Z]\.\s*){2,}[a-zA-Z]\.?', lambda m: re.sub(r'[\.\s]+', '', m.group(0)), normalized)
        # 4. Domain-specific acronym and speech replacements
        normalized = re.sub(r'\bm\s*s\s*marco\b', 'MSMARCO', normalized, flags=re.IGNORECASE)
        normalized = re.sub(r'\bmsmarco\s*(11|eleven|xi)\b', 'MSMARCO-XI', normalized, flags=re.IGNORECASE)
        normalized = re.sub(r'\bmsmarco\s*(1|one|i)\b', 'MSMARCO-XI', normalized, flags=re.IGNORECASE)
        normalized = re.sub(r'\bf\s*a\s*i\s*s\s*s\b', 'FAISS', normalized, flags=re.IGNORECASE)
        normalized = re.sub(r'\bb\s*m\s*25\b', 'BM25', normalized, flags=re.IGNORECASE)
        normalized = re.sub(r'\bb\s*m\s*twenty\s*five\b', 'BM25', normalized, flags=re.IGNORECASE)
        normalized = re.sub(r'\br\s*r\s*f\b', 'RRF', normalized, flags=re.IGNORECASE)
        normalized = re.sub(r'\br\s*a\s*g\b', 'RAG', normalized, flags=re.IGNORECASE)
        normalized = re.sub(r'\bv\s*a\s*s\s*t\b', 'VAST', normalized, flags=re.IGNORECASE)
        normalized = re.sub(r'\bs\s*a\s*r\s*v\s*a\s*m\b', 'Sarvam', normalized, flags=re.IGNORECASE)
        normalized = re.sub(r'\bdatabse\b', 'database', normalized, flags=re.IGNORECASE)
        normalized = re.sub(r'\bdatbase\b', 'database', normalized, flags=re.IGNORECASE)
        normalized = re.sub(r'\bdata\s+base\b', 'database', normalized, flags=re.IGNORECASE)
        normalized = re.sub(r'\bpli\s+scheme\b', 'PLI manufacturing incentives', normalized, flags=re.IGNORECASE)
        
        return normalized

    def validate_query(self, query: str) -> Dict[str, Any]:
        cleaned = self.normalize_query(query)

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
