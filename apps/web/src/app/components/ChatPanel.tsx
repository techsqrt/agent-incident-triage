'use client';

import { useState } from 'react';
import { sendMessage } from '@/lib/api';
import type { Message, Assessment } from '@/lib/types';

interface ChatPanelProps {
  incidentId: string;
  onAssessment?: (assessment: Assessment) => void;
}

export function ChatPanel({ incidentId, onAssessment }: ChatPanelProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSend() {
    if (!input.trim() || loading) return;

    const text = input.trim();
    setInput('');
    setError(null);
    setLoading(true);

    try {
      const res = await sendMessage(incidentId, text);
      setMessages((prev) => [...prev, res.message, res.assistant_message]);
      if (res.assessment && onAssessment) {
        onAssessment(res.assessment);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to send message');
    } finally {
      setLoading(false);
    }
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
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
          placeholder="Describe your symptoms..."
          disabled={loading}
          style={{
            flex: 1,
            padding: '10px 14px',
            border: '1px solid #ccc',
            borderRadius: '6px',
            fontSize: '14px',
          }}
        />
        <button
          onClick={handleSend}
          disabled={loading || !input.trim()}
          style={{
            padding: '10px 20px',
            background: '#333',
            color: '#fff',
            border: 'none',
            borderRadius: '6px',
            cursor: loading ? 'not-allowed' : 'pointer',
            opacity: loading || !input.trim() ? 0.5 : 1,
            fontWeight: 'bold',
          }}
        >
          Send
        </button>
      </div>
    </div>
  );
}
