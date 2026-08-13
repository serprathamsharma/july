import React, { useEffect, useState } from 'react';
import { Activity, Zap, ShieldAlert, Database, Play, BarChart3, RefreshCw } from 'lucide-react';
import { AnalyticsSummary, fetchAnalytics, runBenchmark } from '../services/api';

export const AnalyticsView: React.FC = () => {
  const [data, setData] = useState<AnalyticsSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [runningBenchmark, setRunningBenchmark] = useState(false);

  const loadData = () => {
    setLoading(true);
    fetchAnalytics()
      .then((res) => setData(res))
      .catch((err) => console.error(err))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleRunBenchmark = async () => {
    setRunningBenchmark(true);
    try {
      await runBenchmark();
      loadData();
    } catch (err) {
      console.error(err);
    } finally {
      setRunningBenchmark(false);
    }
  };

  if (loading || !data) {
    return (
      <div className="flex items-center justify-center py-20">
        <RefreshCw className="w-8 h-8 text-indigo-500 animate-spin" />
      </div>
    );
  }

  const { latency, pipeline_breakdown, retrieval, guardrails } = data;

  return (
    <div className="w-full max-w-6xl mx-auto px-4 py-8 animate-fadeIn">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-8 pb-4 border-b border-slate-800">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <Activity className="w-6 h-6 text-indigo-400" />
            Developer & Benchmark Analytics
          </h1>
          <p className="text-sm text-slate-400 mt-1">Real-time sub-millisecond pipeline latency instrumentation & evaluation statistics</p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={loadData}
            className="p-2.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl transition-all"
            title="Refresh Metrics"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
          <button
            onClick={handleRunBenchmark}
            disabled={runningBenchmark}
            className="flex items-center gap-2 px-4 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs rounded-xl shadow-lg shadow-indigo-600/30 transition-all disabled:opacity-50"
          >
            {runningBenchmark ? (
              <RefreshCw className="w-4 h-4 animate-spin" />
            ) : (
              <Play className="w-4 h-4 fill-white" />
            )}
            <span>{runningBenchmark ? 'Evaluating Queries...' : 'Run Benchmark Suite'}</span>
          </button>
        </div>
      </div>

      {/* Latency Percentiles Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <div className="glass-panel rounded-2xl p-6 border border-emerald-500/30 relative overflow-hidden">
          <div className="absolute top-0 right-0 p-4 text-emerald-400/20">
            <Zap className="w-16 h-16" />
          </div>
          <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider block mb-1">P50 Latency</span>
          <div className="text-4xl font-extrabold text-white font-mono tracking-tight">{latency.p50} <span className="text-lg text-emerald-400 font-sans">ms</span></div>
          <span className="text-[11px] text-emerald-400 font-mono mt-2 block">Median Execution Time</span>
        </div>

        <div className="glass-panel rounded-2xl p-6 border border-indigo-500/30 relative overflow-hidden">
          <div className="absolute top-0 right-0 p-4 text-indigo-400/20">
            <BarChart3 className="w-16 h-16" />
          </div>
          <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider block mb-1">P70 Latency</span>
          <div className="text-4xl font-extrabold text-white font-mono tracking-tight">{latency.p70} <span className="text-lg text-indigo-400 font-sans">ms</span></div>
          <span className="text-[11px] text-indigo-400 font-mono mt-2 block">70th Percentile Target</span>
        </div>

        <div className="glass-panel rounded-2xl p-6 border border-amber-500/30 relative overflow-hidden">
          <div className="absolute top-0 right-0 p-4 text-amber-400/20">
            <Activity className="w-16 h-16" />
          </div>
          <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider block mb-1">P100 Max Latency</span>
          <div className="text-4xl font-extrabold text-white font-mono tracking-tight">{latency.p100} <span className="text-lg text-amber-400 font-sans">ms</span></div>
          <span className="text-[11px] text-amber-400 font-mono mt-2 block">Maximum Tail Latency</span>
        </div>
      </div>

      {/* Stage Breakdown & Retrieval Metrics */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
        {/* Pipeline Stage Latency Breakdown */}
        <div className="glass-panel rounded-2xl p-6 border border-slate-800">
          <h3 className="text-base font-bold text-white mb-6 flex items-center gap-2">
            <BarChart3 className="w-5 h-5 text-indigo-400" />
            Pipeline Stage Latency Breakdown (ms)
          </h3>

          <div className="space-y-4">
            {[
              { label: 'Sarvam STT', value: pipeline_breakdown.stt_ms, color: 'bg-rose-500' },
              { label: 'Query Processing', value: pipeline_breakdown.query_processing_ms, color: 'bg-amber-500' },
              { label: 'Embedding Generation', value: pipeline_breakdown.embedding_ms, color: 'bg-yellow-500' },
              { label: 'FAISS Dense Retrieval', value: pipeline_breakdown.dense_retrieval_ms, color: 'bg-indigo-500' },
              { label: 'BM25 Lexical Search', value: pipeline_breakdown.bm25_ms, color: 'bg-blue-500' },
              { label: 'RRF Score Fusion', value: pipeline_breakdown.fusion_ms, color: 'bg-cyan-500' },
              { label: 'Grounded LLM Generation', value: pipeline_breakdown.generation_ms, color: 'bg-emerald-500' },
              { label: 'Guardrail Validation', value: pipeline_breakdown.guardrail_ms, color: 'bg-purple-500' },
            ].map((stage) => (
              <div key={stage.label}>
                <div className="flex justify-between text-xs font-medium mb-1">
                  <span className="text-slate-300">{stage.label}</span>
                  <span className="font-mono text-slate-400">{stage.value} ms</span>
                </div>
                <div className="w-full bg-slate-900 rounded-full h-2 overflow-hidden">
                  <div
                    className={`${stage.color} h-full rounded-full transition-all duration-500`}
                    style={{ width: `${Math.min(100, (stage.value / (pipeline_breakdown.total_ms || 1)) * 100)}%` }}
                  />
                </div>
              </div>
            ))}
          </div>

          <div className="mt-6 pt-4 border-t border-slate-800 flex justify-between items-center text-xs font-mono text-slate-400">
            <span>TOTAL RAG LATENCY:</span>
            <span className="text-emerald-400 font-bold text-sm">{pipeline_breakdown.total_ms} ms</span>
          </div>
        </div>

        {/* Retrieval Metrics & Index Info */}
        <div className="glass-panel rounded-2xl p-6 border border-slate-800">
          <h3 className="text-base font-bold text-white mb-6 flex items-center gap-2">
            <Database className="w-5 h-5 text-indigo-400" />
            Retrieval & Index Benchmark Metrics
          </h3>

          <div className="grid grid-cols-2 gap-4 mb-6">
            <div className="bg-slate-900/60 p-4 rounded-xl border border-slate-800">
              <span className="text-xs text-slate-400 block mb-1">Recall@5 Score</span>
              <span className="text-2xl font-bold font-mono text-emerald-400">{(retrieval.recall_at_5 * 100).toFixed(1)}%</span>
            </div>

            <div className="bg-slate-900/60 p-4 rounded-xl border border-slate-800">
              <span className="text-xs text-slate-400 block mb-1">MRR Score</span>
              <span className="text-2xl font-bold font-mono text-indigo-400">{retrieval.mrr}</span>
            </div>
          </div>

          <div className="space-y-3 text-xs">
            <div className="flex justify-between py-2 border-b border-slate-800">
              <span className="text-slate-400">Indexed Documents:</span>
              <span className="font-mono text-slate-200 font-semibold">{retrieval.indexed_documents}</span>
            </div>

            <div className="flex justify-between py-2 border-b border-slate-800">
              <span className="text-slate-400">Total VAST Chunks:</span>
              <span className="font-mono text-slate-200 font-semibold">{retrieval.indexed_chunks}</span>
            </div>

            <div className="flex justify-between py-2 border-b border-slate-800">
              <span className="text-slate-400">Chunking Strategy:</span>
              <span className="font-semibold text-indigo-400">{retrieval.active_chunking_strategy}</span>
            </div>

            <div className="flex justify-between py-2">
              <span className="text-slate-400">Embedding Model:</span>
              <span className="font-mono text-slate-300">{retrieval.embedding_model}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Guardrails Summary */}
      <div className="glass-panel rounded-2xl p-6 border border-slate-800">
        <h3 className="text-base font-bold text-white mb-6 flex items-center gap-2">
          <ShieldAlert className="w-5 h-5 text-indigo-400" />
          Guardrails Audit Log
        </h3>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div className="bg-slate-900/60 p-4 rounded-xl border border-slate-800 text-center">
            <span className="text-xs text-slate-400 block mb-1">Queries Rejected</span>
            <span className="text-2xl font-mono font-bold text-rose-400">{guardrails.queries_rejected}</span>
          </div>

          <div className="bg-slate-900/60 p-4 rounded-xl border border-slate-800 text-center">
            <span className="text-xs text-slate-400 block mb-1">Low-Confidence Abstentions</span>
            <span className="text-2xl font-mono font-bold text-amber-400">{guardrails.low_confidence_abstentions}</span>
          </div>

          <div className="bg-slate-900/60 p-4 rounded-xl border border-slate-800 text-center">
            <span className="text-xs text-slate-400 block mb-1">Grounding Failures Replaced</span>
            <span className="text-2xl font-mono font-bold text-indigo-400">{guardrails.grounding_failures}</span>
          </div>

          <div className="bg-slate-900/60 p-4 rounded-xl border border-slate-800 text-center">
            <span className="text-xs text-slate-400 block mb-1">Unsafe Queries Blocked</span>
            <span className="text-2xl font-mono font-bold text-emerald-400">{guardrails.unsafe_queries_blocked}</span>
          </div>
        </div>
      </div>
    </div>
  );
};
