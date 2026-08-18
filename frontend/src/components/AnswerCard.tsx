import React, { useState, useEffect, useRef } from 'react';
import { Sparkles, BookOpen, ShieldCheck, ExternalLink, Volume2, VolumeX, Loader2, ThumbsUp, ThumbsDown, Check } from 'lucide-react';
import { type RAGPipelineResponse, type RetrievedChunkPayload, synthesizeSpeech, submitFeedback } from '../services/api';
import { LatencyBadge } from './LatencyBadge';
import { SourceExplorer } from './SourceExplorer';

interface AnswerCardProps {
  response: RAGPipelineResponse;
  selectedMode: 'RAG' | 'End-to-End';
  onModeToggle: (mode: 'RAG' | 'End-to-End') => void;
  onAskFollowUp?: (question: string) => void;
  autoSpeak?: boolean;
}

export const AnswerCard: React.FC<AnswerCardProps> = ({ response, selectedMode, onModeToggle, onAskFollowUp, autoSpeak = false }) => {
  const [selectedChunk, setSelectedChunk] = useState<RetrievedChunkPayload | null>(null);
  const [isSpeaking, setIsSpeaking] = useState<boolean>(false);
  const [isSynthesizing, setIsSynthesizing] = useState<boolean>(false);
  const [userRating, setUserRating] = useState<'up' | 'down' | null>(null);
  const [feedbackSent, setFeedbackSent] = useState<boolean>(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const isAbstention = !response.supported || response.answer.includes("couldn't find enough");

  const stopSpeaking = () => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
    }
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel();
    }
    setIsSpeaking(false);
    setIsSynthesizing(false);
  };

  const speakAnswer = async () => {
    if (isSpeaking || isSynthesizing) {
      stopSpeaking();
      return;
    }

    const textToSpeak = response.answer.replace(/\[.*?\]/g, '').trim();
    if (!textToSpeak) return;

    setIsSynthesizing(true);

    try {
      const ttsRes = await synthesizeSpeech(textToSpeak, 'en-IN');
      if (ttsRes && ttsRes.audio_base64) {
        const audioSrc = `data:audio/wav;base64,${ttsRes.audio_base64}`;
        if (!audioRef.current) {
          audioRef.current = new Audio();
        }
        audioRef.current.src = audioSrc;
        audioRef.current.onplay = () => {
          setIsSynthesizing(false);
          setIsSpeaking(true);
        };
        audioRef.current.onended = () => {
          setIsSpeaking(false);
        };
        audioRef.current.onerror = () => {
          fallbackSpeechSynthesis(textToSpeak);
        };
        await audioRef.current.play();
        return;
      }
    } catch (e) {
      console.warn("Sarvam TTS synthesis fallback to browser synthesis:", e);
    }

    fallbackSpeechSynthesis(textToSpeak);
  };

  const fallbackSpeechSynthesis = (textToSpeak: string) => {
    setIsSynthesizing(false);
    if (typeof window === 'undefined' || !('speechSynthesis' in window)) {
      console.warn("Web SpeechSynthesis API not supported in this browser.");
      return;
    }

    try {
      window.speechSynthesis.cancel();
      
      const utterance = new SpeechSynthesisUtterance(textToSpeak);
      utterance.rate = 1.0;
      utterance.pitch = 1.0;
      utterance.lang = 'en-IN';

      const voices = window.speechSynthesis.getVoices();
      if (voices && voices.length > 0) {
        const indicVoice = voices.find(v => v.lang.includes('IN') || v.name.includes('India') || v.name.includes('Indian'));
        if (indicVoice) {
          utterance.voice = indicVoice;
        }
      }

      utterance.onstart = () => setIsSpeaking(true);
      utterance.onend = () => setIsSpeaking(false);
      utterance.onerror = (e) => {
        console.warn("Speech synthesis error:", e);
        setIsSpeaking(false);
      };

      window.speechSynthesis.speak(utterance);
      if (window.speechSynthesis.paused) {
        window.speechSynthesis.resume();
      }
    } catch (err) {
      console.error("Speech synthesis invocation failed:", err);
      setIsSpeaking(false);
    }
  };

  const handleFeedback = async (rating: 'up' | 'down') => {
    if (userRating === rating) return;
    setUserRating(rating);
    setFeedbackSent(true);
    try {
      await submitFeedback(response.request_id, rating);
    } catch (err) {
      console.warn("Feedback submission error:", err);
    }
  };

  useEffect(() => {
    setUserRating(null);
    setFeedbackSent(false);
  }, [response.request_id]);

  useEffect(() => {
    return () => {
      stopSpeaking();
    };
  }, []);

  useEffect(() => {
    if (autoSpeak && response.answer) {
      const timer = setTimeout(() => {
        speakAnswer();
      }, 300);
      return () => clearTimeout(timer);
    }
  }, [response.request_id]);

  return (
    <div className="w-full max-w-3xl glass-panel rounded-2xl p-6 sm:p-8 shadow-2xl border border-slate-800 animate-fadeIn my-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 mb-6 border-b border-slate-800/80">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-indigo-500/20 text-indigo-400 rounded-xl border border-indigo-500/30">
            <Sparkles className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-sm font-semibold tracking-wide text-slate-300 uppercase flex items-center gap-2">
              <span>Grounded Response</span>
              {isAbstention ? (
                <span className="text-[10px] font-mono bg-amber-500/20 text-amber-300 border border-amber-500/40 px-2 py-0.5 rounded-full">
                  ABSTENTION
                </span>
              ) : (
                <span className="text-[10px] font-mono bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 px-2 py-0.5 rounded-full">
                  GROUNDED
                </span>
              )}
            </h2>
            <p className="text-xs text-slate-400 font-mono">
              Query: "{response.query}"
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3 self-end sm:self-center">
          {!isAbstention && (
            <button
              onClick={speakAnswer}
              disabled={isSynthesizing}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl border text-xs font-semibold transition-all cursor-pointer ${
                isSpeaking
                  ? 'bg-rose-500/20 text-rose-300 border-rose-500/40 animate-pulse'
                  : isSynthesizing
                  ? 'bg-slate-800 text-slate-400 border-slate-700 cursor-wait'
                  : 'bg-white hover:bg-slate-100 text-black border-white/80 shadow-md shadow-white/5'
              }`}
              title={isSpeaking ? 'Stop speaking' : 'Listen to answer'}
            >
              {isSynthesizing ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin text-slate-400" />
              ) : isSpeaking ? (
                <VolumeX className="w-3.5 h-3.5" />
              ) : (
                <Volume2 className="w-3.5 h-3.5 fill-black text-black" />
              )}
              <span>{isSynthesizing ? 'Synthesizing...' : isSpeaking ? 'Stop Audio' : 'Speak Answer'}</span>
            </button>
          )}

          <div className="flex items-center bg-slate-900/80 p-1 rounded-xl border border-slate-800 text-xs">
            <button
              onClick={() => onModeToggle('RAG')}
              className={`px-3 py-1 rounded-lg font-medium transition-all ${
                selectedMode === 'RAG'
                  ? 'bg-indigo-600 text-white shadow'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              RAG
            </button>
            <button
              onClick={() => onModeToggle('End-to-End')}
              className={`px-3 py-1 rounded-lg font-medium transition-all ${
                selectedMode === 'End-to-End'
                  ? 'bg-indigo-600 text-white shadow'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              End-to-End
            </button>
          </div>
        </div>
      </div>

      {/* Answer Text */}
      <div className="mb-6">
        <p className="text-slate-100 text-base sm:text-lg leading-relaxed font-normal">
          {response.answer}
        </p>
      </div>

      {/* Suggested Follow-Ups */}
      {response.follow_up_questions && response.follow_up_questions.length > 0 && !isAbstention && (
        <div className="mb-6 pt-4 border-t border-slate-800/60">
          <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2.5">
            <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
            <span>Suggested Follow-Ups</span>
          </div>
          <div className="flex flex-wrap gap-2">
            {response.follow_up_questions.map((question, qIdx) => (
              <button
                key={qIdx}
                onClick={() => onAskFollowUp && onAskFollowUp(question)}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-indigo-950/40 hover:bg-indigo-900/60 text-indigo-200 hover:text-white border border-indigo-500/30 hover:border-indigo-400/60 rounded-xl text-xs transition-all duration-200 text-left cursor-pointer group shadow-sm"
              >
                <span className="text-indigo-400 font-mono text-[10px]">↳</span>
                <span>{question}</span>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Latency Waterfall Breakdown */}
      <div className="mb-6">
        <LatencyBadge metrics={response.metrics} selectedMode={selectedMode} onModeToggle={onModeToggle} />
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
                className="inline-flex items-center gap-1.5 px-3 py-1 bg-slate-800/80 hover:bg-indigo-600/30 text-indigo-300 border border-slate-700/80 hover:border-indigo-500/50 rounded-lg text-xs font-mono transition-all cursor-pointer"
                title="Click to view full chunk with citation sentence highlight"
              >
                <span>[{idx + 1}] {chunk.chunk_id.split('_').slice(-2).join('_')}</span>
                <ExternalLink className="w-3 h-3 text-indigo-400" />
              </button>
            ))
          )}
        </div>

        {/* Confidence Pill & Thumbs Feedback */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1 px-2.5 py-1 bg-slate-900/80 rounded-md border border-slate-800 text-[11px] font-mono text-slate-400">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
            Confidence: <span className="text-emerald-400 font-semibold">{Math.round(response.confidence * 100)}%</span>
          </div>

          {/* Feedback Buttons */}
          <div className="flex items-center gap-1 bg-slate-900/80 p-0.5 rounded-md border border-slate-800 text-xs">
            <button
              onClick={() => handleFeedback('up')}
              className={`p-1.5 rounded transition-all flex items-center gap-1 cursor-pointer ${
                userRating === 'up'
                  ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
              }`}
              title="Good answer"
            >
              {feedbackSent && userRating === 'up' ? <Check className="w-3 h-3 text-emerald-400" /> : <ThumbsUp className="w-3 h-3" />}
            </button>
            <button
              onClick={() => handleFeedback('down')}
              className={`p-1.5 rounded transition-all flex items-center gap-1 cursor-pointer ${
                userRating === 'down'
                  ? 'bg-rose-500/20 text-rose-300 border border-rose-500/40'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
              }`}
              title="Poor answer"
            >
              {feedbackSent && userRating === 'down' ? <Check className="w-3 h-3 text-rose-400" /> : <ThumbsDown className="w-3 h-3" />}
            </button>
          </div>
        </div>
      </div>

      <SourceExplorer
        chunk={selectedChunk}
        groundingAnswer={response.answer}
        query={response.query}
        onClose={() => setSelectedChunk(null)}
      />
    </div>
  );
};
