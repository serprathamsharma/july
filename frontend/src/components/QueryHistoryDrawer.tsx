import React from 'react';
import { History, X, Clock, ShieldCheck, Zap, ChevronRight, MessageSquare, Trash2 } from 'lucide-react';
import type { RAGPipelineResponse } from '../services/api';

export interface HistoryItem {
  id: string;
  timestamp: string;
  response: RAGPipelineResponse;
}

interface QueryHistoryDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  history: HistoryItem[];
  onSelectQuery: (item: HistoryItem) => void;
  onClearHistory: () => void;
}

export const QueryHistoryDrawer: React.FC<QueryHistoryDrawerProps> = ({
  isOpen,
  onClose,
  history,
  onSelectQuery,
  onClearHistory
}) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-hidden animate-fadeIn">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm transition-opacity"
        onClick={onClose}
      />

      {/* Slide-over Drawer Panel */}
      <div className="fixed inset-y-0 right-0 max-w-full flex pl-10">
        <div className="w-screen max-w-md bg-slate-950/95 border-l border-slate-800 p-6 flex flex-col shadow-2xl backdrop-blur-xl">
          {/* Header */}
          <div className="flex items-center justify-between pb-4 border-b border-slate-800/80 mb-6">
            <div className="flex items-center gap-2.5">
              <div className="p-2 bg-indigo-500/20 text-indigo-400 rounded-xl border border-indigo-500/30">
                <History className="w-5 h-5" />
              </div>
              <div>
                <h2 className="text-base font-bold text-white tracking-wide">Session Query History</h2>
                <p className="text-xs text-slate-400">Past questions & grounded answers in this session</p>
              </div>
            </div>

            <button
              onClick={onClose}
              className="p-2 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition-all"
              title="Close history"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* List of Previous Queries */}
          <div className="flex-1 overflow-y-auto space-y-3 pr-1 custom-scrollbar">
            {history.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-20 text-center text-slate-500">
                <MessageSquare className="w-12 h-12 stroke-1 mb-3 text-slate-600" />
                <p className="text-sm font-medium text-slate-400">No questions asked yet</p>
                <p className="text-xs text-slate-600 mt-1 max-w-xs">Ask questions via microphone or speech to build your session history.</p>
              </div>
            ) : (
              history.map((item) => (
                <div
                  key={item.id}
                  onClick={() => {
                    onSelectQuery(item);
                    onClose();
                  }}
                  className="p-4 rounded-xl glass-panel border border-slate-800/80 hover:border-indigo-500/50 hover:bg-slate-900/80 cursor-pointer transition-all duration-200 group"
                >
                  <div className="flex items-start justify-between gap-2 mb-2">
                    <h3 className="text-sm font-semibold text-slate-100 group-hover:text-indigo-300 transition-colors line-clamp-2">
                      "{item.response.query || item.response.transcription}"
                    </h3>
                    <ChevronRight className="w-4 h-4 text-slate-500 group-hover:text-indigo-400 group-hover:translate-x-0.5 transition-all flex-shrink-0 mt-0.5" />
                  </div>

                  <p className="text-xs text-slate-400 line-clamp-2 leading-relaxed mb-3">
                    {item.response.answer}
                  </p>

                  <div className="flex items-center justify-between text-[11px] font-mono text-slate-500 pt-2 border-t border-slate-800/60">
                    <div className="flex items-center gap-3">
                      <span className="flex items-center gap-1 text-indigo-400">
                        <Zap className="w-3 h-3" />
                        {Math.round(item.response.metrics.total_ms)}ms
                      </span>
                      <span className="flex items-center gap-1 text-emerald-400">
                        <ShieldCheck className="w-3 h-3" />
                        {Math.round(item.response.confidence * 100)}%
                      </span>
                    </div>

                    <span className="flex items-center gap-1 text-slate-500">
                      <Clock className="w-3 h-3" />
                      {item.timestamp}
                    </span>
                  </div>
                </div>
              ))
            )}
          </div>

          {/* Footer with Clear button */}
          {history.length > 0 && (
            <div className="pt-4 mt-4 border-t border-slate-800/80 flex justify-between items-center">
              <span className="text-xs font-mono text-slate-500">{history.length} queries stored</span>
              <button
                onClick={onClearHistory}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-rose-400 hover:text-rose-300 hover:bg-rose-950/30 border border-rose-900/40 rounded-lg transition-all"
              >
                <Trash2 className="w-3.5 h-3.5" />
                <span>Clear History</span>
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
