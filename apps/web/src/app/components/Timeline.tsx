'use client';

import { useEffect, useState } from 'react';
import { fetchTimeline } from '@/lib/api';
import type { AuditEvent } from '@/lib/types';

interface TimelineProps {
  incidentId: string;
}

const STEP_LABELS: Record<string, string> = {
  STT: 'Speech to Text',
  EXTRACT: 'Data Extraction',
  TRIAGE_RULES: 'Triage Rules',
  GENERATE: 'Response Generation',
  TTS: 'Text to Speech',
  RESPONSE_GENERATED: 'Response Generated',
};

export function Timeline({ incidentId }: TimelineProps) {
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadTimeline();
  }, [incidentId]);

  async function loadTimeline() {
    setLoading(true);
    try {
      const res = await fetchTimeline(incidentId);
      setEvents(res.events);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load timeline');
    } finally {
      setLoading(false);
    }
  }

  if (loading) return <p>Loading timeline...</p>;
  if (error) return <p style={{ color: 'red' }}>{error}</p>;

  if (events.length === 0) {
    return (
      <p style={{ color: '#999', textAlign: 'center', marginTop: '24px' }}>
        No events yet. Send a message or use voice to start.
      </p>
    );
  }

  return (
    <div>
      <button
        onClick={loadTimeline}
        style={{
          padding: '6px 14px',
          border: '1px solid #ccc',
          borderRadius: '4px',
          background: 'transparent',
          cursor: 'pointer',
          fontSize: '13px',
          marginBottom: '16px',
        }}
      >
        Refresh
      </button>

      <div style={{ position: 'relative' }}>
        {events.map((event, i) => (
          <div
            key={event.id}
            style={{
              position: 'relative',
              display: 'flex',
              gap: '12px',
              marginBottom: '16px',
              paddingLeft: '20px',
              borderLeft: '2px solid #ddd',
            }}
          >
            <div
              style={{
                position: 'absolute',
                left: '-6px',
                top: '4px',
                width: '10px',
                height: '10px',
                borderRadius: '50%',
                background: event.step === 'TRIAGE_RULES' ? '#c0392b' : '#333',
              }}
            />
            <div style={{ flex: 1 }}>
              <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                <strong style={{ fontSize: '14px' }}>
                  {STEP_LABELS[event.step] || event.step}
                </strong>
                {event.latency_ms !== null && (
                  <span style={{ fontSize: '12px', color: '#999' }}>
                    {event.latency_ms}ms
                  </span>
                )}
                {event.model_used && (
                  <span
                    style={{
                      fontSize: '11px',
                      color: '#666',
                      background: '#eee',
                      padding: '1px 6px',
                      borderRadius: '3px',
                    }}
                  >
                    {event.model_used}
                  </span>
                )}
              </div>
              <div
                style={{
                  fontSize: '12px',
                  color: '#999',
                  marginTop: '2px',
                }}
              >
                {new Date(event.created_at).toLocaleTimeString()} | trace:{' '}
                {event.trace_id.slice(0, 8)}
              </div>
              {event.payload_json &&
                Object.keys(event.payload_json).length > 0 && (
                  <pre
                    style={{
                      fontSize: '12px',
                      background: '#f5f5f5',
                      padding: '8px',
                      borderRadius: '4px',
                      marginTop: '6px',
                      overflow: 'auto',
                      maxHeight: '150px',
                    }}
                  >
                    {JSON.stringify(event.payload_json, null, 2)}
                  </pre>
                )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
