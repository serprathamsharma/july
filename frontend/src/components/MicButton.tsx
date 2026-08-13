import React, { useState, useRef, useEffect } from 'react';
import { Mic, Square, Loader2, Volume2, AlertCircle } from 'lucide-react';

export type MicState = 'Idle' | 'Listening' | 'Processing' | 'Generating' | 'Complete' | 'Error';

interface MicButtonProps {
  state: MicState;
  onAudioRecorded: (blob: Blob) => void;
  onStateChange: (newState: MicState) => void;
}

export const MicButton: React.FC<MicButtonProps> = ({ state, onAudioRecorded, onStateChange }) => {
  const [mediaRecorder, setMediaRecorder] = useState<MediaRecorder | null>(null);
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
        onAudioRecorded(audioBlob);
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
    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
      mediaRecorder.stop();
      onStateChange('Processing');
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
        return 'bg-rose-600 hover:bg-rose-500 shadow-[0_0_40px_rgba(225,29,72,0.7)] animate-pulse';
      case 'Processing':
      case 'Generating':
        return 'bg-indigo-600/80 cursor_wait shadow-[0_0_30px_rgba(99,102,241,0.5)]';
      case 'Error':
        return 'bg-amber-600 hover:bg-amber-500 shadow-[0_0_30px_rgba(217,119,6,0.6)]';
      default:
        return 'bg-indigo-600 hover:bg-indigo-500 glow-button';
    }
  };

  return (
    <div className="flex flex-col items-center justify-center py-6">
      {/* Central Interactive Mic Button */}
      <button
        onClick={handleClick}
        disabled={state === 'Processing' || state === 'Generating'}
        className={`w-28 h-28 rounded-full flex items-center justify-center transition-all duration-300 transform active:scale-95 ${getButtonStyles()}`}
        aria-label="Microphone Query"
      >
        {state === 'Listening' ? (
          <Square className="w-10 h-10 text-white fill-white" />
        ) : state === 'Processing' || state === 'Generating' ? (
          <Loader2 className="w-12 h-12 text-white animate-spin" />
        ) : state === 'Error' ? (
          <AlertCircle className="w-10 h-10 text-white" />
        ) : (
          <Mic className="w-11 h-11 text-white" />
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

      {/* Status Label */}
      <div className="mt-4 text-center">
        <span className="text-sm font-medium tracking-wide uppercase text-slate-400">
          {state === 'Listening' && 'Tap to stop recording'}
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
