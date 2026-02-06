'use client';

import type { Domain } from '@/lib/types';

interface DomainTabsProps {
  domains: Domain[];
  activeDomain: string;
  onDomainChange: (domain: string) => void;
}

export function DomainTabs({ domains, activeDomain, onDomainChange }: DomainTabsProps) {
  return (
    <div style={{ display: 'flex', gap: '8px', marginBottom: '24px' }}>
      {domains.map((domain) => (
        <button
          key={domain.name}
          onClick={() => domain.active && onDomainChange(domain.name)}
          disabled={!domain.active}
          style={{
            padding: '8px 16px',
            border: '1px solid #333',
            borderRadius: '4px',
            background: activeDomain === domain.name ? '#333' : 'transparent',
            color: !domain.active
              ? '#999'
              : activeDomain === domain.name
                ? '#fff'
                : '#333',
            cursor: domain.active ? 'pointer' : 'not-allowed',
            fontWeight: activeDomain === domain.name ? 'bold' : 'normal',
            opacity: domain.active ? 1 : 0.5,
          }}
        >
          {domain.name.charAt(0).toUpperCase() + domain.name.slice(1)}
          {!domain.active && ' (Coming soon)'}
        </button>
      ))}
    </div>
  );
}
