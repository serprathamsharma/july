import React, { useState, useEffect, useRef } from 'react';
import { Sparkles, Activity, History } from 'lucide-react';
import { MicButton, type MicState } from './components/MicButton';
import { AnswerCard } from './components/AnswerCard';
import { AnalyticsView } from './components/AnalyticsView';
import { KnowledgeGraphView } from './components/KnowledgeGraphView';
import { QueryHistoryDrawer, type HistoryItem } from './components/QueryHistoryDrawer';
import { processTextQuery, processTextQueryStream, processVoiceQuery, type RAGPipelineResponse } from './services/api';

export const App: React.FC = () => {
  const [activeSection, setActiveSection] = useState<'hero' | 'voice-rag' | 'knowledge-map' | 'analytics'>('hero');
  const [micState, setMicState] = useState<MicState>('Idle');
  const [ragResponse, setRagResponse] = useState<RAGPipelineResponse | null>(null);
  const [selectedMode, setSelectedMode] = useState<'RAG' | 'End-to-End'>('End-to-End');
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [historyDrawerOpen, setHistoryDrawerOpen] = useState(false);
  const [queryHistory, setQueryHistory] = useState<HistoryItem[]>([]);
  const isManualScrollingRef = useRef(false);
  const spacebarDownRef = useRef(false);

  // Push-to-Talk keyboard shortcut (Spacebar)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Don't trigger if user is typing in an input or textarea
      const target = e.target as HTMLElement;
      if (target && (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable)) {
        return;
      }

      if (e.code === 'Space' && !e.repeat && !spacebarDownRef.current) {
        if (micState === 'Idle' || micState === 'Complete') {
          e.preventDefault();
          spacebarDownRef.current = true;
          // Scroll to voice rag section if not visible
          const voiceRagEl = document.getElementById('voice-rag');
          if (voiceRagEl && activeSection !== 'voice-rag') {
            voiceRagEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
          }
        }
      }
    };

    const handleKeyUp = (e: KeyboardEvent) => {
      if (e.code === 'Space' && spacebarDownRef.current) {
        e.preventDefault();
        spacebarDownRef.current = false;
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    window.addEventListener('keyup', handleKeyUp);
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      window.removeEventListener('keyup', handleKeyUp);
    };
  }, [micState, activeSection]);

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

  // Dynamic scroll listener to update activeSection on scroll
  useEffect(() => {
    const handleScroll = () => {
      if (isManualScrollingRef.current) return;

      const voiceRagEl = document.getElementById('voice-rag');
      const knowledgeMapEl = document.getElementById('knowledge-map');
      const analyticsEl = document.getElementById('analytics');

      // 1) Bottom of page fallback for Analytics
      if (window.innerHeight + window.scrollY >= document.documentElement.scrollHeight - 120) {
        setActiveSection('analytics');
        return;
      }

      const viewportMid = window.scrollY + window.innerHeight * 0.4;

      if (analyticsEl && viewportMid >= analyticsEl.offsetTop) {
        setActiveSection('analytics');
      } else if (knowledgeMapEl && viewportMid >= knowledgeMapEl.offsetTop) {
        setActiveSection('knowledge-map');
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

  const scrollToSection = (sectionId: 'hero' | 'voice-rag' | 'knowledge-map' | 'analytics') => {
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

  const handleFollowUpQuery = async (queryText: string) => {
    scrollToSection('voice-rag');
    await handleAudioRecorded(new Blob([]), queryText);
  };

  const handleAudioRecorded = async (audioBlob: Blob, liveTranscript?: string) => {
    setMicState('Generating');

    try {
      const queryToSubmit = liveTranscript?.trim();
      let finalRes: RAGPipelineResponse;

      if (queryToSubmit) {
        // Stream text response token-by-token
        let accumulatedTokens = '';
        finalRes = await processTextQueryStream(
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
      } else {
        finalRes = await processVoiceQuery(audioBlob, 'en-IN');
      }

      setRagResponse(finalRes);
      
      // Append to session query history
      const now = new Date();
      const timeStr = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
      setQueryHistory((prev) => [
        {
          id: finalRes.request_id || `hist_${Date.now()}`,
          timestamp: timeStr,
          response: finalRes
        },
        ...prev.slice(0, 9)
      ]);

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
              onClick={() => scrollToSection('knowledge-map')}
              className={`nav-link ${activeSection === 'knowledge-map' ? 'active' : ''}`}
            >
              Knowledge Map
            </button>
            <button
              onClick={() => scrollToSection('analytics')}
              className={`nav-link ${activeSection === 'analytics' ? 'active' : ''}`}
            >
              Analytics
            </button>
            <button
              onClick={() => setHistoryDrawerOpen(true)}
              className="nav-link flex items-center gap-1.5 hover:text-indigo-400"
              title="View past questions in this session"
            >
              <History className="w-3.5 h-3.5" />
              <span>History</span>
              {queryHistory.length > 0 && (
                <span className="w-4 h-4 text-[10px] bg-indigo-600 text-white rounded-full flex items-center justify-center font-mono">
                  {queryHistory.length}
                </span>
              )}
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

      {/* Query History Slide-Over Drawer */}
      <QueryHistoryDrawer
        isOpen={historyDrawerOpen}
        onClose={() => setHistoryDrawerOpen(false)}
        history={queryHistory}
        onSelectQuery={(item) => {
          setRagResponse(item.response);
          scrollToSection('voice-rag');
        }}
        onClearHistory={() => setQueryHistory([])}
      />

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

          {/* Grounded Answer Card */}
          {ragResponse && (
            <AnswerCard
              response={ragResponse}
              selectedMode={selectedMode}
              autoSpeak={false}
              onAskFollowUp={handleFollowUpQuery}
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

      {/* 4) SECTION 3: KNOWLEDGE GRAPH MAP (13.1) */}
      <section id="knowledge-map" className="content-section">
        <KnowledgeGraphView onSelectEntityQuery={handleFollowUpQuery} />
      </section>

      {/* 5) SECTION 4: ANALYTICS VIEW */}
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
                onClick={() => scrollToSection('knowledge-map')}
                className={`mobile-nav-link ${activeSection === 'knowledge-map' ? 'active' : ''}`}
              >
                Knowledge Map
              </button>
              <button
                onClick={() => scrollToSection('analytics')}
                className={`mobile-nav-link ${activeSection === 'analytics' ? 'active' : ''}`}
              >
                Analytics
              </button>
              <button
                onClick={() => {
                  setMobileMenuOpen(false);
                  setHistoryDrawerOpen(true);
                }}
                className="mobile-nav-link flex items-center justify-between"
              >
                <span>Query History</span>
                {queryHistory.length > 0 && (
                  <span className="text-xs bg-indigo-600 px-2 py-0.5 rounded-full text-white">
                    {queryHistory.length}
                  </span>
                )}
              </button>
            </nav>
          </div>
        </>
      )}
    </div>
  );
};

export default App;
