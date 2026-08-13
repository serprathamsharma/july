import React, { useState, useEffect } from 'react';
import { Send, HelpCircle, ArrowLeft, Sparkles, Activity } from 'lucide-react';
import { MicButton, type MicState } from './components/MicButton';
import { AnswerCard } from './components/AnswerCard';
import { AnalyticsView } from './components/AnalyticsView';
import { type RAGPipelineResponse, processTextQuery, processVoiceQuery } from './services/api';

export const App: React.FC = () => {
  const [activeView, setActiveView] = useState<'landing' | 'rag' | 'analytics'>('landing');
  const [micState, setMicState] = useState<MicState>('Idle');
  const [textInput, setTextInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState<RAGPipelineResponse | null>(null);
  const [selectedMode, setSelectedMode] = useState<'RAG' | 'End-to-End'>('RAG');
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  // Animated Stats Counter State
  const [stats, setStats] = useState({
    inference: 0,
    uptime: 0,
    runtime: 0,
    context: 0,
  });

  // Count-up animation for Stats Footer
  useEffect(() => {
    const duration = 1500;
    const startTime = performance.now();

    const updateStats = (currentTime: number) => {
      const elapsed = currentTime - startTime;
      const progress = Math.min(elapsed / duration, 1);
      const easeOut = 1 - Math.pow(1 - progress, 3);

      setStats({
        inference: Math.round(120 * easeOut),
        uptime: parseFloat((99.99 * easeOut).toFixed(2)),
        runtime: Math.round(24 * easeOut),
        context: parseFloat((2.4 * easeOut).toFixed(1)),
      });

      if (progress < 1) {
        requestAnimationFrame(updateStats);
      } else {
        setStats({
          inference: 120,
          uptime: 99.99,
          runtime: 24,
          context: 2.4,
        });
      }
    };

    const timer = setTimeout(() => {
      requestAnimationFrame(updateStats);
    }, 400);

    return () => clearTimeout(timer);
  }, []);

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

  const handleAudioRecorded = async (audioBlob: Blob, liveTranscript?: string) => {
    setLoading(true);
    setMicState('Generating');

    try {
      const queryToSubmit = liveTranscript?.trim() || textInput.trim();
      let res: RAGPipelineResponse;

      if (queryToSubmit) {
        res = await processTextQuery(queryToSubmit, 'End-to-End');
        res.transcription = queryToSubmit;
      } else {
        res = await processVoiceQuery(audioBlob, 'en-IN');
      }

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
    <div className="page-container select-none">
      {/* 1) HEADER (Desktop & Mobile) */}
      <header className="header">
        {/* Logo Button */}
        <button onClick={() => setActiveView('landing')} className="logo-btn" aria-label="Home">
          <img src="/assets/logo.webp" alt="" width="52" height="52" className="logo-img" />
        </button>

        {/* Desktop Nav Pill (white) */}
        <nav className="nav-pill" aria-label="Main Navigation">
          <button
            onClick={() => setActiveView('landing')}
            className={`nav-link ${activeView === 'landing' ? 'active' : ''}`}
          >
            Home
          </button>
          <button
            onClick={() => setActiveView('rag')}
            className={`nav-link ${activeView === 'rag' ? 'active' : ''}`}
          >
            Voice RAG
          </button>
          <button
            onClick={() => setActiveView('analytics')}
            className={`nav-link ${activeView === 'analytics' ? 'active' : ''}`}
          >
            Analytics
          </button>
          <a href="#contact" className="nav-link">Contact</a>
        </nav>

        {/* Desktop Sign In Pill */}
        <a href="#signin" className="signin-pill">Sign in</a>

        {/* Mobile Hamburger Button */}
        <button
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          className={`burger-btn ${mobileMenuOpen ? 'open' : ''}`}
          aria-label="Toggle Navigation Menu"
          aria-expanded={mobileMenuOpen}
        >
          <span className="burger-bar"></span>
          <span className="burger-bar"></span>
          <span className="burger-bar"></span>
        </button>
      </header>

      {/* 2) HERO / MAIN VIEW AREA */}
      <main className="hero">
        {activeView === 'landing' && (
          <div className="w-full flex flex-col items-center">

            {/* Headline */}
            <h1 className="headline">
              <span className="headline-line line-1">Intelligence</span>
              <span className="headline-line line-2">Designed To Evolve</span>
            </h1>

            {/* Subhead */}
            <p className="subhead anim" style={{ '--d': '0.28s' } as React.CSSProperties}>
              Build applications that reason, adapt and collaborate using a modular AI platform designed for production.
            </p>

            {/* Glowing CTA Button -> Opens Voice RAG */}
            <div className="cta-wrapper anim-pulse" style={{ '--d': '0.4s' } as React.CSSProperties}>
              <button
                onClick={() => setActiveView('rag')}
                className="cta-btn cursor-pointer"
              >
                Get Started
              </button>
            </div>
          </div>
        )}

        {activeView === 'rag' && (
          <div className="w-full max-w-2xl flex flex-col items-center animate-fadeIn py-2">
            {/* Back Button & View Header */}
            <div className="w-full flex items-center justify-between mb-4">
              <button
                onClick={() => setActiveView('landing')}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-slate-900/80 hover:bg-slate-800 text-xs text-slate-300 border border-slate-700/60 transition-all cursor-pointer"
              >
                <ArrowLeft className="w-3.5 h-3.5" />
                <span>Back to Overview</span>
              </button>

              <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/30 text-indigo-300 text-xs font-mono">
                <Sparkles className="w-3.5 h-3.5" />
                <span>Voice RAG Active</span>
              </div>
            </div>

            {/* Real-time Voice Recording Component */}
            <MicButton
              state={micState}
              onAudioRecorded={handleAudioRecorded}
              onStateChange={setMicState}
              onLiveTranscriptChange={(liveText) => setTextInput(liveText)}
            />

            {/* Text Query Input Bar */}
            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleTextSubmit(textInput);
              }}
              className="w-full my-3 flex items-center gap-2 glass-panel p-2 rounded-2xl border border-slate-700/60 shadow-xl"
            >
              <input
                type="text"
                value={textInput}
                onChange={(e) => setTextInput(e.target.value)}
                placeholder="Ask anything or speak in real time..."
                className="flex-1 bg-transparent px-4 py-2 text-sm text-slate-100 placeholder-slate-400 focus:outline-none"
              />
              <button
                type="submit"
                disabled={!textInput.trim() || loading}
                className="p-3 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 text-white rounded-xl transition-all shadow-md cursor-pointer"
                aria-label="Send query"
              >
                <Send className="w-4 h-4" />
              </button>
            </form>

            {/* Sample Query Suggestions */}
            <div className="w-full mb-3">
              <div className="flex items-center justify-center gap-1.5 text-xs text-slate-400 mb-2">
                <HelpCircle className="w-3.5 h-3.5 text-indigo-400" />
                <span>Try sample queries:</span>
              </div>
              <div className="flex flex-wrap justify-center gap-1.5">
                {sampleQueries.map((q, idx) => (
                  <button
                    key={idx}
                    onClick={() => {
                      setTextInput(q);
                      handleTextSubmit(q);
                    }}
                    className="px-2.5 py-1 bg-slate-900/80 hover:bg-indigo-600/30 text-slate-300 hover:text-indigo-200 border border-slate-800 hover:border-indigo-500/40 rounded-xl text-xs transition-all text-left cursor-pointer"
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
        )}

        {activeView === 'analytics' && (
          <div className="w-full max-w-4xl py-2 overflow-y-auto">
            <div className="w-full flex items-center justify-between mb-4">
              <button
                onClick={() => setActiveView('landing')}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-slate-900/80 hover:bg-slate-800 text-xs text-slate-300 border border-slate-700/60 transition-all cursor-pointer"
              >
                <ArrowLeft className="w-3.5 h-3.5" />
                <span>Back to Overview</span>
              </button>

              <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/30 text-indigo-300 text-xs font-mono">
                <Activity className="w-3.5 h-3.5" />
                <span>System Analytics</span>
              </div>
            </div>

            <AnalyticsView />
          </div>
        )}
      </main>

      {/* 3) STATS FOOTER (4 Metrics) */}
      <footer className="stats-footer">
        <div className="stat-card anim" style={{ '--d': '0.5s' } as React.CSSProperties}>
          <div className="stat-icon">&lt;</div>
          <div className="stat-value">{stats.inference}<span className="stat-suffix">ms</span></div>
          <div className="stat-label">Inference Time</div>
        </div>

        <div className="stat-card anim" style={{ '--d': '0.58s' } as React.CSSProperties}>
          <div className="stat-icon">%</div>
          <div className="stat-value">{stats.uptime}<span className="stat-suffix">%</span></div>
          <div className="stat-label">Platform Uptime</div>
        </div>

        <div className="stat-card anim" style={{ '--d': '0.66s' } as React.CSSProperties}>
          <div className="stat-icon">*</div>
          <div className="stat-value">{stats.runtime}<span className="stat-suffix">/7</span></div>
          <div className="stat-label">Autonomous Runtime</div>
        </div>

        <div className="stat-card anim" style={{ '--d': '0.74s' } as React.CSSProperties}>
          <div className="stat-icon">#</div>
          <div className="stat-value">{stats.context}<span className="stat-suffix">M</span></div>
          <div className="stat-label">Context Windows</div>
        </div>
      </footer>

      {/* Mobile Overlay & Menu Sheet */}
      {mobileMenuOpen && (
        <>
          <div
            className="mobile-overlay"
            onClick={() => setMobileMenuOpen(false)}
          ></div>
          <div className="mobile-menu" aria-label="Mobile Navigation Menu">
            <nav className="mobile-nav">
              <button
                onClick={() => {
                  setActiveView('landing');
                  setMobileMenuOpen(false);
                }}
                className={`mobile-nav-link ${activeView === 'landing' ? 'active' : ''}`}
              >
                Home
              </button>
              <button
                onClick={() => {
                  setActiveView('rag');
                  setMobileMenuOpen(false);
                }}
                className={`mobile-nav-link ${activeView === 'rag' ? 'active' : ''}`}
              >
                Voice RAG
              </button>
              <button
                onClick={() => {
                  setActiveView('analytics');
                  setMobileMenuOpen(false);
                }}
                className={`mobile-nav-link ${activeView === 'analytics' ? 'active' : ''}`}
              >
                Analytics
              </button>
              <a href="#contact" onClick={() => setMobileMenuOpen(false)} className="mobile-nav-link">Contact</a>
            </nav>
            <a href="#signin" onClick={() => setMobileMenuOpen(false)} className="mobile-signin-btn">Sign in</a>
          </div>
        </>
      )}
    </div>
  );
};

export default App;
