import type {
  DomainsResponse,
  Incident,
  MessageWithAssessmentResponse,
  TimelineResponse,
  VoiceResponse,
} from './types';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';

export async function fetchDomains(): Promise<DomainsResponse> {
  const res = await fetch(`${API_BASE}/api/triage/domains`);
  if (!res.ok) {
    throw new Error(`Failed to fetch domains: ${res.status}`);
  }
  return res.json();
}

export async function createIncident(domain: string, mode: string = 'B'): Promise<Incident> {
  const res = await fetch(`${API_BASE}/api/triage/incidents`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ domain, mode }),
  });
  if (!res.ok) {
    throw new Error(`Failed to create incident: ${res.status}`);
  }
  return res.json();
}

export async function fetchIncident(id: string): Promise<Incident> {
  const res = await fetch(`${API_BASE}/api/triage/incidents/${id}`);
  if (!res.ok) {
    throw new Error(`Failed to fetch incident: ${res.status}`);
  }
  return res.json();
}

export async function sendMessage(incidentId: string, content: string): Promise<MessageWithAssessmentResponse> {
  const res = await fetch(`${API_BASE}/api/triage/incidents/${incidentId}/messages`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content }),
  });
  if (!res.ok) {
    throw new Error(`Failed to send message: ${res.status}`);
  }
  return res.json();
}

export async function fetchTimeline(incidentId: string): Promise<TimelineResponse> {
  const res = await fetch(`${API_BASE}/api/triage/incidents/${incidentId}/timeline`);
  if (!res.ok) {
    throw new Error(`Failed to fetch timeline: ${res.status}`);
  }
  return res.json();
}

export async function sendVoice(incidentId: string, audioBlob: Blob): Promise<VoiceResponse> {
  const formData = new FormData();
  formData.append('audio', audioBlob, 'recording.webm');

  const res = await fetch(`${API_BASE}/api/triage/incidents/${incidentId}/voice`, {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) {
    throw new Error(`Failed to send voice: ${res.status}`);
  }
  return res.json();
}
