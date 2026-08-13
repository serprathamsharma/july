import React, { useState, useEffect } from 'react';
import { Sparkles, Activity } from 'lucide-react';
import { MicButton, type MicState } from './components/MicButton';
import { AnalyticsView } from './components/AnalyticsView';
import { processTextQuery, processVoiceQuery } from './services/api';

export const App: React.FC = () => {
  const [activeSection, setActiveSection] = useState<'hero' | 'voice-rag' | 'analytics'>('hero');
  const [micState, setMicState] = useState<MicState>('Idle');
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

  // IntersectionObserver to dynamically update activeSection on scroll
  useEffect(() => {
    const sectionIds: Array<'hero' | 'voice-rag' | 'analytics'> = ['hero', 'voice-rag', 'analytics'];
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            setActiveSection(entry.target.id as 'hero' | 'voice-rag' | 'analytics');
          }
        });
      },
      {
        root: null,
        rootMargin: '-30% 0px -40% 0px',
        threshold: 0.2,
      }
    );

    sectionIds.forEach((id) => {
      const el = document.getElementById(id);
      if (el) observer.observe(el);
    });

    return () => observer.disconnect();
  }, []);

  const scrollToSection = (sectionId: 'hero' | 'voice-rag' | 'analytics') => {
    setActiveSection(sectionId);
    setMobileMenuOpen(false);
    const element = document.getElementById(sectionId);
    if (element) {
      element.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  };

  const handleAudioRecorded = async (audioBlob: Blob, liveTranscript?: string) => {
    setMicState('Generating');

    try {
      const queryToSubmit = liveTranscript?.trim();

      if (queryToSubmit) {
        await processTextQuery(queryToSubmit, 'End-to-End');
      } else {
        await processVoiceQuery(audioBlob, 'en-IN');
      }

      setMicState('Complete');
    } catch (err) {
      console.error(err);
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

        {/* Stats Footer (4 Metrics) */}
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

          {/* Grounded Answer Card Removed */}
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
