import React, { useState, useRef, useEffect } from 'react';
import { Mic, Square, Loader2, Volume2, AlertCircle, Sparkles } from 'lucide-react';

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
  const [liveTranscript, setLiveTranscript] = useState<string>('');
  const liveTranscriptRef = useRef<string>('');
  const recognitionRef = useRef<any>(null);
  const audioChunks = useRef<Blob[]>([]);
  const [audioLevels, setAudioLevels] = useState<number[]>([15, 30, 45, 20, 35]);

  // Audio wave animation simulator during recording
  useEffect(() => {
    let interval: any;
    if (state === 'Listening') {
      interval = setInterval(() => {
        setAudioLevels([
          Math.floor(Math.random() * 60) + 15,
          Math.floor(Math.random() * 90) + 20,
          Math.floor(Math.random() * 70) + 30,
          Math.floor(Math.random() * 85) + 15,
          Math.floor(Math.random() * 50) + 20,
        ]);
      }, 120);
    }
    return () => clearInterval(interval);
  }, [state]);

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
      };

      recorder.start();
      setMediaRecorder(recorder);
      onStateChange('Listening');
    } catch (err) {
      console.error('Microphone access error:', err);
      onStateChange('Error');
    }
  };

  const stopRecording = () => {
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

      {/* Live Audio Waveform Bars */}
      {state === 'Listening' && (
        <div className="flex items-center gap-1.5 h-10 mt-6 px-4 py-2 rounded-full glass-card">
          <Volume2 className="w-4 h-4 text-rose-400 mr-2 animate-pulse" />
          {audioLevels.map((height, idx) => (
            <div
              key={idx}
              className="w-1.5 bg-rose-500 rounded-full transition-all duration-100"
              style={{ height: `${height}%` }}
            />
          ))}
          <span className="text-xs font-mono text-rose-300 ml-2">Recording Voice...</span>
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
      <div className="mt-8 text-center">
        <span className="text-xs sm:text-sm font-medium tracking-wider uppercase text-slate-400">
          {state === 'Listening' && 'Tap the red button to finish speaking'}
          {state === 'Processing' && 'STT Transcription in progress...'}
          {state === 'Generating' && 'Grounded RAG Retrieval & LLM Generation...'}
          {state === 'Idle' && 'Tap to ask anything via voice'}
          {state === 'Complete' && 'Ready for next question'}
          {state === 'Error' && 'Mic access failed or error occurred'}
        </span>
      </div>
    </div>
  );
};
