import React, { useState } from 'react';
import { Mic, Send, Activity, Sparkles, Database, HelpCircle } from 'lucide-react';
import { MicButton, MicState } from './components/MicButton';
import { AnswerCard } from './components/AnswerCard';
import { AnalyticsView } from './components/AnalyticsView';
import { RAGPipelineResponse, processTextQuery, processVoiceQuery } from './services/api';

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'rag' | 'analytics'>('rag');
  const [micState, setMicState] = useState<MicState>('Idle');
  const [textInput, setTextInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState<RAGPipelineResponse | null>(null);
  const [selectedMode, setSelectedMode] = useState<'RAG' | 'End-to-End'>('RAG');

  const sampleQueries = [
    "What is the MSMARCO-XI dataset designed for?",
    "How does RAG reduce LLM hallucinations?",
    "What indexing algorithms are supported by FAISS?",
    "What role do guardrails play in a RAG pipeline?",
    "What is the capital city of Mars?"
  ];

  const handleTextSubmit = async (queryText: string) => {
    if (!queryText.trim() || loading) return;
    setLoading(true);
    setMicState('Generating');

    try {
      const res = await processTextQuery(queryText.trim(), selectedMode);
      setResponse(res);
      setMicState('Complete');
    } catch (err) {
      console.error(err);
      setMicState('Error');
    } finally {
      setLoading(false);
    }
  };

  const handleAudioRecorded = async (audioBlob: Blob) => {
    setLoading(true);
    setMicState('Generating');

    try {
      const res = await processVoiceQuery(audioBlob, 'en-IN');
      setResponse(res);
      setMicState('Complete');
    } catch (err) {
      console.error(err);
      setMicState('Error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#0a0c10] text-slate-100 flex flex-col selection:bg-indigo-500 selection:text-white">
      {/* Header Bar */}
      <header className="w-full glass-panel sticky top-0 z-40 border-b border-slate-800/80 px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          {/* Logo & Title */}
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center shadow-lg shadow-indigo-500/25">
              <Sparkles className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="text-base font-bold text-white tracking-tight flex items-center gap-2">
                HH GOA 2026
                <span className="text-xs font-mono font-normal px-2 py-0.5 rounded bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                  VOICE RAG
                </span>
              </h1>
              <p className="text-xs text-slate-400">Sub-200ms Grounded RAG Infrastructure</p>
            </div>
          </div>

          {/* Navigation Tabs */}
          <nav className="flex items-center gap-2 bg-slate-900/80 p-1 rounded-xl border border-slate-800">
            <button
              onClick={() => setActiveTab('rag')}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold transition-all ${
                activeTab === 'rag'
                  ? 'bg-indigo-600 text-white shadow-md'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Mic className="w-3.5 h-3.5" />
              <span>Voice RAG</span>
            </button>

            <button
              onClick={() => setActiveTab('analytics')}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold transition-all ${
                activeTab === 'analytics'
                  ? 'bg-indigo-600 text-white shadow-md'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Activity className="w-3.5 h-3.5" />
              <span>Analytics</span>
            </button>
          </nav>
        </div>
      </header>

      {/* Main Body */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 py-8 flex flex-col items-center">
        {activeTab === 'rag' ? (
          <div className="w-full max-w-3xl flex flex-col items-center animate-fadeIn">
            {/* Title Section */}
            <div className="text-center mb-8">
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 text-xs font-mono mb-4">
                <Database className="w-3.5 h-3.5" />
                <span>Indexed Dataset: MSMARCO-XI (VAST Chunking)</span>
              </div>
              <h2 className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight mb-3">
                Voice-Enabled Grounded RAG
              </h2>
              <p className="text-slate-400 text-sm max-w-md mx-auto">
                Speak or type a question to trigger vector + BM25 hybrid search, RRF score fusion, guardrails, and sub-200ms latency answers.
              </p>
            </div>

            {/* Central Mic Interactive Button */}
            <MicButton
              state={micState}
              onAudioRecorded={handleAudioRecorded}
              onStateChange={setMicState}
            />

            {/* Fallback Text Input Bar */}
            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleTextSubmit(textInput);
              }}
              className="w-full my-6 flex items-center gap-2 glass-panel p-2 rounded-2xl border border-slate-800 shadow-xl"
            >
              <input
                type="text"
                value={textInput}
                onChange={(e) => setTextInput(e.target.value)}
                placeholder="Ask anything from the MSMARCO-XI knowledge base..."
                className="flex-1 bg-transparent px-4 py-2.5 text-sm text-slate-100 placeholder-slate-500 focus:outline-none"
              />
              <button
                type="submit"
                disabled={!textInput.trim() || loading}
                className="p-3 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 text-white rounded-xl transition-all shadow-md"
                aria-label="Send query"
              >
                <Send className="w-4 h-4" />
              </button>
            </form>

            {/* Sample Query Suggestions */}
            <div className="w-full mb-8">
              <div className="flex items-center gap-2 text-xs text-slate-400 mb-3">
                <HelpCircle className="w-3.5 h-3.5 text-indigo-400" />
                <span>Try sample test queries:</span>
              </div>
              <div className="flex flex-wrap gap-2">
                {sampleQueries.map((q, idx) => (
                  <button
                    key={idx}
                    onClick={() => {
                      setTextInput(q);
                      handleTextSubmit(q);
                    }}
                    className="px-3 py-1.5 bg-slate-900/60 hover:bg-indigo-600/20 text-slate-300 hover:text-indigo-300 border border-slate-800 hover:border-indigo-500/40 rounded-xl text-xs transition-all text-left"
                  >
                    "{q}"
                  </button>
                ))}
              </div>
            </div>

            {/* Grounded Response Card */}
            {response && (
              <AnswerCard
                response={response}
                selectedMode={selectedMode}
                onModeToggle={setSelectedMode}
              />
            )}
          </div>
        ) : (
          <AnalyticsView />
        )}
      </main>

      {/* Footer */}
      <footer className="w-full border-t border-slate-900 py-6 text-center text-xs text-slate-500">
        <p>HH GOA 2026 — Voice-Enabled RAG System • Sub-200ms Grounded Architecture</p>
      </footer>
    </div>
  );
};

export default App;
