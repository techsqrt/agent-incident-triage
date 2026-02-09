'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { fetchIncidents } from '@/lib/api';
import type { Incident } from '@/lib/types';

interface IncidentsListProps {
  domain: string;
}

const STATUS_OPTIONS = ['All', 'OPEN', 'TRIAGE_READY', 'ESCALATED', 'CLOSED'];
const STATUS_COLORS: Record<string, string> = {
  OPEN: '#27ae60',
  TRIAGE_READY: '#f39c12',
  ESCALATED: '#c0392b',
  CLOSED: '#7f8c8d',
};
const PAGE_SIZE = 10;

export function IncidentsList({ domain }: IncidentsListProps) {
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [total, setTotal] = useState(0);
  const [status, setStatus] = useState('All');
  const [page, setPage] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setPage(0);
  }, [domain, status]);

  useEffect(() => {
    loadIncidents();
  }, [domain, status, page]);

  async function loadIncidents() {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchIncidents({
        domain,
        status: status === 'All' ? undefined : status,
        limit: PAGE_SIZE,
        offset: page * PAGE_SIZE,
      });
      setIncidents(res.incidents);
      setTotal(res.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load incidents');
    } finally {
      setLoading(false);
    }
  }

  const totalPages = Math.ceil(total / PAGE_SIZE);

  function formatDate(dateStr: string) {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
        <h3 style={{ fontSize: '16px', fontWeight: 'bold', margin: 0 }}>
          Recent Incidents
        </h3>
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          <span style={{ fontSize: '13px', color: '#666' }}>Filter:</span>
          <select
            value={status}
            onChange={(e) => setStatus(e.target.value)}
            style={{
              padding: '6px 12px',
              border: '1px solid #ccc',
              borderRadius: '4px',
              fontSize: '13px',
              background: '#fff',
              cursor: 'pointer',
            }}
          >
            {STATUS_OPTIONS.map((opt) => (
              <option key={opt} value={opt}>
                {opt === 'All' ? 'All Status' : opt}
              </option>
            ))}
          </select>
        </div>
      </div>

      {error && (
        <div style={{ padding: '12px', background: '#fee', border: '1px solid #fcc', borderRadius: '6px', color: '#c00', marginBottom: '12px' }}>
          {error}
        </div>
      )}

      {loading ? (
        <div style={{ padding: '24px', textAlign: 'center', color: '#666' }}>
          Loading incidents...
        </div>
      ) : incidents.length === 0 ? (
        <div style={{ padding: '24px', textAlign: 'center', color: '#999', background: '#fafafa', borderRadius: '8px' }}>
          No incidents found for {domain} domain
          {status !== 'All' && ` with status ${status}`}.
        </div>
      ) : (
        <>
          <div style={{ border: '1px solid #e0e0e0', borderRadius: '8px', overflow: 'hidden' }}>
            {incidents.map((incident, idx) => (
              <Link
                key={incident.id}
                href={`/triage/${incident.id}`}
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  padding: '12px 16px',
                  background: idx % 2 === 0 ? '#fff' : '#fafafa',
                  borderBottom: idx < incidents.length - 1 ? '1px solid #e0e0e0' : 'none',
                  textDecoration: 'none',
                  color: 'inherit',
                  transition: 'background 0.15s',
                }}
                onMouseEnter={(e) => (e.currentTarget.style.background = '#f0f0f0')}
                onMouseLeave={(e) => (e.currentTarget.style.background = idx % 2 === 0 ? '#fff' : '#fafafa')}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                  <code style={{ fontSize: '13px', color: '#666', background: '#f5f5f5', padding: '2px 6px', borderRadius: '4px' }}>
                    {incident.id.slice(0, 8)}
                  </code>
                  <span
                    style={{
                      fontSize: '12px',
                      fontWeight: 'bold',
                      color: '#fff',
                      background: STATUS_COLORS[incident.status] || '#999',
                      padding: '2px 8px',
                      borderRadius: '4px',
                    }}
                  >
                    {incident.status}
                  </span>
                  <span style={{ fontSize: '12px', color: '#888', textTransform: 'uppercase' }}>
                    {incident.mode}
                  </span>
                </div>
                <div style={{ fontSize: '12px', color: '#888' }}>
                  {formatDate(incident.created_at)}
                </div>
              </Link>
            ))}
          </div>

          {totalPages > 1 && (
            <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '16px', marginTop: '16px' }}>
              <button
                onClick={() => setPage((p) => Math.max(0, p - 1))}
                disabled={page === 0}
                style={{
                  padding: '6px 14px',
                  border: '1px solid #ccc',
                  borderRadius: '4px',
                  background: page === 0 ? '#f5f5f5' : '#fff',
                  color: page === 0 ? '#999' : '#333',
                  cursor: page === 0 ? 'not-allowed' : 'pointer',
                  fontSize: '13px',
                }}
              >
                Previous
              </button>
              <span style={{ fontSize: '13px', color: '#666' }}>
                Page {page + 1} of {totalPages}
              </span>
              <button
                onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
                disabled={page >= totalPages - 1}
                style={{
                  padding: '6px 14px',
                  border: '1px solid #ccc',
                  borderRadius: '4px',
                  background: page >= totalPages - 1 ? '#f5f5f5' : '#fff',
                  color: page >= totalPages - 1 ? '#999' : '#333',
                  cursor: page >= totalPages - 1 ? 'not-allowed' : 'pointer',
                  fontSize: '13px',
                }}
              >
                Next
              </button>
            </div>
          )}

          <div style={{ textAlign: 'center', marginTop: '8px', fontSize: '12px', color: '#999' }}>
            Showing {page * PAGE_SIZE + 1}-{Math.min((page + 1) * PAGE_SIZE, total)} of {total} incidents
          </div>
        </>
      )}
    </div>
  );
}
