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
      padding: '28px',
      background: '#f8f9fa',
      borderRadius: '12px',
      border: '1px solid #e9ecef',
    }}>
      <h2 style={{ fontSize: '20px', fontWeight: 'bold', marginBottom: '24px', color: '#333' }}>
        How It Works
      </h2>

      {/* Pipeline Steps */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '20px', marginBottom: '28px' }}>
        <div style={{ padding: '20px', background: '#fff', borderRadius: '8px', border: '1px solid #e0e0e0' }}>
          <div style={{ fontWeight: 'bold', marginBottom: '10px', color: '#c0392b', fontSize: '15px' }}>1. Input &amp; Transcription</div>
          <p style={{ fontSize: '13px', color: '#666', margin: 0, lineHeight: 1.6 }}>
            Patient describes symptoms via <strong>text chat</strong> or <strong>voice recording</strong>.
            Voice input uses <code style={{ background: '#f0f0f0', padding: '2px 4px', borderRadius: '3px' }}>gpt-4o-transcribe</code> (Whisper)
            for speech-to-text conversion. Model is configurable per deployment.
          </p>
        </div>

        <div style={{ padding: '20px', background: '#fff', borderRadius: '8px', border: '1px solid #e0e0e0' }}>
          <div style={{ fontWeight: 'bold', marginBottom: '10px', color: '#c0392b', fontSize: '15px' }}>2. Medical Extraction</div>
          <p style={{ fontSize: '13px', color: '#666', margin: 0, lineHeight: 1.6 }}>
            <code style={{ background: '#f0f0f0', padding: '2px 4px', borderRadius: '3px' }}>gpt-4o</code> extracts structured data:
            symptoms, pain scale (0-10), mental status, vitals, and <strong>risk signals</strong> with
            conviction scores (0.0-1.0). Uses JSON schema validation for reliable output.
          </p>
        </div>

        <div style={{ padding: '20px', background: '#fff', borderRadius: '8px', border: '1px solid #e0e0e0' }}>
          <div style={{ fontWeight: 'bold', marginBottom: '10px', color: '#c0392b', fontSize: '15px' }}>3. Conviction-Based Escalation</div>
          <p style={{ fontSize: '13px', color: '#666', margin: 0, lineHeight: 1.6 }}>
            Each risk signal (chest pain, breathing issues, suicidal ideation) has a <strong>conviction score</strong>.
            Deterministic rules compare against thresholds. If <code style={{ background: '#f0f0f0', padding: '2px 4px', borderRadius: '3px' }}>conviction &gt;= threshold</code>,
            the flag triggers. No LLM decides escalation.
          </p>
        </div>

        <div style={{ padding: '20px', background: '#fff', borderRadius: '8px', border: '1px solid #e0e0e0' }}>
          <div style={{ fontWeight: 'bold', marginBottom: '10px', color: '#c0392b', fontSize: '15px' }}>4. ESI Classification</div>
          <p style={{ fontSize: '13px', color: '#666', margin: 0, lineHeight: 1.6 }}>
            <code style={{ background: '#f0f0f0', padding: '2px 4px', borderRadius: '3px' }}>rules.py</code> assigns
            Emergency Severity Index (ESI 1-5) based on red flags count, pain level, mental status.
            ESI-1/2 or any triggered risk flag → automatic escalation to human provider.
          </p>
        </div>

        <div style={{ padding: '20px', background: '#fff', borderRadius: '8px', border: '1px solid #e0e0e0' }}>
          <div style={{ fontWeight: 'bold', marginBottom: '10px', color: '#c0392b', fontSize: '15px' }}>5. Response Generation</div>
          <p style={{ fontSize: '13px', color: '#666', margin: 0, lineHeight: 1.6 }}>
            AI generates contextual follow-up questions or escalation message.
            For voice mode, <code style={{ background: '#f0f0f0', padding: '2px 4px', borderRadius: '3px' }}>gpt-4o-mini-tts</code> converts
            response to speech. Model choices configurable for cost/quality tradeoffs.
          </p>
        </div>

        <div style={{ padding: '20px', background: '#fff', borderRadius: '8px', border: '1px solid #e0e0e0' }}>
          <div style={{ fontWeight: 'bold', marginBottom: '10px', color: '#c0392b', fontSize: '15px' }}>6. Full Audit Trail</div>
          <p style={{ fontSize: '13px', color: '#666', margin: 0, lineHeight: 1.6 }}>
            Every step logged with <code style={{ background: '#f0f0f0', padding: '2px 4px', borderRadius: '3px' }}>TOOL_CALL</code> /
            <code style={{ background: '#f0f0f0', padding: '2px 4px', borderRadius: '3px' }}>TOOL_RESULT</code> pattern:
            model used, latency, token counts, human-readable explanations. Full explainability for compliance.
          </p>
        </div>
      </div>

      {/* Conviction Thresholds */}
      <div style={{ marginBottom: '24px' }}>
        <h3 style={{ fontSize: '15px', fontWeight: 'bold', marginBottom: '12px', color: '#555' }}>
          Risk Signal Thresholds
        </h3>
        <p style={{ fontSize: '13px', color: '#666', marginBottom: '12px' }}>
          Lower threshold = more sensitive (escalate with less certainty). Psychiatric signals use 20% to catch subtle hints.
        </p>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
          <span style={{ padding: '6px 12px', background: '#c0392b', color: '#fff', borderRadius: '4px', fontSize: '12px' }}>
            Suicidal Ideation: 20%
          </span>
          <span style={{ padding: '6px 12px', background: '#c0392b', color: '#fff', borderRadius: '4px', fontSize: '12px' }}>
            Self-Harm: 20%
          </span>
          <span style={{ padding: '6px 12px', background: '#e67e22', color: '#fff', borderRadius: '4px', fontSize: '12px' }}>
            Homicidal: 40%
          </span>
          <span style={{ padding: '6px 12px', background: '#f39c12', color: '#fff', borderRadius: '4px', fontSize: '12px' }}>
            Chest Pain: 50%
          </span>
          <span style={{ padding: '6px 12px', background: '#f39c12', color: '#fff', borderRadius: '4px', fontSize: '12px' }}>
            Breathing: 50%
          </span>
          <span style={{ padding: '6px 12px', background: '#f39c12', color: '#fff', borderRadius: '4px', fontSize: '12px' }}>
            Neurological: 50%
          </span>
          <span style={{ padding: '6px 12px', background: '#f39c12', color: '#fff', borderRadius: '4px', fontSize: '12px' }}>
            Bleeding: 50%
          </span>
        </div>
      </div>

      {/* Architecture Note */}
      <div style={{ padding: '16px', background: '#fff3cd', borderRadius: '8px', border: '1px solid #ffc107' }}>
        <p style={{ fontSize: '13px', color: '#856404', margin: 0 }}>
          <strong>Safety-First Architecture:</strong> The LLM is treated as an &quot;untrusted helper&quot; —
          it extracts information and generates responses, but all safety-critical escalation decisions
          are made by deterministic rules with explicit thresholds. This prevents prompt injection from
          bypassing medical safety checks.
        </p>
      </div>
    </div>
  );
}

export default function HomePage() {
  return (
    <div style={{ padding: '32px', maxWidth: '900px', margin: '0 auto' }}>
      <HeroBanner />

      <div style={{ textAlign: 'center', marginBottom: '32px' }}>
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

      <HowItWorks />
    </div>
  );
}
