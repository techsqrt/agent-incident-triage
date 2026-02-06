'use client';

import { useEffect, useState } from 'react';
import { fetchDomains } from '@/lib/api';
import type { Domain } from '@/lib/types';
import { DomainTabs } from '@/app/components/DomainTabs';

export default function TriagePage() {
  const [domains, setDomains] = useState<Domain[]>([]);
  const [activeDomain, setActiveDomain] = useState('medical');
  const [loading, setLoading] = useState(true);
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
      <h1 style={{ fontSize: '24px', fontWeight: 'bold', marginBottom: '8px' }}>
        Triage Dashboard
      </h1>
      <p style={{ color: '#666', marginBottom: '24px' }}>
        Select a domain to begin triage
      </p>

      <DomainTabs
        domains={domains}
        activeDomain={activeDomain}
        onDomainChange={setActiveDomain}
      />

      {activeDomain === 'medical' && (
        <div style={{
          padding: '24px',
          border: '1px solid #ddd',
          borderRadius: '8px',
          background: '#fafafa',
        }}>
          <h2 style={{ fontSize: '18px', fontWeight: 'bold', marginBottom: '12px' }}>
            Medical Triage
          </h2>
          <p style={{ color: '#666', marginBottom: '16px' }}>
            Start a new medical triage incident to begin the assessment process.
          </p>
          <p style={{ color: '#999', fontSize: '14px' }}>
            Chat and voice interfaces will be available after starting an incident.
          </p>
        </div>
      )}
    </div>
  );
}
