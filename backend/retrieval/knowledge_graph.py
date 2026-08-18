import re
from typing import List, Dict, Any

class KnowledgeGraphStore:
    """
    In-memory Knowledge Graph containing entity nodes and relational edges
    extracted from the indexed knowledge base.
    """
    def __init__(self):
        self.nodes: Dict[str, Dict[str, Any]] = {}
        self.edges: List[Dict[str, Any]] = []
        self._initialize_core_graph()

    def _initialize_core_graph(self):
        """Seed the graph with high-value technical & contextual entities from the knowledge base."""
        core_entities = [
            {"id": "july", "label": "July Voice RAG", "type": "System", "category": "Core Platform"},
            {"id": "sarvam_ai", "label": "Sarvam AI", "type": "Provider", "category": "Voice AI"},
            {"id": "gemini", "label": "Google Gemini", "type": "Provider", "category": "LLM Synthesis"},
            {"id": "msmarco_xi", "label": "MSMARCO-XI", "type": "Dataset", "category": "Knowledge Base"},
            {"id": "faiss", "label": "FAISS Index", "type": "Algorithm", "category": "Vector Search"},
            {"id": "bm25", "label": "BM25 Search", "type": "Algorithm", "category": "Lexical Search"},
            {"id": "rrf", "label": "Reciprocal Rank Fusion", "type": "Algorithm", "category": "Score Fusion"},
            {"id": "cross_encoder", "label": "Cross-Encoder Re-Ranker", "type": "Algorithm", "category": "Precision Tuning"},
            {"id": "vast_chunking", "label": "VAST Chunking", "type": "Technique", "category": "Ingestion"},
            {"id": "guardrails", "label": "Guardrails Layer", "type": "Security", "category": "Safety & PII"},
            {"id": "sqlite_analytics", "label": "SQLite Analytics", "type": "Storage", "category": "Telemetry"},
            {"id": "crag", "label": "Corrective RAG", "type": "Technique", "category": "Self-Reflection"},
            {"id": "hh_goa_2026", "label": "Hacker House Goa 2026", "type": "Event", "category": "Hackathon"},
            {"id": "goa", "label": "Goa, India", "type": "Location", "category": "Geography"},
            {"id": "pli_scheme", "label": "PLI Scheme", "type": "Policy", "category": "Economics"},
        ]

        for entity in core_entities:
            self.add_node(entity["id"], entity["label"], entity["type"], entity.get("category", "General"))

        core_relations = [
            ("july", "sarvam_ai", "integrates_with", "Voice STT & Bulbul TTS"),
            ("july", "gemini", "synthesizes_via", "Grounded Generative LLM"),
            ("july", "msmarco_xi", "indexes_documents_from", "1,000+ Passages"),
            ("july", "faiss", "retrieves_dense_vectors_via", "Dense Similarity"),
            ("july", "bm25", "retrieves_lexical_terms_via", "Sparse Term Scoring"),
            ("july", "rrf", "fuses_rankings_with", "Reciprocal Rank Fusion (k=60)"),
            ("july", "cross_encoder", "reranks_candidates_using", "Cross-Attention Scoring"),
            ("july", "vast_chunking", "partitions_text_using", "Hierarchical Windows"),
            ("july", "guardrails", "protects_queries_via", "PII Redaction & Injection Defense"),
            ("july", "sqlite_analytics", "persists_telemetry_to", "P50/P70/P100 Metrics"),
            ("july", "crag", "recovers_marginal_queries_via", "Dynamic Reformulation"),
            ("july", "hh_goa_2026", "developed_for", "Sub-200ms Voice RAG Track"),
            ("hh_goa_2026", "goa", "hosted_in", "Coastal Tech Hub"),
            ("msmarco_xi", "pli_scheme", "contains_domain_data_on", "Manufacturing & Subsidies"),
            ("msmarco_xi", "goa", "contains_geography_data_on", "Culture, Tourism & Economy"),
        ]

        for source, target, relation, details in core_relations:
            self.add_edge(source, target, relation, details)

    def add_node(self, node_id: str, label: str, node_type: str, category: str = "General") -> Dict[str, Any]:
        node = {
            "id": node_id,
            "label": label,
            "type": node_type,
            "category": category,
            "degree": 0
        }
        if node_id not in self.nodes:
            self.nodes[node_id] = node
        return self.nodes[node_id]

    def add_edge(self, source: str, target: str, relation: str, details: str = ""):
        if source not in self.nodes or target not in self.nodes:
            return
        edge = {
            "source": source,
            "target": target,
            "relation": relation,
            "details": details
        }
        self.edges.append(edge)
        self.nodes[source]["degree"] = self.nodes[source].get("degree", 0) + 1
        self.nodes[target]["degree"] = self.nodes[target].get("degree", 0) + 1

    def extract_and_ingest_triples(self, document_id: str, text: str):
        """
        Lightweight rule-based entity and relation extraction from newly ingested text.
        """
        if not text:
            return
        candidates = set(re.findall(r'\b[A-Z][a-zA-Z0-9\-_]{2,}(?:\s+[A-Z][a-zA-Z0-9\-_]{2,})*\b', text))
        
        extracted_ids = []
        for cand in list(candidates)[:6]:
            clean_id = cand.lower().replace(" ", "_")
            if clean_id not in self.nodes:
                self.add_node(clean_id, cand, "DynamicEntity", f"Doc: {document_id}")
            extracted_ids.append(clean_id)

        for ent_id in extracted_ids:
            self.add_edge("july", ent_id, "indexes_entity", f"Extracted from {document_id}")

    def get_graph(self) -> Dict[str, Any]:
        """Returns the full node-link graph payload."""
        return {
            "nodes": list(self.nodes.values()),
            "edges": self.edges,
            "stats": {
                "total_nodes": len(self.nodes),
                "total_edges": len(self.edges),
                "categories": list(set(n.get("category", "General") for n in self.nodes.values()))
            }
        }

knowledge_graph = KnowledgeGraphStore()
