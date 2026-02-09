'use client';

import { useEffect, useRef, useState, useCallback } from 'react';
import { sendVoice, checkRecaptchaStatus } from '@/lib/api';
import type { Assessment } from '@/lib/types';

declare global {
  interface Window {
    grecaptcha?: {
      ready: (callback: () => void) => void;
      render: (container: string | HTMLElement, params: {
        sitekey: string;
        callback: (token: string) => void;
        'expired-callback': () => void;
      }) => number;
      reset: (widgetId: number) => void;
    };
    onRecaptchaLoad?: () => void;
  }
}

const RECAPTCHA_SITE_KEY = process.env.NEXT_PUBLIC_RECAPTCHA_SITE_KEY || '';

interface VoiceRecorderProps {
  incidentId: string;
  onAssessment?: (assessment: Assessment) => void;
  disabled?: boolean;
}

export function VoiceRecorder({ incidentId, onAssessment, disabled = false }: VoiceRecorderProps) {
  const [recording, setRecording] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [responseText, setResponseText] = useState('');
  const [audioSrc, setAudioSrc] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [recaptchaToken, setRecaptchaToken] = useState<string | null>(null);
  const [recaptchaReady, setRecaptchaReady] = useState(false);
  const [recaptchaError, setRecaptchaError] = useState<string | null>(null);
  const [ipVerified, setIpVerified] = useState(false);
  const [recaptchaRequired, setRecaptchaRequired] = useState(true);
  const [statusChecked, setStatusChecked] = useState(false);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const recaptchaWidgetRef = useRef<number | null>(null);
  const recaptchaContainerRef = useRef<HTMLDivElement | null>(null);

  const MAX_RECORDING_SECONDS = 60;

  const renderRecaptcha = useCallback(() => {
    console.log('renderRecaptcha called:', {
      hasGrecaptcha: !!window.grecaptcha,
      hasContainer: !!recaptchaContainerRef.current,
      widgetId: recaptchaWidgetRef.current,
    });

    if (
      window.grecaptcha &&
      recaptchaContainerRef.current &&
      recaptchaWidgetRef.current === null
    ) {
      try {
        console.log('Rendering reCAPTCHA widget...');
        recaptchaWidgetRef.current = window.grecaptcha.render(recaptchaContainerRef.current, {
          sitekey: RECAPTCHA_SITE_KEY,
          callback: (token: string) => {
            console.log('reCAPTCHA verified, token received');
            setRecaptchaToken(token);
            setRecaptchaError(null);
          },
          'expired-callback': () => {
            console.log('reCAPTCHA token expired');
            setRecaptchaToken(null);
          },
        });
        console.log('reCAPTCHA widget rendered successfully');
        setRecaptchaReady(true);
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to load reCAPTCHA';
        setRecaptchaError(message);
        console.error('reCAPTCHA render error:', err);
      }
    }
  }, []);

  // Check if IP is already verified on mount
  useEffect(() => {
    checkRecaptchaStatus()
      .then(({ verified, required }) => {
        console.log('reCAPTCHA status:', { verified, required });
        setIpVerified(verified);
        setRecaptchaRequired(required);
        if (verified || !required) {
          setRecaptchaReady(true); // No need to show captcha
        }
        setStatusChecked(true);
      })
      .catch((err) => {
        console.error('reCAPTCHA status check failed:', err);
        setRecaptchaError(`Failed to check verification status: ${err.message || 'Unknown error'}`);
        setRecaptchaRequired(true);
        setStatusChecked(true);
      });
  }, []);

  useEffect(() => {
    // Wait for status check to complete
    if (!statusChecked) {
      return;
    }

    // Skip if IP already verified or captcha not required
    if (ipVerified || !recaptchaRequired) {
      console.log('reCAPTCHA skipped:', { ipVerified, recaptchaRequired });
      return;
    }

    if (!RECAPTCHA_SITE_KEY) {
      setRecaptchaError('reCAPTCHA not configured: NEXT_PUBLIC_RECAPTCHA_SITE_KEY is missing');
      return;
    }

    console.log('Loading reCAPTCHA widget...');

    let timeoutId: ReturnType<typeof setTimeout>;
    let pollId: ReturnType<typeof setInterval>;

    // Timeout after 2 seconds
    timeoutId = setTimeout(() => {
      if (!recaptchaReady) {
        setRecaptchaError('reCAPTCHA failed to load (timeout). You can still use the app.');
      }
    }, 2000);

    const tryRender = () => {
      // Poll for grecaptcha.render to be available
      pollId = setInterval(() => {
        if (window.grecaptcha?.render && typeof window.grecaptcha.render === 'function') {
          clearInterval(pollId);
          clearTimeout(timeoutId);
          renderRecaptcha();
        }
      }, 100);
    };

    // If script already loaded
    const existingScript = document.querySelector('script[src*="recaptcha/api.js"]');
    if (existingScript) {
      tryRender();
      return;
    }

    window.onRecaptchaLoad = tryRender;

    const script = document.createElement('script');
    script.src = 'https://www.google.com/recaptcha/api.js?onload=onRecaptchaLoad&render=explicit';
    script.async = true;
    script.defer = true;
    script.onerror = () => {
      clearTimeout(timeoutId);
      setRecaptchaError('Failed to load reCAPTCHA script');
    };
    document.head.appendChild(script);

    return () => {
      window.onRecaptchaLoad = undefined;
      clearTimeout(timeoutId);
      clearInterval(pollId);
    };
  }, [renderRecaptcha, recaptchaReady, ipVerified, recaptchaRequired, statusChecked]);

  async function startRecording() {
    setError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      mediaRecorderRef.current = recorder;
      chunksRef.current = [];

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };

      recorder.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop());
        const blob = new Blob(chunksRef.current, { type: 'audio/webm' });
        await processAudio(blob);
      };

      recorder.start();
      setRecording(true);

      timerRef.current = setTimeout(() => {
        if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
          mediaRecorderRef.current.stop();
          setRecording(false);
        }
      }, MAX_RECORDING_SECONDS * 1000);
    } catch (err) {
      setError('Microphone access denied. Please allow microphone access.');
    }
  }

  function stopRecording() {
    if (timerRef.current) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }
    if (mediaRecorderRef.current && recording) {
      mediaRecorderRef.current.stop();
      setRecording(false);
    }
  }

  async function processAudio(blob: Blob) {
    setProcessing(true);
    setTranscript('');
    setResponseText('');
    setAudioSrc(null);

    try {
      const res = await sendVoice(incidentId, blob, recaptchaToken || undefined);
      setTranscript(res.transcript);
      setResponseText(res.response_text);

      if (res.audio_base64) {
        setAudioSrc(`data:audio/mp3;base64,${res.audio_base64}`);
      }

      if (res.assessment && onAssessment) {
        onAssessment(res.assessment);
      }

      // Backend verified the token and saved our IP - mark as verified
      if (recaptchaToken) {
        setIpVerified(true);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Voice processing failed');
    } finally {
      setProcessing(false);
      // Reset reCAPTCHA after each use (tokens are single-use)
      setRecaptchaToken(null);
      if (window.grecaptcha && recaptchaWidgetRef.current !== null) {
        window.grecaptcha.reset(recaptchaWidgetRef.current);
      }
    }
  }

  // Allow recording if: IP verified, captcha token obtained, captcha failed/loading, or no captcha required
  const canRecord = ipVerified || recaptchaToken !== null || recaptchaError !== null || !recaptchaRequired || !statusChecked;

  return (
    <div>
      {recaptchaError && (
        <div
          style={{
            padding: '12px',
            marginBottom: '16px',
            background: '#fff3cd',
            border: '1px solid #ffc107',
            borderRadius: '6px',
            fontSize: '13px',
            color: '#856404',
          }}
        >
          <strong>reCAPTCHA issue:</strong> {recaptchaError}
        </div>
      )}

      {statusChecked && RECAPTCHA_SITE_KEY && !recaptchaError && !ipVerified && recaptchaRequired && (
        <div style={{ marginBottom: '16px' }}>
          <div ref={recaptchaContainerRef} />
          {!recaptchaReady && (
            <p style={{ color: '#666', fontSize: '13px' }}>Loading verification...</p>
          )}
          {recaptchaReady && !recaptchaToken && (
            <p style={{ color: '#999', fontSize: '13px', marginTop: '8px' }}>
              Please verify you are human before recording.
            </p>
          )}
        </div>
      )}

      <div style={{ display: 'flex', gap: '12px', marginBottom: '16px' }}>
        {!recording ? (
          <button
            onClick={startRecording}
            disabled={processing || !canRecord || disabled}
            style={{
              padding: '12px 24px',
              background: '#c0392b',
              color: '#fff',
              border: 'none',
              borderRadius: '6px',
              cursor: processing || !canRecord || disabled ? 'not-allowed' : 'pointer',
              opacity: processing || !canRecord || disabled ? 0.5 : 1,
              fontWeight: 'bold',
              fontSize: '14px',
            }}
          >
            {disabled ? 'Incident Closed' : processing ? 'Processing...' : 'Start Recording'}
          </button>
        ) : (
          <button
            onClick={stopRecording}
            style={{
              padding: '12px 24px',
              background: '#333',
              color: '#fff',
              border: 'none',
              borderRadius: '6px',
              cursor: 'pointer',
              fontWeight: 'bold',
              fontSize: '14px',
            }}
          >
            Stop Recording
          </button>
        )}
      </div>

      {recording && (
        <p style={{ color: '#c0392b', fontSize: '14px', marginBottom: '12px' }}>
          Recording... Speak now.
        </p>
      )}

      {error && (
        <p style={{ color: 'red', fontSize: '13px', marginBottom: '12px' }}>
          {error}
        </p>
      )}

      {transcript && (
        <div
          style={{
            padding: '12px',
            border: '1px solid #ddd',
            borderRadius: '8px',
            marginBottom: '12px',
            background: '#f9f9f9',
          }}
        >
          <strong style={{ fontSize: '13px', color: '#666' }}>Transcript:</strong>
          <p style={{ margin: '4px 0 0', fontSize: '14px' }}>{transcript}</p>
        </div>
      )}

      {responseText && (
        <div
          style={{
            padding: '12px',
            border: '1px solid #cce5cc',
            borderRadius: '8px',
            marginBottom: '12px',
            background: '#f0f8f0',
          }}
        >
          <strong style={{ fontSize: '13px', color: '#666' }}>Assistant:</strong>
          <p style={{ margin: '4px 0 0', fontSize: '14px' }}>{responseText}</p>
        </div>
      )}

      {audioSrc && (
        <div style={{ marginTop: '8px' }}>
          <audio controls src={audioSrc} style={{ width: '100%' }} />
        </div>
      )}
    </div>
  );
}
