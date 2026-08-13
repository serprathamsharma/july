import React, { useState } from 'react';
import { Sparkles, BookOpen, ShieldCheck, AlertTriangle, ExternalLink } from 'lucide-react';
import type { RAGPipelineResponse, RetrievedChunkPayload } from '../services/api';
import { LatencyBadge } from './LatencyBadge';
import { SourceExplorer } from './SourceExplorer';

interface AnswerCardProps {
  response: RAGPipelineResponse;
  selectedMode: 'RAG' | 'End-to-End';
  onModeToggle: (mode: 'RAG' | 'End-to-End') => void;
}

export const AnswerCard: React.FC<AnswerCardProps> = ({ response, selectedMode, onModeToggle }) => {
  const [selectedChunk, setSelectedChunk] = useState<RetrievedChunkPayload | null>(null);

  const isAbstention = !response.supported || response.answer.includes("couldn't find enough");

  return (
    <div className="w-full max-w-3xl glass-panel rounded-2xl p-6 sm:p-8 shadow-2xl border border-slate-800 animate-fadeIn my-6">
      {/* Header bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 mb-6 border-b border-slate-800/80">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-indigo-500/20 text-indigo-400 rounded-xl border border-indigo-500/30">
            <Sparkles className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-sm font-semibold tracking-wide text-slate-300 uppercase">Grounded Response</h2>
            {response.transcription && (
              <p className="text-xs text-slate-400 italic">"{response.transcription}"</p>
            )}
          </div>
        </div>

        <LatencyBadge metrics={response.metrics} selectedMode={selectedMode} onModeToggle={onModeToggle} />
      </div>

      {/* Answer Body */}
      <div className="mb-6">
        {isAbstention ? (
          <div className="flex items-start gap-3 p-4 bg-amber-500/10 border border-amber-500/30 rounded-xl text-amber-300 text-sm">
            <AlertTriangle className="w-5 h-5 text-amber-400 flex-shrink-0 mt-0.5" />
            <div>
              <span className="font-semibold block mb-1">Retrieval Guardrail Triggered</span>
              <p className="text-xs text-amber-200/90 leading-relaxed">{response.answer}</p>
            </div>
          </div>
        ) : (
          <p className="text-slate-100 text-base sm:text-lg leading-relaxed font-normal">
            {response.answer}
          </p>
        )}
      </div>

      {/* Metadata & Citations Footer */}
      <div className="pt-4 border-t border-slate-800/80 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        {/* Sources / Citations */}
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-xs text-slate-400 font-medium flex items-center gap-1">
            <BookOpen className="w-3.5 h-3.5" />
            Sources:
          </span>
          {response.retrieved_chunks.length === 0 ? (
            <span className="text-xs text-slate-500 italic">None</span>
          ) : (
            response.retrieved_chunks.map((chunk, idx) => (
              <button
                key={chunk.chunk_id}
                onClick={() => setSelectedChunk(chunk)}
                className="inline-flex items-center gap-1.5 px-3 py-1 bg-slate-800/80 hover:bg-indigo-600/30 text-indigo-300 border border-slate-700/80 hover:border-indigo-500/50 rounded-lg text-xs font-mono transition-all"
              >
                <span>[{idx + 1}] {chunk.chunk_id.split('_').slice(-2).join('_')}</span>
                <ExternalLink className="w-3 h-3 text-indigo-400" />
              </button>
            ))
          )}
        </div>

        {/* Confidence Pill */}
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1 px-2.5 py-1 bg-slate-900/80 rounded-md border border-slate-800 text-[11px] font-mono text-slate-400">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
            Confidence: <span className="text-emerald-400 font-semibold">{Math.round(response.confidence * 100)}%</span>
          </div>
        </div>
      </div>

      {/* Source Explorer Modal */}
      <SourceExplorer chunk={selectedChunk} onClose={() => setSelectedChunk(null)} />
    </div>
  );
};
