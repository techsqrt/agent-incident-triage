export interface Domain {
  name: string;
  active: boolean;
}

export interface DomainsResponse {
  domains: Domain[];
}

export type SeverityType = 'UNASSIGNED' | 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | 'RESOLVED';

export interface Incident {
  id: string;
  domain: string;
  status: string;
  mode: string;
  severity: SeverityType;
  created_at: string;
  updated_at: string;
}

export interface Message {
  id: string;
  incident_id: string;
  role: string;
  content_text: string;
  created_at: string;
}

export interface AuditEvent {
  id: string;
  incident_id: string;
  trace_id: string;
  step: string;
  payload_json: Record<string, unknown>;
  latency_ms: number | null;
  model_used: string | null;
  token_usage_json: Record<string, unknown> | null;
  created_at: string;
}

export interface Assessment {
  id: string;
  incident_id: string;
  domain: string;
  result_json: Record<string, unknown>;
  created_at: string;
}

export interface TimelineResponse {
  incident_id: string;
  events: AuditEvent[];
}

export interface VoiceResponse {
  transcript: string;
  response_text: string;
  audio_base64: string | null;
  assessment: Assessment | null;
}

export interface MessageWithAssessmentResponse {
  message: Message;
  assistant_message: Message;
  assessment: Assessment | null;
}

export interface IncidentListResponse {
  incidents: Incident[];
  total: number;
}
