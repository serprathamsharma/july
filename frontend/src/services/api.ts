import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000/api';

export interface LatencyMetrics {
  request_id: str;
  stt_ms: number;
  query_processing_ms: number;
  embedding_ms: number;
  dense_retrieval_ms: number;
  bm25_ms: number;
  fusion_ms: number;
  generation_ms: number;
  guardrail_ms: number;
  total_ms: number;
  mode: string;
}

export interface RetrievedChunkPayload {
  chunk_id: string;
  document_id: string;
  chunk_type: string;
  text: string;
  rrf_score: number;
  dense_score: number;
  bm25_score: number;
  parent_document: string;
  position: number;
}

export interface RAGPipelineResponse {
  request_id: string;
  query: string;
  transcription?: string;
  answer: string;
  supported: boolean;
  confidence: number;
  citations: string[];
  retrieved_chunks: RetrievedChunkPayload[];
  metrics: LatencyMetrics;
}

export interface AnalyticsSummary {
  latency: {
    p50: number;
    p70: number;
    p100: number;
    sample_count: number;
  };
  pipeline_breakdown: {
    stt_ms: number;
    query_processing_ms: number;
    embedding_ms: number;
    dense_retrieval_ms: number;
    bm25_ms: number;
    fusion_ms: number;
    generation_ms: number;
    guardrail_ms: number;
    total_ms: number;
  };
  retrieval: {
    recall_at_1: number;
    recall_at_5: number;
    mrr: number;
    indexed_documents: number;
    indexed_chunks: number;
    active_chunking_strategy: string;
    embedding_model: string;
  };
  guardrails: {
    queries_total: number;
    queries_rejected: number;
    low_confidence_abstentions: number;
    grounding_failures: number;
    unsafe_queries_blocked: number;
  };
}

export const processTextQuery = async (query: string, mode: string = "RAG"): Promise<RAGPipelineResponse> => {
  const response = await axios.post<RAGPipelineResponse>(`${API_BASE_URL}/text/query`, { query, mode });
  return response.data;
};

export const processVoiceQuery = async (audioBlob: Blob, languageCode: string = "en-IN"): Promise<RAGPipelineResponse> => {
  const formData = new FormData();
  formData.append('file', audioBlob, 'recording.wav');
  formData.append('language_code', languageCode);

  const response = await axios.post<RAGPipelineResponse>(`${API_BASE_URL}/voice/query`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  });
  return response.data;
};

export const fetchAnalytics = async (): Promise<AnalyticsSummary> => {
  const response = await axios.get<AnalyticsSummary>(`${API_BASE_URL}/analytics`);
  return response.data;
};

export const fetchSourceDetail = async (chunkId: string): Promise<RetrievedChunkPayload> => {
  const response = await axios.get<RetrievedChunkPayload>(`${API_BASE_URL}/sources/${chunkId}`);
  return response.data;
};

export const runBenchmark = async (): Promise<any> => {
  const response = await axios.post(`${API_BASE_URL}/benchmark/run`);
  return response.data;
};
