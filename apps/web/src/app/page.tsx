'use client';

import Link from 'next/link';

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

function HowItWorks() {
  return (
    <div style={{
      padding: '24px',
      background: '#f8f9fa',
      borderRadius: '12px',
      border: '1px solid #e9ecef',
      marginBottom: '24px',
    }}>
      <h2 style={{ fontSize: '18px', fontWeight: 'bold', marginBottom: '16px', color: '#333' }}>
        How It Works
      </h2>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px' }}>
        <div style={{ padding: '16px', background: '#fff', borderRadius: '8px', border: '1px solid #e0e0e0' }}>
          <div style={{ fontWeight: 'bold', marginBottom: '6px', color: '#c0392b' }}>1. Describe Symptoms</div>
          <p style={{ fontSize: '13px', color: '#666', margin: 0 }}>
            Chat or voice input. AI extracts symptoms, pain levels, and risk signals.
          </p>
        </div>
        <div style={{ padding: '16px', background: '#fff', borderRadius: '8px', border: '1px solid #e0e0e0' }}>
          <div style={{ fontWeight: 'bold', marginBottom: '6px', color: '#c0392b' }}>2. Risk Analysis</div>
          <p style={{ fontSize: '13px', color: '#666', margin: 0 }}>
            Each signal gets a conviction score. Thresholds trigger escalation.
          </p>
        </div>
        <div style={{ padding: '16px', background: '#fff', borderRadius: '8px', border: '1px solid #e0e0e0' }}>
          <div style={{ fontWeight: 'bold', marginBottom: '6px', color: '#c0392b' }}>3. ESI Classification</div>
          <p style={{ fontSize: '13px', color: '#666', margin: 0 }}>
            Deterministic rules assign ESI 1-5. No LLM decides escalation.
          </p>
        </div>
        <div style={{ padding: '16px', background: '#fff', borderRadius: '8px', border: '1px solid #e0e0e0' }}>
          <div style={{ fontWeight: 'bold', marginBottom: '6px', color: '#c0392b' }}>4. Audit Trail</div>
          <p style={{ fontSize: '13px', color: '#666', margin: 0 }}>
            Every step logged. Full explainability for all decisions.
          </p>
        </div>
      </div>
    </div>
  );
}

export default function HomePage() {
  return (
    <div style={{ padding: '32px', maxWidth: '900px', margin: '0 auto' }}>
      <HeroBanner />
      <HowItWorks />

      <div style={{ textAlign: 'center' }}>
        <Link
          href="/triage"
          style={{
            display: 'inline-block',
            padding: '14px 28px',
            background: 'linear-gradient(135deg, #c0392b 0%, #e74c3c 100%)',
            color: '#fff',
            borderRadius: '8px',
            textDecoration: 'none',
            fontWeight: 'bold',
            fontSize: '15px',
          }}
        >
          Open Triage Dashboard
        </Link>
      </div>
    </div>
  );
}
