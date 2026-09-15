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

    def strip_disfluencies(self, query: str) -> str:
        """
        Removes verbal hesitations, speech disfluencies, and filler words from voice transcripts:
        - English: 'umm', 'uh', 'uhm', 'er', 'ah', 'like', 'you know', 'basically', 'actually', 'sort of', 'kind of', 'i mean'
        - Indic: 'matlab', 'accha', 'arrey', 'toh', 'hmmm'
        """
        if not query:
            return ""

        cleaned = query
        disfluency_patterns = [
            r'\b(u+m+|u+h+|u+h+m+|e+r+|a+h+|h+m+m+)\b',
            r'\b(you\s+know|i\s+mean|sort\s+of|kind\s+of|so\s+yeah)\b',
            r'\b(basically|actually|literally)\b',
            r'\b(matlab|accha|arrey|toh\s+bhai|bhai)\b',
            r'\b(like\s+(can|could|tell|what|how|why|is|are)|like)\b'
        ]
        for pat in disfluency_patterns:
            cleaned = re.sub(pat, ' ', cleaned, flags=re.IGNORECASE)

        # Collapse excess whitespace
        return re.sub(r'\s+', ' ', cleaned).strip()

    def detect_language(self, query: str) -> Dict[str, Any]:
        """
        Detects query language and script type for Indic/English auto-routing.
        Supports: Devanagari (Hindi/Marathi), Tamil, Telugu, Bengali, Gujarati, Kannada, Malayalam, Punjabi, Odia, and Latin (English/Hinglish).
        """
        if not query:
            return {"language": "English", "language_code": "en-IN", "script": "Latin"}

        # Check Unicode script ranges
        for char in query:
            code = ord(char)
            if 0x0900 <= code <= 0x097F:
                return {"language": "Hindi", "language_code": "hi-IN", "script": "Devanagari"}
            elif 0x0B80 <= code <= 0x0BFF:
                return {"language": "Tamil", "language_code": "ta-IN", "script": "Tamil"}
            elif 0x0C00 <= code <= 0x0C7F:
                return {"language": "Telugu", "language_code": "te-IN", "script": "Telugu"}
            elif 0x0980 <= code <= 0x09FF:
                return {"language": "Bengali", "language_code": "bn-IN", "script": "Bengali"}
            elif 0x0A80 <= code <= 0x0AFF:
                return {"language": "Gujarati", "language_code": "gu-IN", "script": "Gujarati"}
            elif 0x0C80 <= code <= 0x0CFF:
                return {"language": "Kannada", "language_code": "kn-IN", "script": "Kannada"}
            elif 0x0D00 <= code <= 0x0D7F:
                return {"language": "Malayalam", "language_code": "ml-IN", "script": "Malayalam"}
            elif 0x0A00 <= code <= 0x0A7F:
                return {"language": "Punjabi", "language_code": "pa-IN", "script": "Gurmukhi"}
            elif 0x0B00 <= code <= 0x0B7F:
                return {"language": "Odia", "language_code": "or-IN", "script": "Odia"}

        # Latin Script - Check for Hinglish / Romanized Hindi cues
        hinglish_words = {"kya", "kaise", "batao", "hai", "hota", "karo", "kyun", "kahan", "samjhao"}
        words = set(re.findall(r'\b\w+\b', query.lower()))
        if words.intersection(hinglish_words):
            return {"language": "Hinglish", "language_code": "hi-IN", "script": "Latin"}

        return {"language": "English", "language_code": "en-IN", "script": "Latin"}

    SPELL_CORRECTIONS = {
        # RAG / AI domain
        "waht": "what",
        "wat": "what",
        "wht": "what",
        "whr": "where",
        "wher": "where",
        "locatd": "located",
        "locted": "located",
        "famus": "famous",
        "famouse": "famous",
        "famoous": "famous",
        "bechs": "beaches",
        "beches": "beaches",
        "beache": "beaches",
        "algo": "algorithm",
        "algoritm": "algorithm",
        "latncy": "latency",
        "letency": "latency",
        "retreival": "retrieval",
        "retrival": "retrieval",
        "retreval": "retrieval",
        "embeding": "embedding",
        "embedings": "embeddings",
        "vectr": "vector",
        "vecter": "vector",
        "sarvm": "Sarvam",
        "sarvan": "Sarvam",
        "sarvaam": "Sarvam",
        "fais": "FAISS",
        "faiss": "FAISS",
        "fase": "FAISS",
        "faas": "FAISS",
        "gound": "grounded",
        "grownded": "grounded",
        "halucination": "hallucination",
        "halucinations": "hallucinations",
        "hallucenation": "hallucination",
        "indec": "index",
        "indeces": "indexes",
        "chunkng": "chunking",
        "chuncking": "chunking",
        "chank": "chunk",
        "databse": "database",
        "datbase": "database",
        "plr": "PLI",
        "ply": "PLI",
        "plai": "PLI",
        # General knowledge
        "captial": "capital",
        "captal": "capital",
        "counrty": "country",
        "contry": "country",
        "populaton": "population",
        "populaion": "population",
        "presiedent": "president",
        "presdent": "president",
        "goverment": "government",
        "govenment": "government",
        "parliment": "parliament",
        "parliment": "parliament",
        "sciene": "science",
        "scienec": "science",
        "histry": "history",
        "histroy": "history",
        "geograpy": "geography",
        "geografy": "geography",
        "tecnology": "technology",
        "tecnolgy": "technology",
        "medicne": "medicine",
        "medcine": "medicine",
        "ecnomy": "economy",
        "econmy": "economy",
        "mathmatcs": "mathematics",
        "mathmatics": "mathematics",
        "enviroment": "environment",
        "enviornment": "environment",
        "univers": "universe",
        "univrese": "universe",
        "astrnomy": "astronomy",
        "astronmy": "astronomy",
        "philosphy": "philosophy",
        "philosofy": "philosophy",
        "biolgy": "biology",
        "biolgoy": "biology",
        "chemstry": "chemistry",
        "chemisty": "chemistry",
        "physcs": "physics",
        "physic": "physics",
    }

    def correct_spelling(self, query: str) -> str:
        """
        Lightweight fast spell-correction & phonetic normalization for common voice STT transcription artifacts.
        """
        if not query:
            return ""
        tokens = query.split()
        corrected = []
        for t in tokens:
            # Preserve punctuation on edges
            m = re.match(r'^([^\w]*)([\w\-]+)([^\w]*)$', t)
            if m:
                pre, word, post = m.groups()
                w_lower = word.lower()
                repl = self.SPELL_CORRECTIONS.get(w_lower, word)
                corrected.append(f"{pre}{repl}{post}")
            else:
                corrected.append(t)
        return " ".join(corrected)

    def normalize_query(self, query: str) -> str:
        """
        Collapses spelled-out letters (e.g. 'm s m a r c o' -> 'MSMARCO'),
        strips disfluencies, preamble/fillers, fixes spelling errors, normalizes acronyms, and redacts PII.
        """
        if not query:
            return ""
        
        # 1. Strip disfluencies & speech fillers
        clean_speech = self.strip_disfluencies(query)

        # 2. Spell-correct voice transcription slips
        spelled = self.correct_spelling(clean_speech)

        # 3. Redact PII
        sanitized, _ = self.redact_pii(spelled)
        normalized = sanitized.strip()

        # 4. Strip conversational preamble / filler phrases
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

        # 5. Collapse spelled-out sequences: 'm s m a r c o' -> 'msmarco', 'f a i s s' -> 'faiss'
        normalized = re.sub(r'\b([a-zA-Z]\s+){2,}[a-zA-Z]\b', lambda m: re.sub(r'\s+', '', m.group(0)), normalized)
        # 6. Handle dot-separated letters: 'm.s.m.a.r.c.o' -> 'msmarco'
        normalized = re.sub(r'\b([a-zA-Z]\.\s*){2,}[a-zA-Z]\.?', lambda m: re.sub(r'[\.\s]+', '', m.group(0)), normalized)
        # 7. Domain-specific acronym and speech replacements
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
        normalized = re.sub(r'\bp\s*l\s*[riay]\b', 'PLI', normalized, flags=re.IGNORECASE)
        normalized = re.sub(r'\bplr\b', 'PLI', normalized, flags=re.IGNORECASE)
        normalized = re.sub(r'\bply\b', 'PLI', normalized, flags=re.IGNORECASE)
        normalized = re.sub(r'\bpli\s+scheme\b', 'PLI manufacturing scheme', normalized, flags=re.IGNORECASE)
        
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

        # Identity and Bot Description queries
        if re.search(r'\b(what(\'s| is) your name|who are you|what are you|what is july|introduce yourself|tell me about yourself|your name)\b', lower_q):
            return {
                "valid": False,
                "supported": True,
                "confidence": 1.0,
                "reason": "identity_query",
                "message": "I am July, a sub-200ms voice-enabled AI assistant that can answer questions on virtually any topic. How can I help you today?"
            }

        # Capabilities queries
        if re.search(r'\b(what can you do|how can you help|what are your capabilities|what do you do)\b', lower_q):
            return {
                "valid": False,
                "supported": True,
                "confidence": 1.0,
                "reason": "capability_query",
                "message": "I can answer questions across general knowledge, science, history, geography, technology, economics, culture, and more, all with sub-200ms voice synthesis."
            }

        # Greetings
        if re.search(r'^(hi|hello|hey|greetings|good\s+(morning|afternoon|evening))\b', lower_q):
            return {
                "valid": False,
                "supported": True,
                "confidence": 1.0,
                "reason": "greeting_query",
                "message": "Hello! I am July, a sub-200ms voice-enabled grounded RAG platform. How can I help you today?"
            }

        # Small talk / Politeness
        if re.search(r'\b(how are you|how\'re you|how is it going|how do you do)\b', lower_q):
            return {
                "valid": False,
                "supported": True,
                "confidence": 1.0,
                "reason": "smalltalk_query",
                "message": "I'm doing great, ready to answer any questions you have! What would you like to know?"
            }

        if re.search(r'\b(thank you|thanks|thanks a lot|thank you so much)\b', lower_q):
            return {
                "valid": False,
                "supported": True,
                "confidence": 1.0,
                "reason": "politeness_query",
                "message": "You're very welcome! Let me know if you need anything else."
            }

        return {"valid": True, "reason": None, "message": "OK"}

    def expand_query(self, query: str) -> str:
        """
        HyDE-style semantic query expansion for short or ambiguous voice queries.
        Appends relevant domain keywords to broaden lexical & dense recall.
        Covers both RAG/AI domain terms and general knowledge topics.
        """
        q = self.normalize_query(query)
        words = q.split()
        if len(words) > 6:
            return q

        expansions = {
            # RAG / AI infrastructure
            r'\bfaiss\b': 'FAISS vector similarity search index algorithms',
            r'\bbm25\b': 'BM25 probabilistic relevance ranking term frequency IDF',
            r'\brrf\b': 'Reciprocal Rank Fusion hybrid retrieval rankings',
            r'\bmsmarco\b': 'MSMARCO multilingual Indian language passages dataset',
            r'\bsarvam\b': 'Sarvam AI speech to text transcription models',
            r'\bvast\b': 'VAST variable adaptive semantic text chunking',
            r'\brag\b': 'Retrieval-Augmented Generation hallucinations groundedness',
            r'\bgoa\b': 'Goa culture hackathons developer ecosystem Western India',
            # General geography
            r'\bcapital\b': 'capital city country government seat',
            r'\bpopulation\b': 'population people country million',
            r'\blocated\b': 'located country region continent geography',
            r'\bocean\b': 'ocean sea water Pacific Atlantic Indian',
            r'\bmountain\b': 'mountain peak highest elevation Himalayas Everest',
            r'\briver\b': 'river longest Amazon Nile water flow',
            r'\bdesert\b': 'desert Sahara arid hot dry sand',
            # Science
            r'\bphotosynthesis\b': 'photosynthesis plants sunlight glucose oxygen chlorophyll',
            r'\bdna\b': 'DNA genetics double helix chromosomes genes heredity',
            r'\bevolution\b': 'evolution Darwin natural selection species adaptation',
            r'\bquantum\b': 'quantum mechanics physics particles wave-particle duality',
            r'\bgravity\b': 'gravity force mass Newton Einstein relativity',
            r'\bblack\s*hole\b': 'black hole gravity event horizon spacetime singularity',
            r'\bbig\s*bang\b': 'Big Bang universe origin 13.8 billion years expansion',
            r'\bcrispr\b': 'CRISPR gene editing DNA Cas9 genomics',
            # Health & medicine
            r'\bvaccine\b': 'vaccine immunity antibodies pathogens immunisation',
            r'\bdiabetes\b': 'diabetes blood sugar insulin Type 1 Type 2',
            r'\bcancer\b': 'cancer tumour cells chemotherapy treatment disease',
            r'\bimmu(ne|nity)\b': 'immune system white blood cells antibodies lymphocytes',
            # History
            r'\bww2\b|\bworld\s*war\s*2\b|\bworld\s*war\s*ii\b': 'World War II 1939 1945 Allied Nazi Germany Japan',
            r'\brendaissance\b': 'Renaissance Italy 14th century humanism arts science',
            r'\bindustrial\s*revolution\b': 'Industrial Revolution Britain steam power factory manufacturing',
            r'\bindependence\b': 'independence freedom colonial nation Gandhi Nehru 1947',
            # Technology
            r'\bblockchain\b': 'blockchain distributed ledger Bitcoin cryptocurrency',
            r'\bcloud\b': 'cloud computing AWS Azure Google infrastructure',
            r'\bcybersecurity\b': 'cybersecurity encryption firewall threat protection',
            r'\binternet\b': 'Internet TCP/IP ARPANET global network web',
            r'\bpython\b': 'Python programming language code scripting data',
            r'\bai\b|\bartificial\s*intelligence\b': 'artificial intelligence machine learning deep learning neural',
            # Economics
            r'\bgdp\b': 'GDP Gross Domestic Product economy output growth',
            r'\binflation\b': 'inflation prices purchasing power central bank interest rate',
            r'\bstock\s*market\b': 'stock market NYSE shares equity investing trading',
            r'\bcryptocurrency\b': 'cryptocurrency Bitcoin Ethereum blockchain decentralised',
            # Space
            r'\bmoon\b': 'Moon Earth satellite Apollo astronaut lunar orbit',
            r'\bmars\b': 'Mars Red Planet NASA rover Perseverance solar system',
            r'\bsolar\s*system\b': 'solar system Sun planets Mercury Venus Earth Mars Jupiter',
            r'\btelescope\b': 'telescope James Webb Hubble space observatory infrared',
            # India-specific
            r'\bisro\b': 'ISRO Indian Space Research Organisation Chandrayaan satellite',
            r'\btaj\s*mahal\b': 'Taj Mahal Agra Mughal Shah Jahan marble monument UNESCO',
            r'\bupi\b': 'UPI Unified Payments Interface NPCI digital payment India',
            r'\bipl\b': 'IPL Indian Premier League cricket T20 BCCI',
        }

        expanded = q
        for pattern, enriched in expansions.items():
            if re.search(pattern, q, re.IGNORECASE):
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

