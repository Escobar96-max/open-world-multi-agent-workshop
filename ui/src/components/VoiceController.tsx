import React, { useState, useRef } from 'react';
import { Mic, MicOff, Loader2, Volume2 } from 'lucide-react';

interface VoiceControllerProps {
  onTranscriptionReceived: (text: string) => void;
  className?: string;
}

export const VoiceController: React.FC<VoiceControllerProps> = ({
  onTranscriptionReceived,
  className = ''
}) => {
  const [recording, setRecording] = useState<boolean>(false);
  const [processing, setProcessing] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);

  const startListening = async () => {
    setErrorMsg(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaStreamRef.current = stream;

      // Select supported MIME type
      const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
        ? 'audio/webm;codecs=opus'
        : MediaRecorder.isTypeSupported('audio/ogg;codecs=opus')
        ? 'audio/ogg;codecs=opus'
        : 'audio/wav';

      const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
      mediaRecorderRef.current = recorder;
      audioChunksRef.current = [];

      recorder.ondataavailable = (event: BlobEvent) => {
        if (event.data && event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      recorder.onstop = async () => {
        // Release hardware mic stream
        if (mediaStreamRef.current) {
          mediaStreamRef.current.getTracks().forEach((track) => track.stop());
          mediaStreamRef.current = null;
        }

        const audioBlob = new Blob(audioChunksRef.current, { type: mimeType || 'audio/wav' });
        if (audioBlob.size === 0) {
          setProcessing(false);
          return;
        }

        setProcessing(true);
        try {
          const formData = new FormData();
          formData.append('file', audioBlob, 'mic_input.wav');

          // Relative endpoint with fallback
          const baseUrl = window.location.origin.includes(':5173')
            ? 'http://127.0.0.1:8000'
            : '';

          const res = await fetch(`${baseUrl}/api/v1/voice/transcribe`, {
            method: 'POST',
            body: formData,
          });

          if (!res.ok) {
            throw new Error(`Server returned HTTP ${res.status}`);
          }

          const data = await res.json();
          if (data && data.transcription) {
            onTranscriptionReceived(data.transcription);
          } else {
            setErrorMsg('No speech detected.');
          }
        } catch (err: any) {
          console.error('STT Transcription error:', err);
          setErrorMsg('Transcription failed. Check microphone and backend.');
        } finally {
          setProcessing(false);
        }
      };

      recorder.start();
      setRecording(true);
    } catch (err: any) {
      console.error('Microphone access denied or unsupported:', err);
      setErrorMsg('Microphone unavailable. Use quick prompt buttons below!');
      setTimeout(() => setErrorMsg(null), 4000);
      setRecording(false);
    }
  };

  const stopListening = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
    }
    setRecording(false);
  };

  return (
    <div className={`relative flex items-center ${className}`}>
      <button
        type="button"
        onClick={recording ? stopListening : startListening}
        disabled={processing}
        title={recording ? 'Click to finish speaking' : 'Click to speak via faster-whisper'}
        className={`px-3 py-2 rounded-xl flex items-center gap-2 text-xs font-semibold tracking-wide transition-all shadow-md select-none ${
          recording
            ? 'bg-rose-600 text-white animate-pulse shadow-rose-600/30 hover:bg-rose-700 ring-2 ring-rose-400'
            : processing
            ? 'bg-purple-900/60 text-purple-300 border border-purple-500/40 cursor-wait'
            : 'bg-purple-950/60 text-purple-200 border border-purple-500/40 hover:bg-purple-900/80 hover:text-white hover:border-purple-400'
        }`}
      >
        {processing ? (
          <>
            <Loader2 className="w-4 h-4 animate-spin text-purple-300" />
            <span>Transcribing...</span>
          </>
        ) : recording ? (
          <>
            <MicOff className="w-4 h-4 text-white animate-bounce" />
            <span>Listening... (Click Stop)</span>
          </>
        ) : (
          <>
            <Mic className="w-4 h-4 text-purple-400" />
            <span>Voice Mode</span>
          </>
        )}
      </button>

      {errorMsg && (
        <span 
          onClick={() => setErrorMsg(null)}
          className="absolute -top-7 left-0 text-[10px] text-amber-300 bg-slate-950/95 px-2.5 py-0.5 rounded border border-amber-500/60 whitespace-nowrap z-30 shadow-md cursor-pointer"
        >
          {errorMsg}
        </span>
      )}
    </div>
  );
};

const speakFallback = (rawText: string, persona: 'Nova' | 'Orion') => {
  if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
    window.speechSynthesis.cancel();
    const clean = rawText.replace(/[*_#`~[\]()]/g, ' ').replace(/\s+/g, ' ').trim();
    const utterance = new SpeechSynthesisUtterance(clean);
    utterance.rate = 1.02;
    utterance.pitch = persona === 'Nova' ? 1.25 : 0.92;
    window.speechSynthesis.speak(utterance);
  }
};

/**
 * Helper to play spoken audio response using Edge-TTS with SpeechSynthesis fallback
 */
export const playAgentVoice = async (text: string, persona: 'Nova' | 'Orion' = 'Nova'): Promise<void> => {
  try {
    const baseUrl = window.location.origin.includes(':5173')
      ? 'http://127.0.0.1:8000'
      : '';

    const formData = new FormData();
    formData.append('text', text);
    formData.append('persona', persona);

    let res = await fetch(`${baseUrl}/api/v1/voice/speak`, {
      method: 'POST',
      body: formData,
    }).catch(() => null);

    if (!res || !res.ok) {
      res = await fetch('http://127.0.0.1:8000/api/v1/voice/speak', {
        method: 'POST',
        body: formData,
      }).catch(() => null);
    }

    if (!res || !res.ok) {
      speakFallback(text, persona);
      return;
    }

    const blob = await res.blob();
    const audioUrl = URL.createObjectURL(blob);
    const audio = new Audio(audioUrl);
    audio.play().catch(() => speakFallback(text, persona));
  } catch (err) {
    speakFallback(text, persona);
  }
};
