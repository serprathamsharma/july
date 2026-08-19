import React, { useState, useRef, useEffect, useCallback } from 'react';
import { Mic, Square, Loader2, Volume2, AlertCircle, Sparkles, Zap, Radio, RefreshCw } from 'lucide-react';
import { WaveformVisualizer } from './WaveformVisualizer';
import { normalizeVoiceQuery } from '../utils/voiceNormalizer';

export type MicState = 'Idle' | 'Listening' | 'Processing' | 'Generating' | 'Complete' | 'Error';

interface MicButtonProps {
  state: MicState;
  onAudioRecorded: (blob: Blob, liveTranscript?: string) => void;
  onStateChange: (newState: MicState) => void;
  onLiveTranscriptChange?: (text: string) => void;
}

export const MicButton: React.FC<MicButtonProps> = ({
  state,
  onAudioRecorded,
  onStateChange,
  onLiveTranscriptChange
}) => {
  const [activeStream, setActiveStream] = useState<MediaStream | null>(null);
  const [liveTranscript, setLiveTranscript] = useState<string>('');
  const [vadEnabled, setVadEnabled] = useState<boolean>(true);
  const [isVoiceActive, setIsVoiceActive] = useState<boolean>(false);
  const [silenceCountdown, setSilenceCountdown] = useState<number | null>(null);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const liveTranscriptRef = useRef<string>('');
  const recognitionRef = useRef<any>(null);
  const audioChunks = useRef<Blob[]>([]);
  const vadIntervalRef = useRef<number | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const hasSpokenRef = useRef<boolean>(false);
  const lastSpeechTimeRef = useRef<number>(Date.now());
  const recordingStartTimeRef = useRef<number>(Date.now());
  const noiseFloorRef = useRef<number>(16);

  const stopVadMonitoring = useCallback(() => {
    if (vadIntervalRef.current) {
      window.clearInterval(vadIntervalRef.current);
      vadIntervalRef.current = null;
    }
    setIsVoiceActive(false);
    setSilenceCountdown(null);
  }, []);

  const cleanupAudio = useCallback(() => {
    stopVadMonitoring();

    if (recognitionRef.current) {
      try {
        recognitionRef.current.stop();
      } catch (e) {
        // ignore
      }
      recognitionRef.current = null;
    }

    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => {
        try {
          track.stop();
        } catch (e) {
          // ignore
        }
      });
      streamRef.current = null;
      setActiveStream(null);
    }

    if (audioContextRef.current && audioContextRef.current.state !== 'closed') {
      try {
        audioContextRef.current.close();
      } catch (e) {
        // ignore
      }
      audioContextRef.current = null;
    }
  }, [stopVadMonitoring]);

  useEffect(() => {
    return () => {
      cleanupAudio();
    };
  }, [cleanupAudio]);

  const stopRecording = useCallback(() => {
    stopVadMonitoring();
    onStateChange('Processing');

    if (recognitionRef.current) {
      try {
        recognitionRef.current.stop();
      } catch (e) {
        console.warn(e);
      }
    }

    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      try {
        mediaRecorderRef.current.stop();
      } catch (e) {
        console.warn('Error stopping media recorder:', e);
      }
    }
  }, [stopVadMonitoring, onStateChange]);

  const startVadMonitoring = useCallback((stream: MediaStream) => {
    try {
      const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
      if (!AudioCtx) return;

      const audioCtx = new AudioCtx();
      audioContextRef.current = audioCtx;

      const analyser = audioCtx.createAnalyser();
      analyser.fftSize = 256;
      analyser.smoothingTimeConstant = 0.4;
      analyserRef.current = analyser;

      const source = audioCtx.createMediaStreamSource(stream);
      source.connect(analyser);

      const bufferLength = analyser.frequencyBinCount;
      const dataArray = new Uint8Array(bufferLength);

      hasSpokenRef.current = false;
      lastSpeechTimeRef.current = Date.now();
      recordingStartTimeRef.current = Date.now();
      noiseFloorRef.current = 16;

      const SILENCE_TIMEOUT_MS = 1400; // 1.4s of silence after speech -> auto answer
      const INITIAL_MAX_SILENCE_MS = 8000; // 8s initial timeout

      // Human speech frequency bandpass: 300Hz to 3400Hz
      const sampleRate = audioCtx.sampleRate || 48000;
      const binHz = (sampleRate / 2) / bufferLength;
      const startBin = Math.max(1, Math.floor(300 / binHz));
      const endBin = Math.min(bufferLength - 1, Math.ceil(3400 / binHz));
      const numVocalBins = endBin - startBin + 1;

      vadIntervalRef.current = window.setInterval(() => {
        if (!analyserRef.current) return;

        analyserRef.current.getByteFrequencyData(dataArray);

        let vocalSum = 0;
        for (let i = startBin; i <= endBin; i++) {
          vocalSum += dataArray[i];
        }
        const avgVocalEnergy = vocalSum / numVocalBins;
        const now = Date.now();

        // Dynamically adjust noise floor baseline
        if (avgVocalEnergy < noiseFloorRef.current + 8) {
          noiseFloorRef.current = 0.92 * noiseFloorRef.current + 0.08 * avgVocalEnergy;
        }

        const dynamicSpeechThreshold = Math.max(24, noiseFloorRef.current + 12);
        const isCurrentlySpeaking = avgVocalEnergy > dynamicSpeechThreshold;

        if (isCurrentlySpeaking) {
          hasSpokenRef.current = true;
          lastSpeechTimeRef.current = now;
          setIsVoiceActive(true);
          setSilenceCountdown(null);
        } else {
          setIsVoiceActive(false);

          if (!vadEnabled) return;

          if (hasSpokenRef.current) {
            const silentDuration = now - lastSpeechTimeRef.current;
            const remainingMs = SILENCE_TIMEOUT_MS - silentDuration;

            if (remainingMs > 0 && remainingMs <= 1100) {
              setSilenceCountdown(parseFloat((remainingMs / 1000).toFixed(1)));
            } else if (silentDuration >= SILENCE_TIMEOUT_MS) {
              stopVadMonitoring();
              stopRecording();
            }
          } else {
            if (now - recordingStartTimeRef.current >= INITIAL_MAX_SILENCE_MS) {
              stopVadMonitoring();
              stopRecording();
            }
          }
        }
      }, 100);
    } catch (err) {
      console.warn('VAD monitoring initialization warning:', err);
    }
  }, [vadEnabled, stopRecording, stopVadMonitoring]);

  const startRecording = async () => {
    cleanupAudio();

    try {
      setLiveTranscript('');
      liveTranscriptRef.current = '';
      if (onLiveTranscriptChange) onLiveTranscriptChange('');

      const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
      if (SpeechRecognition) {
        try {
          const recognition = new SpeechRecognition();
          recognition.continuous = true;
          recognition.interimResults = true;
          recognition.lang = 'en-IN';

          recognition.onresult = (event: any) => {
            let rawTranscript = '';
            for (let i = 0; i < event.results.length; i++) {
              rawTranscript += event.results[i][0].transcript;
            }
            const normalized = normalizeVoiceQuery(rawTranscript);
            setLiveTranscript(normalized);
            liveTranscriptRef.current = normalized;

            if (normalized.trim().length > 0) {
              hasSpokenRef.current = true;
              lastSpeechTimeRef.current = Date.now();
            }

            if (onLiveTranscriptChange) {
              onLiveTranscriptChange(normalized);
            }
          };

          recognition.onerror = (err: any) => {
            console.warn('Speech recognition notice:', err.error || err);
          };

          recognition.start();
          recognitionRef.current = recognition;
        } catch (speechErr) {
          console.warn('Web Speech API fallback:', speechErr);
        }
      }

      let stream: MediaStream;
      try {
        stream = await navigator.mediaDevices.getUserMedia({
          audio: {
            echoCancellation: true,
            noiseSuppression: true,
            autoGainControl: true,
            channelCount: 1
          }
        });
      } catch (constraintErr) {
        stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      }

      streamRef.current = stream;
      setActiveStream(stream);

      const recorder = new MediaRecorder(stream);
      audioChunks.current = [];

      recorder.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) {
          audioChunks.current.push(event.data);
        }
      };

      recorder.onstop = () => {
        const audioBlob = new Blob(audioChunks.current, { type: 'audio/wav' });
        const finalTranscript = liveTranscriptRef.current.trim();
        onAudioRecorded(audioBlob, finalTranscript);
        cleanupAudio();
      };

      recorder.start(100);
      mediaRecorderRef.current = recorder;
      onStateChange('Listening');

      startVadMonitoring(stream);
    } catch (err) {
      console.error('Microphone access error:', err);
      cleanupAudio();
      onStateChange('Error');
    }
  };

  const handleClick = () => {
    if (state === 'Listening') {
      stopRecording();
    } else if (state === 'Idle' || state === 'Complete' || state === 'Error') {
      startRecording();
    }
  };

  const getButtonStyles = () => {
    switch (state) {
      case 'Listening':
        return 'bg-white text-rose-600 border border-rose-500/30 shadow-[0_0_30px_rgba(244,63,94,0.45)] animate-pulse';
      case 'Processing':
      case 'Generating':
        return 'bg-slate-900/60 border border-slate-700/60 text-white cursor-wait';
      case 'Error':
        return 'bg-white text-amber-600 border border-amber-500/30 shadow-[0_0_30px_rgba(217,119,6,0.4)] hover:scale-105 cursor-pointer';
      default:
        return 'bg-white text-black hover:scale-105 shadow-[0_0_24px_rgba(255,255,255,0.32)] hover:shadow-[0_0_32px_rgba(255,255,255,0.48)] cursor-pointer';
    }
  };

  return (
    <div className="flex flex-col items-center justify-center py-6 w-full max-w-lg">
      {/* Central Interactive Mic Button */}
      <button
        onClick={handleClick}
        disabled={state === 'Processing' || state === 'Generating'}
        className={`w-28 h-28 rounded-full flex items-center justify-center transition-all duration-300 transform active:scale-95 ${getButtonStyles()}`}
        aria-label="Microphone Query"
      >
        {state === 'Listening' ? (
          <Square className="w-10 h-10 fill-current" />
        ) : state === 'Processing' || state === 'Generating' ? (
          <Loader2 className="w-12 h-12 animate-spin" />
        ) : state === 'Error' ? (
          <AlertCircle className="w-10 h-10" />
        ) : (
          <Mic className="w-11 h-11" />
        )}
      </button>

      {/* Live Audio Waveform Bars & VAD Status */}
      {state === 'Listening' && (
        <div className="flex flex-col items-center gap-2 mt-6 animate-fadeIn">
          <div className="flex items-center gap-3 px-5 py-2.5 rounded-full glass-card border border-rose-500/30 shadow-lg shadow-rose-950/20">
            <Volume2 className={`w-4 h-4 flex-shrink-0 transition-colors ${isVoiceActive ? 'text-emerald-400 animate-pulse' : 'text-rose-400'}`} />
            <WaveformVisualizer stream={activeStream} isRecording={state === 'Listening'} />
            <span className="text-xs font-mono font-medium flex items-center gap-1.5 min-w-[90px]">
              {isVoiceActive ? (
                <span className="text-emerald-300 flex items-center gap-1">
                  <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping"></span>
                  Speaking
                </span>
              ) : silenceCountdown !== null ? (
                <span className="text-amber-300 flex items-center gap-1 font-mono text-[11px]">
                  <Radio className="w-3 h-3 text-amber-400 animate-pulse" />
                  Auto-answering in {silenceCountdown}s...
                </span>
              ) : (
                <span className="text-rose-300">Listening...</span>
              )}
            </span>
          </div>

          {/* VAD Auto-Stop Mode Pill */}
          <div className="flex items-center gap-2 text-[11px] font-mono text-slate-400 mt-1">
            <button
              onClick={() => setVadEnabled(!vadEnabled)}
              className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full border transition-all cursor-pointer ${
                vadEnabled
                  ? 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30 hover:bg-emerald-500/20'
                  : 'bg-slate-800/80 text-slate-400 border-slate-700 hover:text-white'
              }`}
              title="Toggle automatic silence detection"
            >
              <Zap className={`w-3 h-3 ${vadEnabled ? 'text-emerald-400' : 'text-slate-500'}`} />
              <span>Noise Filter & Auto-Stop: {vadEnabled ? 'ACTIVE' : 'OFF'}</span>
            </button>
          </div>
        </div>
      )}

      {/* Real-time Speech Transcript Display Box */}
      {state === 'Listening' && (
        <div className="w-full mt-4 p-4 rounded-2xl glass-panel border border-rose-500/30 text-center animate-fadeIn shadow-lg shadow-rose-950/20">
          <div className="flex items-center justify-center gap-2 text-xs font-semibold text-rose-400 uppercase tracking-wider mb-2">
            <Sparkles className="w-3.5 h-3.5 animate-spin" />
            <span>Listening in Real Time</span>
          </div>
          <p className="text-sm font-medium text-slate-100 min-h-[1.5rem] leading-relaxed">
            {liveTranscript ? `"${liveTranscript}"` : <span className="text-slate-500 italic">Start speaking your question...</span>}
          </p>
        </div>
      )}

      {/* Status Label & Error Recovery */}
      <div className="mt-8 text-center max-w-sm">
        <span className="text-xs sm:text-sm font-medium tracking-wider uppercase text-slate-400">
          {state === 'Listening' && (vadEnabled ? 'Speak naturally — will auto-answer when you finish' : 'Tap the square button to finish speaking')}
          {state === 'Processing' && 'STT Transcription in progress...'}
          {state === 'Generating' && 'Grounded RAG Retrieval & LLM Generation...'}
          {state === 'Idle' && 'Tap to ask anything via voice'}
          {state === 'Complete' && 'Ready for next question'}
          {state === 'Error' && (
            <span
              onClick={startRecording}
              className="text-amber-400 font-semibold flex items-center justify-center gap-2 cursor-pointer hover:text-amber-300 transition-colors"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span>Microphone access blocked / failed. Tap here to retry</span>
            </span>
          )}
        </span>
      </div>
    </div>
  );
};
