import React, { useState, useEffect, useRef } from 'react';
import { Sparkles, Activity } from 'lucide-react';
import { MicButton, type MicState } from './components/MicButton';
import { AnswerCard } from './components/AnswerCard';
import { AnalyticsView } from './components/AnalyticsView';
import { processTextQuery, processTextQueryStream, processVoiceQuery, type RAGPipelineResponse } from './services/api';

export const App: React.FC = () => {
  const [activeSection, setActiveSection] = useState<'hero' | 'voice-rag' | 'analytics'>('hero');
  const [micState, setMicState] = useState<MicState>('Idle');
  const [ragResponse, setRagResponse] = useState<RAGPipelineResponse | null>(null);
  const [selectedMode, setSelectedMode] = useState<'RAG' | 'End-to-End'>('End-to-End');
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [textQueryInput, setTextQueryInput] = useState('');
  const [isSubmittingText, setIsSubmittingText] = useState(false);
  const isManualScrollingRef = useRef(false);

  // Animated Stats Counter State matching actual RAG dataset & performance data
  const [stats, setStats] = useState({
    latency: 0,
    recall: 0,
    documents: 0,
    chunks: 0,
  });

  // Count-up animation matching our MSMARCO-XI & Voice RAG system data
  useEffect(() => {
    const duration = 1500;
    const startTime = performance.now();

    const updateStats = (currentTime: number) => {
      const elapsed = currentTime - startTime;
      const progress = Math.min(elapsed / duration, 1);
      const easeOut = 1 - Math.pow(1 - progress, 3);

      setStats({
        latency: Math.round(200 * easeOut),
        recall: Math.round(94 * easeOut),
        documents: Math.round(1000 * easeOut),
        chunks: Math.round(3450 * easeOut),
      });
    };

    let animationFrameId: number;
    const animate = (currentTime: number) => {
      updateStats(currentTime);
      if (currentTime - startTime < duration) {
        animationFrameId = requestAnimationFrame(animate);
      } else {
        setStats({
          latency: 200,
          recall: 94,
          documents: 1000,
          chunks: 3450,
        });
      }
    };
    animationFrameId = requestAnimationFrame(animate);

    return () => cancelAnimationFrame(animationFrameId);
  }, []);

  const submitTextQuery = async (queryText: string) => {
    const q = queryText.trim();
    if (!q) return;

    setIsSubmittingText(true);
    setMicState('Generating');

    try {
      let accumulatedTokens = '';
      const response = await processTextQueryStream(
        q,
        selectedMode,
        (token) => {
          accumulatedTokens += token;
          setRagResponse((prev) => ({
            request_id: prev?.request_id || 'streaming...',
            query: q,
            answer: accumulatedTokens,
            supported: true,
            confidence: 0.95,
            citations: prev?.citations || [],
            retrieved_chunks: prev?.retrieved_chunks || [],
            metrics: prev?.metrics || {
              request_id: 'live',
              stt_ms: 0,
              query_processing_ms: 0,
              embedding_ms: 0,
              dense_retrieval_ms: 0,
              bm25_ms: 0,
              fusion_ms: 0,
              generation_ms: 0,
              guardrail_ms: 0,
              total_ms: 0,
              mode: selectedMode
            }
          }));
        }
      );
      setRagResponse(response);
      setMicState('Complete');
    } catch (err) {
      console.error('Error submitting text query:', err);
      setMicState('Error');
    } finally {
      setIsSubmittingText(false);
    }
  };

  // Dynamic scroll listener to update activeSection on scroll
  useEffect(() => {
    const handleScroll = () => {
      if (isManualScrollingRef.current) return;

      const voiceRagEl = document.getElementById('voice-rag');
      const analyticsEl = document.getElementById('analytics');

      // 1) Bottom of page fallback for Analytics
      if (window.innerHeight + window.scrollY >= document.documentElement.scrollHeight - 120) {
        setActiveSection('analytics');
        return;
      }

      const viewportMid = window.scrollY + window.innerHeight * 0.4;

      if (analyticsEl && viewportMid >= analyticsEl.offsetTop) {
        setActiveSection('analytics');
      } else if (voiceRagEl && viewportMid >= voiceRagEl.offsetTop) {
        setActiveSection('voice-rag');
      } else {
        setActiveSection('hero');
      }
    };

    window.addEventListener('scroll', handleScroll, { passive: true });
    handleScroll();
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const scrollToSection = (sectionId: 'hero' | 'voice-rag' | 'analytics') => {
    isManualScrollingRef.current = true;
    setActiveSection(sectionId);
    setMobileMenuOpen(false);
    if (sectionId === 'hero') {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    } else {
      const element = document.getElementById(sectionId);
      if (element) {
        element.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
    }
    setTimeout(() => {
      isManualScrollingRef.current = false;
    }, 850);
  };

  const handleAudioRecorded = async (audioBlob: Blob, liveTranscript?: string) => {
    setMicState('Generating');

    try {
      const queryToSubmit = liveTranscript?.trim();

      if (queryToSubmit) {
        // Stream text response token-by-token
        let accumulatedTokens = '';
        const response = await processTextQueryStream(
          queryToSubmit,
          selectedMode,
          (token) => {
            accumulatedTokens += token;
            setRagResponse((prev) => ({
              request_id: prev?.request_id || 'streaming...',
              query: queryToSubmit,
              answer: accumulatedTokens,
              supported: true,
              confidence: 0.95,
              citations: prev?.citations || [],
              retrieved_chunks: prev?.retrieved_chunks || [],
              metrics: prev?.metrics || {
                request_id: 'live',
                stt_ms: 0,
                query_processing_ms: 0,
                embedding_ms: 0,
                dense_retrieval_ms: 0,
                bm25_ms: 0,
                fusion_ms: 0,
                generation_ms: 0,
                guardrail_ms: 0,
                total_ms: 0,
                mode: selectedMode
              }
            }));
          }
        );
        setRagResponse(response);
      } else {
        const response = await processVoiceQuery(audioBlob, 'en-IN');
        setRagResponse(response);
      }

      setMicState('Complete');
    } catch (err) {
      console.error('Error processing audio/text query:', err);
      setMicState('Error');
    }
  };

  return (
    <div className="page-container select-none">
      {/* 1) STICKY HEADER */}
      <div className="header-wrapper">
        <header className="header">
          {/* Logo Button */}
          <button onClick={() => scrollToSection('hero')} className="logo-btn" aria-label="Home">
            <svg viewBox="0 0 100 100" className="w-7 h-7">
              <circle cx="50" cy="50" r="46" fill="#ffffff" />
              <circle cx="50" cy="50" r="24" fill="none" stroke="#000000" strokeWidth="8" />
            </svg>
          </button>

          {/* Desktop Nav Pill (white) */}
          <nav className="nav-pill" aria-label="Main Navigation">
            <button
              onClick={() => scrollToSection('hero')}
              className={`nav-link ${activeSection === 'hero' ? 'active' : ''}`}
            >
              Home
            </button>
            <button
              onClick={() => scrollToSection('voice-rag')}
              className={`nav-link ${activeSection === 'voice-rag' ? 'active' : ''}`}
            >
              Voice RAG
            </button>
            <button
              onClick={() => scrollToSection('analytics')}
              className={`nav-link ${activeSection === 'analytics' ? 'active' : ''}`}
            >
              Analytics
            </button>
          </nav>

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
      </div>

      {/* 2) SECTION 1: HERO LANDING */}
      <section id="hero" className="hero-section">
        <div className="hero-body">
          {/* Headline */}
          <h1 className="headline">
            <span className="headline-line line-1">Meet July</span>
          </h1>

          {/* Subhead */}
          <p className="subhead anim" style={{ '--d': '0.28s' } as React.CSSProperties}>
            July is a sub-200ms voice-enabled grounded RAG platform engineered for real-time speech transcription, hybrid vector retrieval, and automated answer playback.
          </p>

          {/* Glowing CTA Button -> Smooth Scroll to #voice-rag */}
          <div className="cta-wrapper anim-pulse" style={{ '--d': '0.4s' } as React.CSSProperties}>
            <button
              onClick={() => scrollToSection('voice-rag')}
              className="cta-btn cursor-pointer"
            >
              Get Started
            </button>
          </div>
        </div>

        {/* Stats Footer (4 Metrics matching our actual data) */}
        <footer className="stats-footer">
          <div className="stat-card anim" style={{ '--d': '0.5s' } as React.CSSProperties}>
            <div className="stat-icon">&lt;</div>
            <div className="stat-value">{stats.latency}<span className="stat-suffix">ms</span></div>
            <div className="stat-label">Voice RAG SLA</div>
          </div>

          <div className="stat-card anim" style={{ '--d': '0.58s' } as React.CSSProperties}>
            <div className="stat-icon">%</div>
            <div className="stat-value">{stats.recall}<span className="stat-suffix">%</span></div>
            <div className="stat-label">Recall @ Top 5</div>
          </div>

          <div className="stat-card anim" style={{ '--d': '0.66s' } as React.CSSProperties}>
            <div className="stat-icon">*</div>
            <div className="stat-value">{stats.documents.toLocaleString()}<span className="stat-suffix">+</span></div>
            <div className="stat-label">MSMARCO-XI Docs</div>
          </div>

          <div className="stat-card anim" style={{ '--d': '0.74s' } as React.CSSProperties}>
            <div className="stat-icon">#</div>
            <div className="stat-value">{stats.chunks.toLocaleString()}</div>
            <div className="stat-label">VAST Chunks</div>
          </div>
        </footer>
      </section>

      {/* 3) SECTION 2: VOICE RAG PLATFORM */}
      <section id="voice-rag" className="content-section">
        <div className="w-full flex flex-col items-center">
          {/* Section Badge */}
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/30 text-indigo-300 text-xs font-mono mb-4">
            <Sparkles className="w-3.5 h-3.5" />
            <span>Voice-Enabled RAG Platform</span>
          </div>

          <h2 className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight mb-2 text-center">
            Ask Questions via Voice
          </h2>
          <p className="text-slate-400 text-sm max-w-md text-center mb-8">
            Real-time speech recognition, sub-200ms vector + BM25 hybrid search, guardrails, and spoken answer playback.
          </p>

          {/* Central Interactive Mic Button */}
          <MicButton
            state={micState}
            onAudioRecorded={handleAudioRecorded}
            onStateChange={setMicState}
          />

          {/* Quick Text Query Bar & Suggestion Pills */}
          <div className="w-full max-w-xl mt-4 mb-4">
            <form
              onSubmit={(e) => {
                e.preventDefault();
                submitTextQuery(textQueryInput);
              }}
              className="flex items-center gap-2 bg-slate-900/90 border border-slate-700/70 rounded-full px-4 py-2 shadow-inner focus-within:border-indigo-500 transition-all"
            >
              <input
                type="text"
                placeholder="Or type a question (e.g. What is FAISS?)..."
                value={textQueryInput}
                onChange={(e) => setTextQueryInput(e.target.value)}
                disabled={isSubmittingText}
                className="bg-transparent border-none outline-none flex-1 text-sm text-slate-100 placeholder-slate-500 font-normal"
              />
              <button
                type="submit"
                disabled={isSubmittingText || !textQueryInput.trim()}
                className="px-4 py-1.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 text-white rounded-full text-xs font-semibold tracking-wide transition-all shadow-md"
              >
                {isSubmittingText ? 'Asking...' : 'Ask'}
              </button>
            </form>

            {/* Quick Sample Question Pills */}
            <div className="flex items-center justify-center gap-2 mt-3 flex-wrap">
              {[
                "What is FAISS?",
                "What factors does BM25 compute?",
                "Explain Reciprocal Rank Fusion",
                "Who won Hacker House Goa 2026?"
              ].map((q) => (
                <button
                  key={q}
                  onClick={() => {
                    setTextQueryInput(q);
                    submitTextQuery(q);
                  }}
                  className="text-[11px] font-mono px-3 py-1 bg-slate-800/60 hover:bg-slate-700/80 text-slate-300 hover:text-white border border-slate-700/50 rounded-full transition-all cursor-pointer"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>

          {/* Grounded Answer Card */}
          {ragResponse && (
            <AnswerCard
              response={ragResponse}
              selectedMode={selectedMode}
              autoSpeak={false}
              onModeToggle={async (newMode) => {
                setSelectedMode(newMode);
                if (ragResponse.query) {
                  try {
                    const updated = await processTextQuery(ragResponse.query, newMode);
                    setRagResponse(updated);
                  } catch (e) {
                    console.error('Mode toggle failed:', e);
                  }
                }
              }}
            />
          )}
        </div>
      </section>

      {/* 4) SECTION 3: ANALYTICS VIEW */}
      <section id="analytics" className="content-section">
        <div className="w-full max-w-4xl">
          <div className="flex items-center justify-center gap-2 mb-6">
            <div className="p-2 bg-indigo-500/20 text-indigo-400 rounded-xl border border-indigo-500/30">
              <Activity className="w-5 h-5" />
            </div>
            <h2 className="text-2xl font-bold text-white tracking-tight">Latency & System Analytics</h2>
          </div>

          <AnalyticsView />
        </div>
      </section>

      {/* Mobile Menu Sheet */}
      {mobileMenuOpen && (
        <>
          <div
            className="mobile-overlay"
            onClick={() => setMobileMenuOpen(false)}
          ></div>
          <div className="mobile-menu" aria-label="Mobile Navigation Menu">
            <nav className="mobile-nav">
              <button
                onClick={() => scrollToSection('hero')}
                className={`mobile-nav-link ${activeSection === 'hero' ? 'active' : ''}`}
              >
                Home
              </button>
              <button
                onClick={() => scrollToSection('voice-rag')}
                className={`mobile-nav-link ${activeSection === 'voice-rag' ? 'active' : ''}`}
              >
                Voice RAG
              </button>
              <button
                onClick={() => scrollToSection('analytics')}
                className={`mobile-nav-link ${activeSection === 'analytics' ? 'active' : ''}`}
              >
                Analytics
              </button>
            </nav>
          </div>
        </>
      )}
    </div>
  );
};

export default App;
