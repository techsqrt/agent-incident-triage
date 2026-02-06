'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { fetchIncident } from '@/lib/api';
import type { Assessment, Incident } from '@/lib/types';
import { ChatPanel } from '@/app/components/ChatPanel';
import { VoiceRecorder } from '@/app/components/VoiceRecorder';
import { Timeline } from '@/app/components/Timeline';
import { AssessmentCard } from '@/app/components/AssessmentCard';

type Tab = 'chat' | 'voice' | 'timeline';

export default function IncidentDetailPage() {
  const params = useParams();
  const incidentId = params.id as string;

  const [incident, setIncident] = useState<Incident | null>(null);
  const [assessment, setAssessment] = useState<Assessment | null>(null);
  const [activeTab, setActiveTab] = useState<Tab>('chat');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchIncident(incidentId)
      .then(setIncident)
      .catch((err) => setError(err instanceof Error ? err.message : 'Failed to load'))
      .finally(() => setLoading(false));
  }, [incidentId]);

  function handleAssessment(a: Assessment) {
    setAssessment(a);
    // Refresh incident status
    fetchIncident(incidentId).then(setIncident).catch(() => {});
  }

  if (loading) {
    return (
      <div style={{ padding: '32px', maxWidth: '900px', margin: '0 auto' }}>
        <p>Loading incident...</p>
      </div>
    );
  }

  if (error || !incident) {
    return (
      <div style={{ padding: '32px', maxWidth: '900px', margin: '0 auto' }}>
        <p style={{ color: 'red' }}>Error: {error || 'Incident not found'}</p>
        <Link href="/triage" style={{ color: '#333' }}>
          Back to Dashboard
        </Link>
      </div>
    );
  }

  const tabs: { key: Tab; label: string }[] = [
    { key: 'chat', label: 'Chat' },
    { key: 'voice', label: 'Voice' },
    { key: 'timeline', label: 'Timeline' },
  ];

  return (
    <div style={{ padding: '32px', maxWidth: '900px', margin: '0 auto' }}>
      <div style={{ marginBottom: '20px' }}>
        <Link href="/triage" style={{ color: '#666', fontSize: '14px', textDecoration: 'none' }}>
          &larr; Dashboard
        </Link>
      </div>

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
        <div>
          <h1 style={{ fontSize: '22px', fontWeight: 'bold', margin: 0 }}>
            Incident {incidentId.slice(0, 8)}
          </h1>
          <p style={{ color: '#666', fontSize: '14px', margin: '4px 0 0' }}>
            {incident.domain} | {incident.mode === 'B' ? 'Modular Pipeline' : 'Realtime'} |{' '}
            <span
              style={{
                color: incident.status === 'ESCALATED' ? '#c0392b' : '#333',
                fontWeight: incident.status === 'ESCALATED' ? 'bold' : 'normal',
              }}
            >
              {incident.status}
            </span>
          </p>
        </div>
      </div>

      {assessment && (
        <div style={{ marginBottom: '20px' }}>
          <AssessmentCard assessment={assessment} />
        </div>
      )}

      <div style={{ display: 'flex', gap: '4px', marginBottom: '20px' }}>
        {tabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            style={{
              padding: '8px 18px',
              border: '1px solid #ccc',
              borderBottom: activeTab === tab.key ? '2px solid #333' : '1px solid #ccc',
              borderRadius: '4px 4px 0 0',
              background: activeTab === tab.key ? '#fff' : '#f5f5f5',
              color: activeTab === tab.key ? '#333' : '#666',
              cursor: 'pointer',
              fontWeight: activeTab === tab.key ? 'bold' : 'normal',
              fontSize: '14px',
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div>
        {activeTab === 'chat' && (
          <ChatPanel incidentId={incidentId} onAssessment={handleAssessment} />
        )}
        {activeTab === 'voice' && (
          <VoiceRecorder incidentId={incidentId} onAssessment={handleAssessment} />
        )}
        {activeTab === 'timeline' && <Timeline incidentId={incidentId} />}
      </div>
    </div>
  );
}
