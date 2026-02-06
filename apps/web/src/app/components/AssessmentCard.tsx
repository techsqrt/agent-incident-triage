'use client';

import type { Assessment } from '@/lib/types';

interface AssessmentCardProps {
  assessment: Assessment;
}

const ACUITY_COLORS: Record<number, string> = {
  1: '#c0392b',
  2: '#e67e22',
  3: '#f39c12',
  4: '#27ae60',
  5: '#2ecc71',
};

const ACUITY_LABELS: Record<number, string> = {
  1: 'Immediate',
  2: 'Emergent',
  3: 'Urgent',
  4: 'Less Urgent',
  5: 'Non-Urgent',
};

export function AssessmentCard({ assessment }: AssessmentCardProps) {
  const result = assessment.result_json;
  const acuity = typeof result.acuity === 'number' ? result.acuity : 5;
  const escalate = result.escalate === true;
  const disposition = typeof result.disposition === 'string' ? result.disposition : '';
  const summary = typeof result.summary === 'string' ? result.summary : '';
  const redFlags = Array.isArray(result.red_flags) ? result.red_flags as Array<{ name: string; reason: string }> : [];

  return (
    <div
      style={{
        padding: '16px',
        border: `2px solid ${ACUITY_COLORS[acuity] || '#ccc'}`,
        borderRadius: '8px',
        background: escalate ? '#fef5f5' : '#f9f9f9',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <span
            style={{
              display: 'inline-block',
              padding: '4px 12px',
              borderRadius: '12px',
              background: ACUITY_COLORS[acuity] || '#ccc',
              color: '#fff',
              fontWeight: 'bold',
              fontSize: '14px',
            }}
          >
            ESI-{acuity}: {ACUITY_LABELS[acuity] || 'Unknown'}
          </span>
        </div>
        {escalate && (
          <span
            style={{
              padding: '4px 12px',
              borderRadius: '12px',
              background: '#c0392b',
              color: '#fff',
              fontWeight: 'bold',
              fontSize: '12px',
            }}
          >
            ESCALATED
          </span>
        )}
      </div>

      {summary && (
        <p style={{ margin: '10px 0 0', fontSize: '14px', color: '#555' }}>
          {summary}
        </p>
      )}

      {redFlags.length > 0 && (
        <div style={{ marginTop: '10px' }}>
          <strong style={{ fontSize: '13px', color: '#c0392b' }}>Red Flags:</strong>
          <ul style={{ margin: '4px 0 0', paddingLeft: '20px' }}>
            {redFlags.map((flag, i) => (
              <li key={i} style={{ fontSize: '13px', color: '#666' }}>
                <strong>{flag.name}</strong>: {flag.reason}
              </li>
            ))}
          </ul>
        </div>
      )}

      <div style={{ marginTop: '8px', fontSize: '12px', color: '#999' }}>
        Disposition: {disposition} | Updated:{' '}
        {new Date(assessment.created_at).toLocaleTimeString()}
      </div>
    </div>
  );
}
