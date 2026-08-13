import React from 'react';
import { Zap, Clock } from 'lucide-react';
import { LatencyMetrics } from '../services/api';

interface LatencyBadgeProps {
  metrics: LatencyMetrics;
  selectedMode: 'RAG' | 'End-to-End';
  onModeToggle: (mode: 'RAG' | 'End-to-End') => void;
}

export const LatencyBadge: React.FC<LatencyBadgeProps> = ({ metrics, selectedMode, onModeToggle }) => {
  const ragLatency = roundVal(
    metrics.query_processing_ms +
    metrics.embedding_ms +
    metrics.dense_retrieval_ms +
    metrics.bm25_ms +
    metrics.fusion_ms +
    metrics.generation_ms +
    metrics.guardrail_ms
  );

  const displayLatency = selectedMode === 'End-to-End' ? metrics.total_ms : ragLatency;
  const isSub200 = displayLatency <= 200;

  function roundVal(num: number) {
    return Math.round(num * 10) / 10;
  }

  return (
    <div className="flex flex-col sm:flex-row items-center gap-3">
      {/* Mode Switcher Pills */}
      <div className="flex items-center bg-slate-900/80 p-1 rounded-lg border border-slate-800 text-xs font-medium">
        <button
          onClick={() => onModeToggle('RAG')}
          className={`px-3 py-1 rounded-md transition-all ${
            selectedMode === 'RAG'
              ? 'bg-indigo-600 text-white shadow-sm'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          RAG Latency
        </button>
        <button
          onClick={() => onModeToggle('End-to-End')}
          className={`px-3 py-1 rounded-md transition-all ${
            selectedMode === 'End-to-End'
              ? 'bg-indigo-600 text-white shadow-sm'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          End-to-End Voice
        </button>
      </div>

      {/* Latency Output Pill */}
      <div
        className={`flex items-center gap-2 px-3.5 py-1.5 rounded-full text-xs font-semibold tracking-wide border transition-all ${
          isSub200
            ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30 shadow-[0_0_15px_rgba(16,185,129,0.2)]'
            : 'bg-indigo-500/10 text-indigo-300 border-indigo-500/30'
        }`}
      >
        <Zap className={`w-3.5 h-3.5 ${isSub200 ? 'text-emerald-400 fill-emerald-400' : 'text-indigo-400'}`} />
        <span>⚡ {displayLatency} ms</span>
        {isSub200 && <span className="bg-emerald-500/20 text-emerald-300 text-[10px] px-1.5 py-0.5 rounded font-mono uppercase">Target Hit</span>}
      </div>
    </div>
  );
};
