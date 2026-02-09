import type {
  DomainsResponse,
  Incident,
  IncidentListResponse,
  MessageWithAssessmentResponse,
  TimelineResponse,
  VoiceResponse,
} from './types';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';

async function throwApiError(res: Response, fallback: string): Promise<never> {
  try {
    const body = await res.json();
    throw new Error(body.detail || fallback);
  } catch (err) {
    if (err instanceof Error && err.message !== fallback) throw err;
    throw new Error(fallback);
  }
}

export async function fetchDomains(): Promise<DomainsResponse> {
  const res = await fetch(`${API_BASE}/api/triage/domains`);
  if (!res.ok) {
    await throwApiError(res, `Failed to fetch domains: ${res.status}`);
  }
  return res.json();
}

export interface FetchIncidentsParams {
  domain?: string;
  status?: string;
  limit?: number;
  offset?: number;
}

export async function fetchIncidents(params: FetchIncidentsParams = {}): Promise<IncidentListResponse> {
  const searchParams = new URLSearchParams();
  if (params.domain) searchParams.set('domain', params.domain);
  if (params.status) searchParams.set('status', params.status);
  if (params.limit) searchParams.set('limit', params.limit.toString());
  if (params.offset) searchParams.set('offset', params.offset.toString());

  const queryString = searchParams.toString();
  const url = `${API_BASE}/api/triage/incidents${queryString ? `?${queryString}` : ''}`;

  const res = await fetch(url);
  if (!res.ok) {
    await throwApiError(res, `Failed to fetch incidents: ${res.status}`);
  }
  return res.json();
}

export async function checkRecaptchaStatus(): Promise<{ verified: boolean; required: boolean }> {
  const res = await fetch(`${API_BASE}/api/triage/recaptcha/status`);
  if (!res.ok) {
    // If check fails, assume verification is required
    return { verified: false, required: true };
  }
  return res.json();
}

export async function createIncident(domain: string, mode: string = 'chat'): Promise<Incident> {
  const res = await fetch(`${API_BASE}/api/triage/incidents`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ domain, mode }),
  });
  if (!res.ok) {
    await throwApiError(res, `Failed to create incident: ${res.status}`);
  }
  return res.json();
}

export async function fetchIncident(id: string): Promise<Incident> {
  const res = await fetch(`${API_BASE}/api/triage/incidents/${id}`);
  if (!res.ok) {
    await throwApiError(res, `Failed to fetch incident: ${res.status}`);
  }
  return res.json();
}

export async function sendMessage(incidentId: string, content: string, recaptchaToken?: string): Promise<MessageWithAssessmentResponse> {
  const res = await fetch(`${API_BASE}/api/triage/incidents/${incidentId}/messages`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content, recaptcha_token: recaptchaToken }),
  });
  if (!res.ok) {
    await throwApiError(res, `Failed to send message: ${res.status}`);
  }
  return res.json();
}

export async function fetchTimeline(incidentId: string): Promise<TimelineResponse> {
  const res = await fetch(`${API_BASE}/api/triage/incidents/${incidentId}/timeline`);
  if (!res.ok) {
    await throwApiError(res, `Failed to fetch timeline: ${res.status}`);
  }
  return res.json();
}

export async function sendVoice(incidentId: string, audioBlob: Blob, recaptchaToken?: string): Promise<VoiceResponse> {
  const formData = new FormData();
  formData.append('audio', audioBlob, 'recording.webm');
  if (recaptchaToken) {
    formData.append('recaptcha_token', recaptchaToken);
  }

  const res = await fetch(`${API_BASE}/api/triage/incidents/${incidentId}/voice`, {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) {
    await throwApiError(res, `Failed to send voice: ${res.status}`);
  }
  return res.json();
}

export async function closeIncident(incidentId: string): Promise<Incident> {
  const res = await fetch(`${API_BASE}/api/triage/incidents/${incidentId}/close`, {
    method: 'POST',
  });
  if (!res.ok) {
    await throwApiError(res, `Failed to close incident: ${res.status}`);
  }
  return res.json();
}

export async function reopenIncident(incidentId: string): Promise<Incident> {
  const res = await fetch(`${API_BASE}/api/triage/incidents/${incidentId}/reopen`, {
    method: 'POST',
  });
  if (!res.ok) {
    await throwApiError(res, `Failed to reopen incident: ${res.status}`);
  }
  return res.json();
}
