from typing import List, Dict, Any, Tuple
from pydantic import BaseModel
from backend.chunking.vast import ChunkMetadata

class ScoredChunk(BaseModel):
    chunk: ChunkMetadata
    rrf_score: float
    dense_score: float = 0.0
    bm25_score: float = 0.0
    dense_rank: int = 999
    bm25_rank: int = 999

def reciprocal_rank_fusion(
    dense_results: List[Tuple[ChunkMetadata, float, int]],
    bm25_results: List[Tuple[ChunkMetadata, float, int]],
    w_dense: float = 0.5,
    w_bm25: float = 0.5,
    rrf_k: int = 60,
    top_k: int = 5
) -> List[ScoredChunk]:
    """
    Reciprocal Rank Fusion (RRF) combining dense vector and lexical BM25 rankings.
    """
    score_map: Dict[str, Dict[str, Any]] = {}

    # Process Dense Results
    for chunk, score, rank in dense_results:
        c_id = chunk.chunk_id
        if c_id not in score_map:
            score_map[c_id] = {
                "chunk": chunk,
                "dense_score": score,
                "bm25_score": 0.0,
                "dense_rank": rank,
                "bm25_rank": 999
            }
        else:
            score_map[c_id]["dense_score"] = score
            score_map[c_id]["dense_rank"] = rank

    # Process BM25 Results
    for chunk, score, rank in bm25_results:
        c_id = chunk.chunk_id
        if c_id not in score_map:
            score_map[c_id] = {
                "chunk": chunk,
                "dense_score": 0.0,
                "bm25_score": score,
                "dense_rank": 999,
                "bm25_rank": rank
            }
        else:
            score_map[c_id]["bm25_score"] = score
            score_map[c_id]["bm25_rank"] = rank

    # Calculate RRF Score
    fusion_list: List[ScoredChunk] = []
    for c_id, item in score_map.items():
        r_dense = item["dense_rank"]
        r_bm25 = item["bm25_rank"]

        rrf_val = 0.0
        if r_dense < 999:
            rrf_val += w_dense / (rrf_k + r_dense)
        if r_bm25 < 999:
            rrf_val += w_bm25 / (rrf_k + r_bm25)

        fusion_list.append(ScoredChunk(
            chunk=item["chunk"],
            rrf_score=round(rrf_val, 6),
            dense_score=round(item["dense_score"], 4),
            bm25_score=round(item["bm25_score"], 4),
            dense_rank=r_dense,
            bm25_rank=r_bm25
        ))

    # Sort descending by RRF score
    fusion_list.sort(key=lambda x: x.rrf_score, reverse=True)
    return fusion_list[:top_k]
