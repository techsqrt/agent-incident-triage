import { describe, it, expect, vi, beforeEach } from 'vitest';
import { fetchDomains } from './api';

const mockFetch = vi.fn();
global.fetch = mockFetch;

beforeEach(() => {
  mockFetch.mockReset();
});

describe('fetchDomains', () => {
  it('returns domains list on success', async () => {
    const mockData = {
      domains: [
        { name: 'medical', active: true },
        { name: 'sre', active: false },
        { name: 'crypto', active: false },
      ],
    };
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(mockData),
    });

    const result = await fetchDomains();
    expect(result.domains).toHaveLength(3);
    expect(result.domains[0].name).toBe('medical');
    expect(result.domains[0].active).toBe(true);
  });

  it('throws on non-ok response', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 500,
    });

    await expect(fetchDomains()).rejects.toThrow('Failed to fetch domains: 500');
  });
});
