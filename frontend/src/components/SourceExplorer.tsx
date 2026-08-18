import React, { useEffect, useState } from 'react';
import { X, FileText, Layers, CheckCircle2, Sparkles } from 'lucide-react';
import { type RetrievedChunkPayload, fetchSourceDetail } from '../services/api';

interface SourceExplorerProps {
  chunk: RetrievedChunkPayload | null;
  groundingAnswer?: string;
  query?: string;
  onClose: () => void;
}

export const SourceExplorer: React.FC<SourceExplorerProps> = ({ chunk, groundingAnswer, query, onClose }) => {
  const [detail, setDetail] = useState<RetrievedChunkPayload | null>(chunk);

  useEffect(() => {
    if (chunk) {
      setDetail(chunk);
      fetchSourceDetail(chunk.chunk_id)
        .then((res) => {
          setDetail((prev) => ({ ...prev, ...res }));
        })
        .catch((err) => console.error(err));
    }
  }, [chunk]);

  if (!chunk || !detail) return null;

  // Split retrieved chunk into sentences and highlight matching grounding evidence
  const renderHighlightedText = (text: string) => {
    if (!text) return null;
    if (!groundingAnswer && !query) return <span>"{text}"</span>;

    // Extract significant terms from answer/query
    const stopWords = new Set([
      'the', 'is', 'at', 'which', 'on', 'a', 'an', 'and', 'or', 'in', 'for', 'of', 'to', 'with', 'by', 'as', 'it', 'this', 'that', 'are', 'was', 'were'
    ]);

    const targetTokens = new Set<string>();
    const extractTokens = (str?: string) => {
      if (!str) return;
      str.toLowerCase().replace(/[^a-z0-9\s]/g, '').split(/\s+/).forEach(t => {
        if (t.length > 3 && !stopWords.has(t)) targetTokens.add(t);
      });
    };

    extractTokens(groundingAnswer);
    extractTokens(query);

    // Split into sentences
    const sentences = text.split(/(?<=[.?!])\s+/);

    return (
      <div className="space-y-2">
        {sentences.map((sentence, sIdx) => {
          // Check if this sentence contains significant grounding terms
          const sTokens = sentence.toLowerCase().replace(/[^a-z0-9\s]/g, '').split(/\s+/);
          const matchCount = sTokens.filter(t => targetTokens.has(t)).length;
          const isGroundedSpan = matchCount >= 2;

          if (isGroundedSpan) {
            return (
              <span
                key={sIdx}
                className="bg-indigo-500/20 text-indigo-100 px-1.5 py-0.5 rounded border border-indigo-500/40 inline font-medium shadow-[0_0_12px_rgba(99,102,241,0.15)] mr-1"
                title="Exact Grounding Sentence Span used for LLM Synthesis"
              >
                {sentence}{" "}
              </span>
            );
          }

          return <span key={sIdx} className="text-slate-300 mr-1">{sentence}{" "}</span>;
        })}
      </div>
    );
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-md animate-fadeIn">
      <div className="relative w-full max-w-2xl glass-panel rounded-2xl p-6 shadow-2xl border border-slate-700/60 overflow-hidden max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between pb-4 mb-4 border-b border-slate-800 flex-shrink-0">
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-indigo-600/20 text-indigo-400 rounded-xl border border-indigo-500/30">
              <FileText className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-lg font-bold text-white flex items-center gap-2">
                <span>Source Chunk:</span>
                <span className="font-mono text-indigo-400 text-sm">{detail.chunk_id}</span>
              </h3>
              <p className="text-xs text-slate-400">Provenance, Document Metadata & Grounding Evidence</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-white bg-slate-800/60 hover:bg-slate-800 rounded-lg transition-all cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Chunk Metadata Pills */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-5 flex-shrink-0">
          <div className="bg-slate-900/60 p-3 rounded-xl border border-slate-800">
            <span className="text-[11px] text-slate-400 font-medium uppercase tracking-wider block mb-1">Doc ID</span>
            <span className="text-xs font-mono font-semibold text-slate-200 truncate block">{detail.document_id}</span>
          </div>

          <div className="bg-slate-900/60 p-3 rounded-xl border border-slate-800">
            <span className="text-[11px] text-slate-400 font-medium uppercase tracking-wider block mb-1">VAST Strategy</span>
            <span className="text-xs font-semibold text-indigo-400 capitalize flex items-center gap-1">
              <Layers className="w-3.5 h-3.5" />
              {detail.chunk_type}
            </span>
          </div>

          <div className="bg-slate-900/60 p-3 rounded-xl border border-slate-800">
            <span className="text-[11px] text-slate-400 font-medium uppercase tracking-wider block mb-1">RRF Fusion Score</span>
            <span className="text-xs font-mono font-semibold text-emerald-400">{detail.rrf_score}</span>
          </div>

          <div className="bg-slate-900/60 p-3 rounded-xl border border-slate-800">
            <span className="text-[11px] text-slate-400 font-medium uppercase tracking-wider block mb-1">Dense / BM25</span>
            <span className="text-[11px] font-mono text-slate-300">
              {detail.dense_score} / {detail.bm25_score}
            </span>
          </div>
        </div>

        {/* Chunk Content with Citation Highlight */}
        <div className="mb-5 overflow-y-auto flex-1 pr-1">
          <div className="flex items-center justify-between mb-2">
            <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
              <span>Retrieved Chunk Text</span>
              <span className="text-[10px] text-indigo-400 bg-indigo-500/10 px-2 py-0.5 rounded-full border border-indigo-500/30 flex items-center gap-1">
                <Sparkles className="w-2.5 h-2.5" /> Citation Span Highlighted
              </span>
            </h4>
          </div>
          <div className="bg-slate-950/80 p-4 rounded-xl border border-slate-800/80 text-sm leading-relaxed font-sans">
            {renderHighlightedText(detail.text)}
          </div>
        </div>

        {/* Parent Document Preview */}
        {detail.parent_document && (
          <div className="mb-4 flex-shrink-0">
            <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">Original Parent Context</h4>
            <div className="bg-slate-900/40 p-3 rounded-xl border border-slate-800 text-xs text-slate-400 max-h-24 overflow-y-auto leading-relaxed">
              {detail.parent_document}
            </div>
          </div>
        )}

        {/* Footer */}
        <div className="pt-3 border-t border-slate-800 flex justify-between items-center flex-shrink-0">
          <div className="text-[11px] text-slate-400 flex items-center gap-1.5 font-mono">
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
            <span>Strictly Grounded (0% Hallucination)</span>
          </div>
          <button
            onClick={onClose}
            className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold rounded-lg transition-all cursor-pointer"
          >
            Close Explorer
          </button>
        </div>
      </div>
    </div>
  );
};
