'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { fetchIncident, closeIncident, reopenIncident } from '@/lib/api';
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
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchIncident(incidentId)
      .then(setIncident)
      .catch((err) => setError(err instanceof Error ? err.message : 'Failed to load'))
      .finally(() => setLoading(false));
  }, [incidentId]);

  function handleAssessment(a: Assessment) {
    setAssessment(a);
    fetchIncident(incidentId).then(setIncident).catch(() => {});
  }

  async function handleClose() {
    setActionLoading(true);
    try {
      const updated = await closeIncident(incidentId);
      setIncident(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to close');
    } finally {
      setActionLoading(false);
    }
  }

  async function handleReopen() {
    setActionLoading(true);
    try {
      const updated = await reopenIncident(incidentId);
      setIncident(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to reopen');
    } finally {
      setActionLoading(false);
    }
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

  const isClosed = incident.status === 'CLOSED';
  const tabs: { key: Tab; label: string }[] = [
    { key: 'chat', label: 'Chat' },
    { key: 'voice', label: 'Voice' },
    { key: 'timeline', label: 'Timeline' },
  ];

  const statusColors: Record<string, string> = {
    OPEN: '#27ae60',
    TRIAGE_READY: '#f39c12',
    ESCALATED: '#c0392b',
    CLOSED: '#7f8c8d',
  };

  return (
    <div style={{ padding: '32px', maxWidth: '900px', margin: '0 auto' }}>
      <div style={{ marginBottom: '20px' }}>
        <Link href="/triage" style={{ color: '#666', fontSize: '14px', textDecoration: 'none' }}>
          &larr; Dashboard
        </Link>
      </div>

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '16px' }}>
        <div>
          <h1 style={{ fontSize: '22px', fontWeight: 'bold', margin: 0 }}>
            Incident {incidentId.slice(0, 8)}
          </h1>
          <p style={{ color: '#666', fontSize: '14px', margin: '4px 0 0' }}>
            {incident.domain} | {incident.mode} |{' '}
            <span
              style={{
                color: statusColors[incident.status] || '#333',
                fontWeight: 'bold',
              }}
            >
              {incident.status}
            </span>
          </p>
        </div>

        <div>
          {isClosed ? (
            <button
              onClick={handleReopen}
              disabled={actionLoading}
              style={{
                padding: '8px 16px',
                background: '#27ae60',
                color: '#fff',
                border: 'none',
                borderRadius: '4px',
                cursor: actionLoading ? 'not-allowed' : 'pointer',
                opacity: actionLoading ? 0.6 : 1,
                fontSize: '14px',
                fontWeight: 'bold',
              }}
            >
              {actionLoading ? 'Reopening...' : 'Reopen Incident'}
            </button>
          ) : (
            <button
              onClick={handleClose}
              disabled={actionLoading}
              style={{
                padding: '8px 16px',
                background: '#e74c3c',
                color: '#fff',
                border: 'none',
                borderRadius: '4px',
                cursor: actionLoading ? 'not-allowed' : 'pointer',
                opacity: actionLoading ? 0.6 : 1,
                fontSize: '14px',
                fontWeight: 'bold',
              }}
            >
              {actionLoading ? 'Closing...' : 'Close Incident'}
            </button>
          )}
        </div>
      </div>

      {isClosed && (
        <div style={{
          padding: '12px 16px',
          background: '#f8f9fa',
          border: '1px solid #dee2e6',
          borderRadius: '4px',
          marginBottom: '20px',
          color: '#6c757d',
        }}>
          This incident is closed. Reopen it to continue the conversation.
        </div>
      )}

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
        <div style={{ display: activeTab === 'chat' ? 'block' : 'none' }}>
          <ChatPanel incidentId={incidentId} onAssessment={handleAssessment} disabled={isClosed} />
        </div>
        <div style={{ display: activeTab === 'voice' ? 'block' : 'none' }}>
          <VoiceRecorder incidentId={incidentId} onAssessment={handleAssessment} disabled={isClosed} />
        </div>
        <div style={{ display: activeTab === 'timeline' ? 'block' : 'none' }}>
          <Timeline incidentId={incidentId} />
        </div>
      </div>
    </div>
  );
}
