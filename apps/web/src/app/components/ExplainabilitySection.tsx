'use client';

import { useEffect, useState } from 'react';
import { fetchTimeline } from '@/lib/api';
import type { AuditEvent, Assessment, Incident, HistoryInteraction } from '@/lib/types';

interface ExplainabilitySectionProps {
  incidentId: string;
  incident: Incident | null;
  assessment: Assessment | null;
}

interface StepInfo {
  emoji: string;
  title: string;
  description: string;
}

const STEP_EXPLANATIONS: Record<string, StepInfo> = {
  STT: {
    emoji: '🎤',
    title: 'Voice Recognition',
    description: 'Your voice recording was converted to text so our system could understand what you said.',
  },
  EXTRACT: {
    emoji: '📋',
    title: 'Information Gathering',
    description: 'We analyzed your message to identify key health information like symptoms, pain level, and relevant history.',
  },
  TRIAGE_RULES: {
    emoji: '⚖️',
    title: 'Safety Assessment',
    description: 'Your symptoms were checked against medical guidelines to determine urgency level.',
  },
  GENERATE: {
    emoji: '💬',
    title: 'Response Preparation',
    description: 'A helpful response was prepared based on the assessment.',
  },
  RESPONSE_GENERATED: {
    emoji: '✅',
    title: 'Response Ready',
    description: 'The assessment and response are now complete.',
  },
  TTS: {
    emoji: '🔊',
    title: 'Voice Response',
    description: 'The response was converted to speech for you to hear.',
  },
};

interface AcuityInfo {
  emoji: string;
  label: string;
  color: string;
  description: string;
}

const ACUITY_INFO: Record<number, AcuityInfo> = {
  1: {
    emoji: '🚨',
    label: 'Immediate',
    color: '#c0392b',
    description: 'This requires immediate medical attention. Please seek emergency care right away.',
  },
  2: {
    emoji: '⚠️',
    label: 'Emergent',
    color: '#e67e22',
    description: 'This is a high-priority situation that needs prompt medical attention.',
  },
  3: {
    emoji: '🔶',
    label: 'Urgent',
    color: '#f39c12',
    description: 'This needs medical evaluation soon, but is not immediately life-threatening.',
  },
  4: {
    emoji: '🟢',
    label: 'Less Urgent',
    color: '#27ae60',
    description: 'This can be addressed during normal medical hours or with home care.',
  },
  5: {
    emoji: '✅',
    label: 'Non-Urgent',
    color: '#2ecc71',
    description: 'This appears to be a minor concern that can be managed with self-care.',
  },
};

