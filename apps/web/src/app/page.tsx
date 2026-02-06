'use client';

import Link from 'next/link';

export default function HomePage() {
  return (
    <div style={{ padding: '32px', maxWidth: '800px', margin: '0 auto' }}>
      <h1 style={{ fontSize: '28px', fontWeight: 'bold', marginBottom: '8px' }}>
        Agent Incident Triage
      </h1>
      <p style={{ color: '#666', marginBottom: '32px' }}>
        Modular incident triage agent pipeline
      </p>

      <Link
        href="/triage"
        style={{
          display: 'inline-block',
          padding: '12px 24px',
          background: '#333',
          color: '#fff',
          borderRadius: '6px',
          textDecoration: 'none',
          fontWeight: 'bold',
        }}
      >
        Open Triage Dashboard
      </Link>
    </div>
  );
}
