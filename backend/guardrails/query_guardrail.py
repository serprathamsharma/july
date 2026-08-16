import re
from typing import Dict, Any, Tuple, List
from backend.config.settings import settings

class QueryGuardrail:
    """
    Validates input queries before triggering retrieval pipeline.
    Catches prompt injection, jailbreaks, malicious code, PII leakage, and off-topic requests.
    """
    UNSAFE_PATTERNS = [
        # 1. Prompt Injections & System Prompt Exfiltration
        r'\b(ignore|disregard|forget)\s+(all\s+)?(previous|prior|above)?\s*(instructions?|prompts?|rules|guidelines)\b',
        r'\b(print|show|output|leak|reveal|repeat|dump)\s+(the\s+)?(system\s+prompt|developer\s+instructions?|initial\s+prompt|system\s+instruction)\b',
        r'\b(what\s+(is|are)\s+(your|the)\s+(system\s+prompt|initial\s+instructions?|system\s+message|developer\s+instructions?|initial\s+prompt))\b',
        r'\b(tell\s+me\s+your\s+(initial|developer|system)\s+(prompt|instructions?))\b',
        
        # 2. Jailbreaks, Persona Overrides & Mode Switches
        r'\b(jailbreak|override\s+safety|bypass\s+(all\s+)?guardrails?|dan\s+mode|unrestricted\s+mode)\b',
        r'\b(act\s+as\s+an?\s+[\w\s]{0,30}\b(unfiltered|unrestricted|evil|dark|hacked|dan)\s+(ai|assistant|model|mode))\b',
        r'\b(act\s+as\s+an?\s+(unfiltered|unrestricted|evil|dark|hacked|dan))\b',
        r'\b(forget\s+all\s+(your\s+)?(rules|safety\s+filters|ethics|constraints))\b',
        r'\b(disregard\s+(all\s+)?(safety\s+protocols|guidelines|rules))\b',

        # 3. SQL / Command / Code Execution Injections
        r'\b(drop\s+table|delete\s+from|union\s+select|insert\s+into|truncate\s+table)\b',
        r'\b(exec\s*\(|eval\s*\(|os\.system|subprocess\.Popen|__import__)\b',
        r'(\bselect\b.*\bfrom\b.*\bwhere\b)',

        # 4. Cross-Site Scripting (XSS) & Markup Injections
        r'(<script[\s>].*?</script>|<iframe|<svg[\s>]|javascript:|onerror\s*=|onload\s*=)',

        # 5. Malicious Exfiltration & Credential Dumping
        r'\b(dump\s+(database|passwords?|credentials?|all\s+users?))\b',
        r'\b(leak\s+(api\s+keys?|secret\s+keys?|database\s+records?))\b'
    ]

    def redact_pii(self, text: str) -> Tuple[str, List[str]]:
        """
        Detects and redacts Personal Identifiable Information (PII) from user queries:
        - Emails
        - Phone numbers (Indian & International E.164)
        - Credit / Debit card candidate numbers
        - National Identifiers (Indian PAN, Aadhaar, US SSN)
        Returns: (sanitized_text, list_of_redacted_pii_types)
        """
        if not text or not settings.ENABLE_PII_REDACTION:
            return text, []

        redacted_types = []
        sanitized = text

        # 1. Email Redaction
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        if re.search(email_pattern, sanitized):
            sanitized = re.sub(email_pattern, '[REDACTED_EMAIL]', sanitized)
            redacted_types.append("email")

        # 2. Phone Numbers (Indian 10-digit mobile, +91 prefixes, US/Intl formats)
        phone_patterns = [
            r'(\+91[\-\s]?)?[6789]\d{9}\b',
            r'\b(\+1[\-\s]?)?\(?\d{3}\)?[\-\s]?\d{3}[\-\s]?\d{4}\b'
        ]
        for pat in phone_patterns:
            if re.search(pat, sanitized):
                sanitized = re.sub(pat, '[REDACTED_PHONE]', sanitized)
                redacted_types.append("phone")

        # 3. Credit / Debit Cards (13 to 16 digits grouped or contiguous)
        card_pattern = r'\b(?:\d{4}[\-\s]?){3}\d{4}\b|\b\d{16}\b'
        if re.search(card_pattern, sanitized):
            sanitized = re.sub(card_pattern, '[REDACTED_CARD]', sanitized)
            redacted_types.append("credit_card")

        # 4. National IDs: Indian PAN (5 letters + 4 digits + 1 letter), Aadhaar (12 digits), US SSN (3-2-4)
        id_patterns = [
            (r'\b[A-Z]{5}[0-9]{4}[A-Z]\b', '[REDACTED_PAN_ID]', 'pan_card'),
            (r'\b\d{4}[\s\-]?\d{4}[\s\-]?\d{4}\b', '[REDACTED_AADHAAR_ID]', 'aadhaar_id'),
            (r'\b\d{3}\-\d{2}\-\d{4}\b', '[REDACTED_SSN]', 'ssn')
        ]
        for pat, repl, label in id_patterns:
            if re.search(pat, sanitized, re.IGNORECASE):
                sanitized = re.sub(pat, repl, sanitized, flags=re.IGNORECASE)
                redacted_types.append(label)

        return sanitized, list(set(redacted_types))

    def normalize_query(self, query: str) -> str:
        """
        Collapses spelled-out letters (e.g. 'm s m a r c o' -> 'MSMARCO'),
        strips conversational preamble/fillers, normalizes acronyms, and redacts PII.
        """
        if not query:
            return ""
        
        # Redact PII first
        sanitized, _ = self.redact_pii(query)
        normalized = sanitized.strip()

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

    def expand_query(self, query: str) -> str:
        """
        HyDE-style semantic query expansion for short or ambiguous voice queries.
        Appends relevant domain keywords to broaden lexical & dense recall.
        """
        q = self.normalize_query(query)
        words = q.split()
        if len(words) > 5:
            return q

        expansions = {
            r'\bfaiss\b': 'FAISS vector similarity search index algorithms',
            r'\bbm25\b': 'BM25 probabilistic relevance ranking term frequency IDF',
            r'\brrf\b': 'Reciprocal Rank Fusion hybrid retrieval rankings',
            r'\bmsmarco\b': 'MSMARCO multilingual Indian language passages dataset',
            r'\bsarvam\b': 'Sarvam AI speech to text transcription models',
            r'\bvast\b': 'VAST variable adaptive semantic text chunking',
            r'\brag\b': 'Retrieval-Augmented Generation hallucinations groundedness',
            r'\bgoa\b': 'Goa culture hackathons developer ecosystem Western India'
        }

        expanded = q
        for pattern, enriched in expansions.items():
            if re.search(pattern, q, re.IGNORECASE):
                # Avoid duplicating exact word
                expanded = f"{q} ({enriched})"
                break

        return expanded

    def reformulate_query(self, query: str) -> str:
        """
        Corrective RAG (CRAG) query reformulation:
        Simplifies query to high-information keywords when initial retrieval confidence is weak.
        """
        stop_words = {
            "what", "is", "the", "a", "an", "are", "how", "does", "do", "did", "tell",
            "me", "about", "in", "on", "for", "of", "to", "with", "by", "from", "at",
            "can", "you", "give", "some", "which", "where", "when", "who", "why", "explain"
        }
        tokens = re.findall(r'[a-zA-Z0-9_\-]+', query)
        core_terms = [t for t in tokens if t.lower() not in stop_words and len(t) > 1]
        if core_terms:
            return " ".join(core_terms)
        return query

