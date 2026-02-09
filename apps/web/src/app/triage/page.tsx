'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { fetchDomains, createIncident } from '@/lib/api';
import type { Domain } from '@/lib/types';
import { DomainTabs } from '@/app/components/DomainTabs';
import { IncidentsList } from '@/app/components/IncidentsList';

function TechBadge({ label, tooltip }: { label: string; tooltip: string }) {
  return (
    <span
      title={tooltip}
      style={{
        display: 'inline-block',
        padding: '4px 10px',
        margin: '3px',
        background: 'linear-gradient(135deg, #1a1a2e 0%, #16213e 100%)',
        border: '1px solid #0f3460',
        borderRadius: '12px',
        fontSize: '11px',
        color: '#e0e0e0',
        cursor: 'help',
      }}
    >
      {label}
    </span>
  );
}

function HeroBanner() {
  return (
    <div
      style={{
        background: 'linear-gradient(135deg, #c0392b 0%, #8e44ad 100%)',
        borderRadius: '12px',
        padding: '24px',
        marginBottom: '24px',
        color: 'white',
      }}
    >
      <h1 style={{ fontSize: '1.8rem', fontWeight: 700, marginBottom: '8px' }}>
        Agent Incident Triage
      </h1>
      <p style={{ fontSize: '0.95rem', opacity: 0.95, marginBottom: '16px', maxWidth: '600px' }}>
        AI-powered triage with conviction-based risk assessment, deterministic escalation rules, and full audit trail.
      </p>
      <div style={{ display: 'flex', flexWrap: 'wrap' }}>
        <TechBadge label="Next.js 15" tooltip="React frontend with App Router, TypeScript, dynamic routes" />
        <TechBadge label="FastAPI" tooltip="Python API with Pydantic validation, SQLAlchemy ORM" />
        <TechBadge label="GPT-4o" tooltip="LLM extraction with structured output, Whisper STT, TTS" />
        <TechBadge label="PostgreSQL" tooltip="Neon serverless Postgres with JSONB, full audit trail" />
        <TechBadge label="Docker" tooltip="Multi-stage builds, Docker Compose for local dev" />
        <TechBadge label="Vercel" tooltip="Frontend deployment with preview builds per PR" />
        <TechBadge label="Railway" tooltip="API deployment with PostgreSQL addon" />
        <TechBadge label="GitHub Actions" tooltip="CI/CD: pytest, TypeScript checks, linting" />
        <TechBadge label="pytest" tooltip="146 unit/integration tests for API and rules" />
        <TechBadge label="ESI Triage" tooltip="Emergency Severity Index levels 1-5" />
        <TechBadge label="Risk Signals" tooltip="Conviction thresholds: 20% psychiatric, 50% physical" />
        <TechBadge label="Voice" tooltip="Real-time recording, Whisper transcription, TTS playback" />
      </div>
    </div>
  );
}

export default function TriagePage() {
  const router = useRouter();
  const [domains, setDomains] = useState<Domain[]>([]);
  const [activeDomain, setActiveDomain] = useState('medical');
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchDomains()
      .then((res) => {
        setDomains(res.domains);
        const firstActive = res.domains.find((d) => d.active);
        if (firstActive) {
          setActiveDomain(firstActive.name);
        }
      })
      .catch((err) => setError(err instanceof Error ? err.message : 'Unknown error'))
      .finally(() => setLoading(false));
  }, []);

  async function handleStartIncident() {
    setCreating(true);
    setError(null);
    try {
      const incident = await createIncident(activeDomain);
      router.push(`/triage/${incident.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create incident');
      setCreating(false);
    }
  }

  if (loading) {
    return (
      <div style={{ padding: '32px', maxWidth: '900px', margin: '0 auto' }}>
        <p>Loading...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ padding: '32px', maxWidth: '900px', margin: '0 auto' }}>
        <p style={{ color: 'red' }}>Error: {error}</p>
      </div>
    );
  }

  return (
    <div style={{ padding: '32px', maxWidth: '900px', margin: '0 auto' }}>
      <HeroBanner />

      <DomainTabs
        domains={domains}
        activeDomain={activeDomain}
        onDomainChange={setActiveDomain}
      />

      {activeDomain && (
        <>
          <div style={{
            padding: '24px',
            border: '1px solid #ddd',
            borderRadius: '8px',
            background: '#fafafa',
            marginBottom: '24px',
          }}>
            <h2 style={{ fontSize: '18px', fontWeight: 'bold', marginBottom: '12px' }}>
              {activeDomain.charAt(0).toUpperCase() + activeDomain.slice(1)} Triage
            </h2>
            <p style={{ color: '#666', marginBottom: '16px' }}>
              {activeDomain === 'medical' && 'Start a new medical triage incident to begin the assessment process. You can describe symptoms via text chat or voice recording.'}
              {activeDomain === 'sre' && 'Start a new SRE incident to triage infrastructure and service issues.'}
              {activeDomain === 'crypto' && 'Start a new crypto incident to assess DeFi and blockchain-related concerns.'}
            </p>
            <button
              onClick={handleStartIncident}
              disabled={creating || !domains.find(d => d.name === activeDomain)?.active}
              style={{
                padding: '12px 24px',
                background: '#333',
                color: '#fff',
                border: 'none',
                borderRadius: '6px',
                cursor: creating || !domains.find(d => d.name === activeDomain)?.active ? 'not-allowed' : 'pointer',
                opacity: creating || !domains.find(d => d.name === activeDomain)?.active ? 0.5 : 1,
                fontWeight: 'bold',
                fontSize: '14px',
              }}
            >
              {creating ? 'Creating...' : !domains.find(d => d.name === activeDomain)?.active ? 'Coming Soon' : 'Start New Incident'}
            </button>
          </div>

          <IncidentsList domain={activeDomain} />
        </>
      )}
    </div>
  );
}
