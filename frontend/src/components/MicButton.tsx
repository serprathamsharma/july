import React, { useState, useRef, useEffect } from 'react';
import { Mic, Square, Loader2, Volume2, AlertCircle, Sparkles, Zap, Radio } from 'lucide-react';
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
  const [mediaRecorder, setMediaRecorder] = useState<MediaRecorder | null>(null);
  const [activeStream, setActiveStream] = useState<MediaStream | null>(null);
  const [liveTranscript, setLiveTranscript] = useState<string>('');
  const [vadEnabled, setVadEnabled] = useState<boolean>(true);
  const [isVoiceActive, setIsVoiceActive] = useState<boolean>(false);
  const [silenceCountdown, setSilenceCountdown] = useState<number | null>(null);

  const liveTranscriptRef = useRef<string>('');
  const recognitionRef = useRef<any>(null);
  const audioChunks = useRef<Blob[]>([]);
  const vadIntervalRef = useRef<number | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const hasSpokenRef = useRef<boolean>(false);
  const lastSpeechTimeRef = useRef<number>(Date.now());
  const recordingStartTimeRef = useRef<number>(Date.now());

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stopVadMonitoring();
      if (audioContextRef.current && audioContextRef.current.state !== 'closed') {
        try {
          audioContextRef.current.close();
        } catch (e) {
          console.warn(e);
        }
      }
    };
  }, []);

  const stopVadMonitoring = () => {
    if (vadIntervalRef.current) {
      window.clearInterval(vadIntervalRef.current);
      vadIntervalRef.current = null;
    }
    setIsVoiceActive(false);
    setSilenceCountdown(null);
  };

  const startVadMonitoring = (stream: MediaStream) => {
    try {
      const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
      const audioCtx = new AudioCtx();
      audioContextRef.current = audioCtx;

      const analyser = audioCtx.createAnalyser();
      analyser.fftSize = 256;
      analyser.smoothingTimeConstant = 0.5;
      analyserRef.current = analyser;

      const source = audioCtx.createMediaStreamSource(stream);
      source.connect(analyser);

      const bufferLength = analyser.frequencyBinCount;
      const dataArray = new Uint8Array(bufferLength);

      hasSpokenRef.current = false;
      lastSpeechTimeRef.current = Date.now();
      recordingStartTimeRef.current = Date.now();

      const SILENCE_TIMEOUT_MS = 1600; // 1.6 seconds of silence after speech stops
      const INITIAL_MAX_SILENCE_MS = 7500; // 7.5 seconds initial silence timeout
      const SPEECH_ENERGY_THRESHOLD = 22; // RMS audio frequency threshold

      vadIntervalRef.current = window.setInterval(() => {
        if (!analyserRef.current) return;

        analyserRef.current.getByteFrequencyData(dataArray);

        // Compute average frequency energy
        let sum = 0;
        for (let i = 0; i < bufferLength; i++) {
          sum += dataArray[i];
        }
        const avgEnergy = sum / bufferLength;
        const now = Date.now();

        // Check if user is actively speaking (either via audio energy or non-empty transcript)
        const isSpeaking = avgEnergy > SPEECH_ENERGY_THRESHOLD || liveTranscriptRef.current.length > 2;

        if (isSpeaking) {
          hasSpokenRef.current = true;
          lastSpeechTimeRef.current = now;
          setIsVoiceActive(true);
          setSilenceCountdown(null);
        } else {
          setIsVoiceActive(false);

          if (!vadEnabled) return;

          // If speech was previously detected, check silence duration
          if (hasSpokenRef.current) {
            const silentDuration = now - lastSpeechTimeRef.current;
            const remainingMs = SILENCE_TIMEOUT_MS - silentDuration;

            if (remainingMs > 0 && remainingMs <= 1200) {
              setSilenceCountdown(Math.ceil(remainingMs / 1000));
            } else if (silentDuration >= SILENCE_TIMEOUT_MS) {
              // Silence threshold reached -> Auto-Stop!
              stopVadMonitoring();
              stopRecording();
            }
          } else {
            // Initial silence timeout if user never spoke
            if (now - recordingStartTimeRef.current >= INITIAL_MAX_SILENCE_MS) {
              stopVadMonitoring();
              stopRecording();
            }
          }
        }
      }, 100);
    } catch (err) {
      console.warn("VAD monitoring initialization error:", err);
    }
  };

  const startRecording = async () => {
    try {
      setLiveTranscript('');
      liveTranscriptRef.current = '';
      if (onLiveTranscriptChange) onLiveTranscriptChange('');

      // Initialize Web Speech API for real-time speech recognition
      const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
      if (SpeechRecognition) {
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
          hasSpokenRef.current = true;
          lastSpeechTimeRef.current = Date.now();

          if (onLiveTranscriptChange) {
            onLiveTranscriptChange(normalized);
          }
        };

        recognition.onerror = (err: any) => {
          console.warn('Speech recognition warning:', err);
        };

        recognition.start();
        recognitionRef.current = recognition;
      }

      // Initialize MediaRecorder for audio blob capture
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      setActiveStream(stream);
      const recorder = new MediaRecorder(stream);
      audioChunks.current = [];

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunks.current.push(event.data);
        }
      };

      recorder.onstop = () => {
        const audioBlob = new Blob(audioChunks.current, { type: 'audio/wav' });
        const finalTranscript = liveTranscriptRef.current.trim();
        onAudioRecorded(audioBlob, finalTranscript);
        stream.getTracks().forEach((track) => track.stop());
        setActiveStream(null);
      };

      recorder.start();
      setMediaRecorder(recorder);
      onStateChange('Listening');

      // Start VAD monitoring
      startVadMonitoring(stream);
    } catch (err) {
      console.error('Microphone access error:', err);
      onStateChange('Error');
    }
  };

  const stopRecording = () => {
    stopVadMonitoring();
    onStateChange('Processing');

    setTimeout(() => {
      if (recognitionRef.current) {
        try {
          recognitionRef.current.stop();
        } catch (e) {
          console.warn(e);
        }
      }

      if (mediaRecorder && mediaRecorder.state !== 'inactive') {
        mediaRecorder.stop();
      }
    }, 250);
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
        return 'bg-white text-amber-600 border border-amber-500/30 shadow-[0_0_30px_rgba(217,119,6,0.4)]';
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
        <div className="flex flex-col items-center gap-2 mt-6">
          <div className="flex items-center gap-3 px-5 py-2.5 rounded-full glass-card border border-rose-500/30 shadow-lg shadow-rose-950/20">
            <Volume2 className={`w-4 h-4 flex-shrink-0 transition-colors ${isVoiceActive ? 'text-emerald-400 animate-pulse' : 'text-rose-400'}`} />
            <WaveformVisualizer stream={activeStream} isRecording={state === 'Listening'} />
            <span className="text-xs font-mono font-medium flex items-center gap-1.5">
              {isVoiceActive ? (
                <span className="text-emerald-300 flex items-center gap-1">
                  <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping"></span>
                  Speaking
                </span>
              ) : silenceCountdown !== null ? (
                <span className="text-amber-300 flex items-center gap-1 font-mono text-[11px]">
                  <Radio className="w-3 h-3 text-amber-400 animate-pulse" />
                  Auto-stop in {silenceCountdown}s...
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
              <span>VAD Auto-Stop: {vadEnabled ? 'ON' : 'OFF'}</span>
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

      {/* Status Label */}
      <div className="mt-8 text-center max-w-sm">
        <span className="text-xs sm:text-sm font-medium tracking-wider uppercase text-slate-400">
          {state === 'Listening' && (vadEnabled ? 'Speak naturally — will auto-submit when you pause' : 'Tap the red button to finish speaking')}
          {state === 'Processing' && 'STT Transcription in progress...'}
          {state === 'Generating' && 'Grounded RAG Retrieval & LLM Generation...'}
          {state === 'Idle' && 'Tap to ask anything via voice'}
          {state === 'Complete' && 'Ready for next question'}
          {state === 'Error' && (
            <span className="text-amber-400 font-semibold flex items-center justify-center gap-1.5 cursor-pointer" onClick={handleClick}>
              <span>Mic access blocked / failed. Tap here to retry or type below</span>
            </span>
          )}
        </span>
      </div>
    </div>
  );
};
