'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { fetchDomains, createIncident } from '@/lib/api';
import type { Domain } from '@/lib/types';
import { DomainTabs } from '@/app/components/DomainTabs';
import { IncidentsList } from '@/app/components/IncidentsList';

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
