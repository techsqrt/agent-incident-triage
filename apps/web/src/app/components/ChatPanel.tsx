'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { sendMessage, checkRecaptchaStatus } from '@/lib/api';
import type { Message, Assessment } from '@/lib/types';

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
    onRecaptchaLoadChat?: () => void;
  }
}

const RECAPTCHA_SITE_KEY = process.env.NEXT_PUBLIC_RECAPTCHA_SITE_KEY || '';

interface ChatPanelProps {
  incidentId: string;
  onAssessment?: (assessment: Assessment) => void;
  disabled?: boolean;
}

export function ChatPanel({ incidentId, onAssessment, disabled = false }: ChatPanelProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [recaptchaToken, setRecaptchaToken] = useState<string | null>(null);
  const [recaptchaReady, setRecaptchaReady] = useState(false);
  const [recaptchaError, setRecaptchaError] = useState<string | null>(null);
  const [ipVerified, setIpVerified] = useState(false);
  const [recaptchaRequired, setRecaptchaRequired] = useState(true);
  const [statusChecked, setStatusChecked] = useState(false);
  const recaptchaWidgetRef = useRef<number | null>(null);
  const recaptchaContainerRef = useRef<HTMLDivElement | null>(null);

  const renderRecaptcha = useCallback(() => {
    console.log('renderRecaptcha called (chat):', {
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
        console.log('Rendering reCAPTCHA widget (chat)...');
        recaptchaWidgetRef.current = window.grecaptcha.render(recaptchaContainerRef.current, {
          sitekey: RECAPTCHA_SITE_KEY,
          callback: (token: string) => {
            console.log('reCAPTCHA verified (chat), token received');
            setRecaptchaToken(token);
            setRecaptchaError(null);
          },
          'expired-callback': () => {
            console.log('reCAPTCHA token expired (chat)');
            setRecaptchaToken(null);
          },
        });
        console.log('reCAPTCHA widget rendered successfully (chat)');
        setRecaptchaReady(true);
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to load reCAPTCHA';
        setRecaptchaError(message);
        console.error('reCAPTCHA render error (chat):', err);
      }
    }
  }, []);

  // Check if IP is already verified on mount
  useEffect(() => {
    checkRecaptchaStatus()
      .then(({ verified, required }) => {
        console.log('reCAPTCHA status (chat):', { verified, required });
        setIpVerified(verified);
        setRecaptchaRequired(required);
        if (verified || !required) {
          setRecaptchaReady(true); // No need to show captcha
        }
        setStatusChecked(true);
      })
      .catch((err) => {
        console.error('reCAPTCHA status check failed (chat):', err);
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
      console.log('reCAPTCHA skipped (chat):', { ipVerified, recaptchaRequired });
      return;
    }

    if (!RECAPTCHA_SITE_KEY) {
      setRecaptchaError('reCAPTCHA not configured: NEXT_PUBLIC_RECAPTCHA_SITE_KEY is missing');
      return;
    }

    console.log('Loading reCAPTCHA widget (chat)...');

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

    // If script already loaded (e.g., by VoiceRecorder)
    const existingScript = document.querySelector('script[src*="recaptcha/api.js"]');
    if (existingScript) {
      tryRender();
      return;
    }

    window.onRecaptchaLoadChat = tryRender;

    const script = document.createElement('script');
    script.src = 'https://www.google.com/recaptcha/api.js?onload=onRecaptchaLoadChat&render=explicit';
    script.async = true;
    script.defer = true;
    script.onerror = () => {
      clearTimeout(timeoutId);
      setRecaptchaError('Failed to load reCAPTCHA script');
    };
    document.head.appendChild(script);

    return () => {
      window.onRecaptchaLoadChat = undefined;
      clearTimeout(timeoutId);
      clearInterval(pollId);
    };
  }, [renderRecaptcha, recaptchaReady, ipVerified, recaptchaRequired, statusChecked]);

  async function handleSend() {
    if (!input.trim() || loading) return;

    const text = input.trim();
    setInput('');
    setError(null);
    setLoading(true);

    try {
      const res = await sendMessage(incidentId, text, recaptchaToken || undefined);
      setMessages((prev) => [...prev, res.message, res.assistant_message]);
      if (res.assessment && onAssessment) {
        onAssessment(res.assessment);
      }

      // Backend verified the token and saved our IP - mark as verified
      if (recaptchaToken) {
        setIpVerified(true);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to send message');
    } finally {
      setLoading(false);
      // Reset reCAPTCHA after each use (tokens are single-use)
      setRecaptchaToken(null);
      if (window.grecaptcha && recaptchaWidgetRef.current !== null) {
        window.grecaptcha.reset(recaptchaWidgetRef.current);
      }
    }
  }

  // Allow sending if: IP verified, captcha token obtained, captcha failed/loading, or no captcha required
  const canSend = ipVerified || recaptchaToken !== null || recaptchaError !== null || !recaptchaRequired || !statusChecked;

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
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
              Please verify you are human before sending messages.
            </p>
          )}
        </div>
      )}

      <div
        style={{
          flex: 1,
          overflowY: 'auto',
          padding: '16px',
          border: '1px solid #ddd',
          borderRadius: '8px',
          marginBottom: '12px',
          minHeight: '300px',
          maxHeight: '500px',
          background: '#fafafa',
        }}
      >
        {messages.length === 0 && (
          <p style={{ color: '#999', textAlign: 'center', marginTop: '40px' }}>
            Describe your symptoms to begin the triage assessment.
          </p>
        )}
        {messages.map((msg) => (
          <div
            key={msg.id}
            style={{
              marginBottom: '12px',
              textAlign: msg.role === 'patient' ? 'right' : 'left',
            }}
          >
            <div
              style={{
                display: 'inline-block',
                padding: '8px 14px',
                borderRadius: '12px',
                maxWidth: '80%',
                background: msg.role === 'patient' ? '#333' : '#e8e8e8',
                color: msg.role === 'patient' ? '#fff' : '#333',
                fontSize: '14px',
                lineHeight: '1.5',
              }}
            >
              {msg.content_text}
            </div>
            <div style={{ fontSize: '11px', color: '#999', marginTop: '2px' }}>
              {msg.role === 'patient' ? 'You' : 'Triage Assistant'}
            </div>
          </div>
        ))}
        {loading && (
          <div style={{ textAlign: 'left', color: '#999', fontSize: '14px' }}>
            Analyzing...
          </div>
        )}
      </div>

      {error && (
        <p style={{ color: 'red', fontSize: '13px', marginBottom: '8px' }}>
          {error}
        </p>
      )}

      <div style={{ display: 'flex', gap: '8px' }}>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={disabled ? "Incident is closed" : "Describe your symptoms..."}
          disabled={loading || disabled}
          style={{
            flex: 1,
            padding: '10px 14px',
            border: '1px solid #ccc',
            borderRadius: '6px',
            fontSize: '14px',
            background: disabled ? '#f5f5f5' : '#fff',
          }}
        />
        <button
          onClick={handleSend}
          disabled={loading || !input.trim() || !canSend || disabled}
          style={{
            padding: '10px 20px',
            background: '#333',
            color: '#fff',
            border: 'none',
            borderRadius: '6px',
            cursor: loading || !canSend || disabled ? 'not-allowed' : 'pointer',
            opacity: loading || !input.trim() || !canSend || disabled ? 0.5 : 1,
            fontWeight: 'bold',
          }}
        >
          Send
        </button>
      </div>
    </div>
  );
}
