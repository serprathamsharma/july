import React, { useEffect, useState } from 'react';
import { X, FileText, Layers } from 'lucide-react';
import { type RetrievedChunkPayload, fetchSourceDetail } from '../services/api';

interface SourceExplorerProps {
  chunk: RetrievedChunkPayload | null;
  onClose: () => void;
}

export const SourceExplorer: React.FC<SourceExplorerProps> = ({ chunk, onClose }) => {
  const [detail, setDetail] = useState<RetrievedChunkPayload | null>(chunk);

  useEffect(() => {
    if (chunk) {
      setDetail(chunk);
      // Fetch fresh backend details
      fetchSourceDetail(chunk.chunk_id)
        .then((res) => {
          setDetail((prev) => ({ ...prev, ...res }));
        })
        .catch((err) => console.error(err));
    }
  }, [chunk]);

  if (!chunk || !detail) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-md animate-fadeIn">
      <div className="relative w-full max-w-2xl glass-panel rounded-2xl p-6 shadow-2xl border border-slate-700/60 overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between pb-4 mb-4 border-b border-slate-800">
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-indigo-600/20 text-indigo-400 rounded-xl border border-indigo-500/30">
              <FileText className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-lg font-bold text-white flex items-center gap-2">
                Source Chunk: <span className="font-mono text-indigo-400 text-sm">{detail.chunk_id}</span>
              </h3>
              <p className="text-xs text-slate-400">Provenance & Document Metadata</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-white bg-slate-800/60 hover:bg-slate-800 rounded-lg transition-all"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Chunk Metadata Pills */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-5">
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

        {/* Chunk Content */}
        <div className="mb-5">
          <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">Retrieved Chunk Text</h4>
          <div className="bg-slate-950/80 p-4 rounded-xl border border-slate-800/80 text-sm text-slate-200 leading-relaxed font-sans">
            "{detail.text}"
          </div>
        </div>

        {/* Parent Document Preview */}
        {detail.parent_document && (
          <div className="mb-4">
            <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">Original Parent Context</h4>
            <div className="bg-slate-900/40 p-3 rounded-xl border border-slate-800 text-xs text-slate-400 max-h-28 overflow-y-auto leading-relaxed">
              {detail.parent_document}
            </div>
          </div>
        )}

        {/* Footer */}
        <div className="pt-3 border-t border-slate-800 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold rounded-lg transition-all"
          >
            Close Explorer
          </button>
        </div>
      </div>
    </div>
  );
};