function humanizeFlagName(name: string): string {
  const mapping: Record<string, string> = {
    chest_pain: 'Chest Pain',
    chest_pain_with_sob: 'Chest Pain with Breathing Difficulty',
    altered_mental_status: 'Change in Mental Awareness',
    tachycardia: 'Rapid Heart Rate',
    bradycardia: 'Slow Heart Rate',
    hypoxia: 'Low Oxygen Level',
    high_fever: 'High Fever',
    hypotension: 'Low Blood Pressure',
    severe_pain: 'Severe Pain',
    difficulty_breathing: 'Difficulty Breathing',
    loss_of_consciousness: 'Loss of Consciousness',
    stroke_symptoms: 'Possible Stroke Symptoms',
    allergic_reaction: 'Allergic Reaction',
    bleeding: 'Significant Bleeding',
    poisoning: 'Possible Poisoning',
    trauma: 'Significant Injury',
    pediatric_emergency: 'Pediatric Emergency',
    pregnancy_emergency: 'Pregnancy Emergency',
  };
  return mapping[name] || name.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

const SEVERITY_COLORS: Record<string, string> = {
  CRITICAL: '#c0392b',
  HIGH: '#e67e22',
  MEDIUM: '#f39c12',
  LOW: '#27ae60',
  UNASSIGNED: '#7f8c8d',
  RESOLVED: '#2ecc71',
};

export function ExplainabilitySection({ incidentId, incident, assessment }: ExplainabilitySectionProps) {
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState(false);

  useEffect(() => {
    fetchTimeline(incidentId)
      .then((res) => setEvents(res.events))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [incidentId]);

  const history = incident?.history?.interactions || [];

  // Only show if we have events, history, or assessment
  if (loading) {
    return null;
  }

  if (events.length === 0 && history.length === 0 && !assessment) {
    return null;
  }

  // Get latest assessment from history if available
  const latestAssessmentFromHistory = history.findLast((i: HistoryInteraction) => i.type === 'assessment') as HistoryInteraction | undefined;
  const acuity = (assessment?.result_json?.acuity ?? latestAssessmentFromHistory?.acuity) as number | undefined;
  const escalate = (assessment?.result_json?.escalate ?? latestAssessmentFromHistory?.escalate) as boolean | undefined;
  const redFlags = ((assessment?.result_json?.red_flags ?? latestAssessmentFromHistory?.red_flags) || []) as Array<{ name: string; reason: string }>;
  const summary = assessment?.result_json?.summary as string | undefined;
  const disposition = (assessment?.result_json?.disposition ?? latestAssessmentFromHistory?.disposition) as string | undefined;
  const severity = (incident?.severity ?? latestAssessmentFromHistory?.severity) as string | undefined;

  const acuityInfo = acuity ? ACUITY_INFO[acuity] : null;

  // Group events by trace_id for cleaner display
  const uniqueSteps = events.reduce<AuditEvent[]>((acc, event) => {
    if (!acc.find((e) => e.step === event.step)) {
      acc.push(event);
    }
    return acc;
  }, []);

  return (
    <div
      style={{
        marginTop: '32px',
        padding: '24px',
        background: 'linear-gradient(135deg, #f8f9fa 0%, #fff 100%)',
        borderRadius: '12px',
        border: '1px solid #e9ecef',
      }}
    >
      <div
        onClick={() => setExpanded(!expanded)}
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          cursor: 'pointer',
        }}
      >
        <h2 style={{ fontSize: '18px', fontWeight: 'bold', margin: 0, color: '#333' }}>
          🔍 Agent Escalation Process Explained
        </h2>
        <span style={{ fontSize: '20px', color: '#666' }}>{expanded ? '▲' : '▼'}</span>
      </div>

      <p style={{ color: '#666', fontSize: '14px', marginTop: '8px', marginBottom: expanded ? '20px' : '0' }}>
        See how we analyzed your case step by step
      </p>

      {expanded && (
        <>
          {/* Process Steps */}
          {uniqueSteps.length > 0 && (
            <div style={{ marginBottom: '24px' }}>
              <h3 style={{ fontSize: '15px', fontWeight: 'bold', color: '#555', marginBottom: '12px' }}>
                📊 What Happened Behind the Scenes
              </h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {uniqueSteps.map((event, idx) => {
                  const info = STEP_EXPLANATIONS[event.step];
                  return (
                    <div
                      key={event.id}
                      style={{
                        display: 'flex',
                        alignItems: 'flex-start',
                        gap: '12px',
                        padding: '12px 16px',
                        background: '#fff',
                        borderRadius: '8px',
                        border: '1px solid #e0e0e0',
                      }}
                    >
                      <span style={{ fontSize: '24px', lineHeight: 1 }}>{info?.emoji || '📌'}</span>
                      <div style={{ flex: 1 }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                          <strong style={{ fontSize: '14px', color: '#333' }}>
                            {info?.title || event.step}
                          </strong>
                          {event.latency_ms && (
                            <span
                              style={{
                                fontSize: '11px',
                                color: '#888',
                                background: '#f0f0f0',
                                padding: '2px 6px',
                                borderRadius: '4px',
                              }}
                            >
                              {event.latency_ms}ms
                            </span>
                          )}
                        </div>
                        <p style={{ color: '#666', fontSize: '13px', margin: 0 }}>
                          {info?.description || 'Processing step completed.'}
                        </p>
                      </div>
                      <span style={{ fontSize: '12px', color: '#aaa' }}>Step {idx + 1}</span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Severity Badge */}
          {severity && severity !== 'UNASSIGNED' && (
            <div style={{ marginBottom: '24px' }}>
              <h3 style={{ fontSize: '15px', fontWeight: 'bold', color: '#555', marginBottom: '12px' }}>
                🏥 Triage Severity
              </h3>
              <div
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '8px',
                  padding: '10px 20px',
                  background: `${SEVERITY_COLORS[severity] || '#7f8c8d'}15`,
                  borderRadius: '8px',
                  border: `2px solid ${SEVERITY_COLORS[severity] || '#7f8c8d'}`,
                }}
              >
                <span style={{ fontSize: '18px', fontWeight: 'bold', color: SEVERITY_COLORS[severity] || '#7f8c8d' }}>
                  {severity}
                </span>
              </div>
            </div>
          )}

          {/* Urgency Level */}
          {acuityInfo && (
            <div style={{ marginBottom: '24px' }}>
              <h3 style={{ fontSize: '15px', fontWeight: 'bold', color: '#555', marginBottom: '12px' }}>
                🎯 Urgency Assessment
              </h3>
              <div
                style={{
                  padding: '16px 20px',
                  background: `${acuityInfo.color}10`,
                  borderRadius: '10px',
                  borderLeft: `5px solid ${acuityInfo.color}`,
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
                  <span style={{ fontSize: '28px' }}>{acuityInfo.emoji}</span>
                  <span
                    style={{
                      fontSize: '18px',
                      fontWeight: 'bold',
                      color: acuityInfo.color,
                    }}
                  >
                    {acuityInfo.label} (Level {acuity})
                  </span>
                  {escalate && (
                    <span
                      style={{
                        fontSize: '12px',
                        fontWeight: 'bold',
                        color: '#fff',
                        background: '#c0392b',
                        padding: '3px 10px',
                        borderRadius: '12px',
                      }}
                    >
                      ESCALATED
                    </span>
                  )}
                </div>
                <p style={{ color: '#555', margin: 0, fontSize: '14px' }}>{acuityInfo.description}</p>
              </div>
            </div>
          )}

          {/* Conversation History */}
          {history.length > 0 && (
            <div style={{ marginBottom: '24px' }}>
              <h3 style={{ fontSize: '15px', fontWeight: 'bold', color: '#555', marginBottom: '12px' }}>
                💬 Conversation History
              </h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {history.map((interaction: HistoryInteraction, idx: number) => {
                  const ts = new Date(interaction.ts).toLocaleString();
                  if (interaction.type === 'user_message') {
                    return (
                      <div
                        key={idx}
                        style={{
                          padding: '12px 16px',
                          background: '#e3f2fd',
                          borderRadius: '8px',
                          borderLeft: '4px solid #2196f3',
                        }}
                      >
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                          <strong style={{ color: '#1976d2', fontSize: '13px' }}>👤 Patient</strong>
                          <span style={{ color: '#888', fontSize: '11px' }}>{ts}</span>
                        </div>
                        <p style={{ color: '#333', margin: 0, fontSize: '14px' }}>{interaction.content as string}</p>
                      </div>
                    );
                  }
                  if (interaction.type === 'assistant_message') {
                    return (
                      <div
                        key={idx}
                        style={{
                          padding: '12px 16px',
                          background: '#f3e5f5',
                          borderRadius: '8px',
                          borderLeft: '4px solid #9c27b0',
                        }}
                      >
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                          <strong style={{ color: '#7b1fa2', fontSize: '13px' }}>🤖 Assistant</strong>
                          <span style={{ color: '#888', fontSize: '11px' }}>{ts}</span>
                        </div>
                        <p style={{ color: '#333', margin: 0, fontSize: '14px' }}>{interaction.content as string}</p>
                      </div>
                    );
                  }
                  if (interaction.type === 'assessment') {
                    const assessSeverity = interaction.severity as string;
                    return (
                      <div
                        key={idx}
                        style={{
                          padding: '12px 16px',
                          background: '#fff3e0',
                          borderRadius: '8px',
                          borderLeft: `4px solid ${SEVERITY_COLORS[assessSeverity] || '#f57c00'}`,
                        }}
                      >
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                          <strong style={{ color: '#e65100', fontSize: '13px' }}>📊 Assessment</strong>
                          <span style={{ color: '#888', fontSize: '11px' }}>{ts}</span>
                        </div>
                        <p style={{ color: '#333', margin: 0, fontSize: '13px' }}>
                          Acuity: <strong>ESI-{interaction.acuity as number}</strong> |
                          Severity: <strong style={{ color: SEVERITY_COLORS[assessSeverity] }}>{assessSeverity}</strong> |
                          Disposition: <strong>{interaction.disposition as string}</strong>
                          {interaction.escalate && <span style={{ color: '#c0392b', marginLeft: '8px' }}>⚠️ ESCALATED</span>}
                        </p>
                      </div>
                    );
                  }
                  if (interaction.type === 'system_created') {
                    return (
                      <div
                        key={idx}
                        style={{
                          padding: '8px 16px',
                          background: '#f5f5f5',
                          borderRadius: '8px',
                          borderLeft: '4px solid #9e9e9e',
                        }}
                      >
                        <span style={{ color: '#666', fontSize: '12px' }}>
                          📝 Incident created | {ts}
                        </span>
                      </div>
                    );
                  }
                  // Status changes
                  if (interaction.type?.startsWith('status_changed') || interaction.type?.startsWith('incident_')) {
                    return (
                      <div
                        key={idx}
                        style={{
                          padding: '8px 16px',
                          background: '#e8f5e9',
                          borderRadius: '8px',
                          borderLeft: '4px solid #4caf50',
                        }}
                      >
                        <span style={{ color: '#2e7d32', fontSize: '12px' }}>
                          🔄 {interaction.type.replace(/_/g, ' ')} | {ts}
                        </span>
                      </div>
                    );
                  }
                  return null;
                })}
              </div>
            </div>
          )}

          {/* Summary */}
          {summary && (
            <div style={{ marginBottom: '24px' }}>
              <h3 style={{ fontSize: '15px', fontWeight: 'bold', color: '#555', marginBottom: '12px' }}>
                📝 Assessment Summary
              </h3>
              <div
                style={{
                  padding: '16px',
                  background: '#fff',
                  borderRadius: '8px',
                  border: '1px solid #e0e0e0',
                }}
              >
                <p style={{ color: '#444', margin: 0, fontSize: '14px', lineHeight: 1.6 }}>{summary}</p>
              </div>
            </div>
          )}

          {/* Red Flags */}
          {redFlags.length > 0 && (
            <div style={{ marginBottom: '24px' }}>
              <h3 style={{ fontSize: '15px', fontWeight: 'bold', color: '#c0392b', marginBottom: '12px' }}>
                ⚠️ Important Findings
              </h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {redFlags.map((flag, i) => (
                  <div
                    key={i}
                    style={{
                      padding: '12px 16px',
                      background: '#fff5f5',
                      borderRadius: '8px',
                      border: '1px solid #fed7d7',
                    }}
                  >
                    <strong style={{ color: '#c0392b', fontSize: '14px' }}>
                      {humanizeFlagName(flag.name)}
                    </strong>
                    {flag.reason && (
                      <p style={{ color: '#666', margin: '4px 0 0', fontSize: '13px' }}>{flag.reason}</p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Disposition / Next Steps */}
          {disposition && (
            <div>
              <h3 style={{ fontSize: '15px', fontWeight: 'bold', color: '#555', marginBottom: '12px' }}>
                ➡️ Recommended Next Step
              </h3>
              <div
                style={{
                  padding: '16px',
                  background: disposition === 'escalate' ? '#fff5f5' : '#f0fff4',
                  borderRadius: '8px',
                  border: `1px solid ${disposition === 'escalate' ? '#fed7d7' : '#c6f6d5'}`,
                  display: 'flex',
                  alignItems: 'center',
                  gap: '12px',
                }}
              >
                <span style={{ fontSize: '24px' }}>
                  {disposition === 'escalate' ? '🏥' : disposition === 'continue' ? '💬' : '✅'}
                </span>
                <div>
                  <strong style={{ fontSize: '14px', color: '#333' }}>
                    {disposition === 'escalate' && 'Seek Professional Care'}
                    {disposition === 'continue' && 'Continue Assessment'}
                    {disposition === 'resolve' && 'Self-Care Recommended'}
                    {!['escalate', 'continue', 'resolve'].includes(disposition) &&
                      disposition.charAt(0).toUpperCase() + disposition.slice(1)}
                  </strong>
                  <p style={{ color: '#666', margin: '4px 0 0', fontSize: '13px' }}>
                    {disposition === 'escalate' &&
                      'Based on the symptoms described, we recommend speaking with a healthcare professional.'}
                    {disposition === 'continue' &&
                      'We may need more information to complete the assessment.'}
                    {disposition === 'resolve' &&
                      'Your symptoms suggest self-care measures may be appropriate.'}
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Footer */}
          <div
            style={{
              marginTop: '20px',
              paddingTop: '16px',
              borderTop: '1px solid #e0e0e0',
              fontSize: '12px',
              color: '#888',
              textAlign: 'center',
            }}
          >
            💡 This assessment is provided for informational purposes and is not a substitute for professional
            medical advice.
          </div>
        </>
      )}
    </div>
  );
}
