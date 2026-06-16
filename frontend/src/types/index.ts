export interface Finding {
  id: string
  title: string
  description: string
  artifact_type: string
  artifact_ref: string
  mitre_tactic: string
  mitre_technique: string
  ioc_type?: string
  ioc_value?: string
  confidence: number
  status: 'PENDING' | 'ADMITTED' | 'ADMITTED_WITH_CAVEAT' | 'REJECTED' | 'DEFERRED' | 'INCONCLUSIVE'
  event_timestamp?: string
  iteration: number
  challenge?: {
    challenge_type: string
    severity: 'FATAL' | 'MAJOR' | 'MINOR'
    argument: string
    verdict_recommendation: string
  }
  ruling?: {
    status: string
    rationale: string
    correction_required: boolean
  }
}

export interface LogEntry {
  id: string
  node: 'investigator' | 'challenger' | 'judge' | 'self_correction' | 'system'
  event_type: string
  message: string
  iteration: number
  payload: Record<string, unknown>
  finding_id?: string
  tool_name?: string
  ts: string
}

export interface FinalVerdict {
  case_id: string
  threat_classification: 'CONFIRMED_BREACH' | 'LIKELY_BREACH' | 'SUSPICIOUS' | 'BENIGN'
  confidence_level: 'HIGH' | 'MEDIUM' | 'LOW'
  admission_rate: number
  bench_opinion: string
  attack_narrative: string
  admitted_findings: string[]
  rejected_findings: string[]
  inconclusive_findings: string[]
  containment_actions: string[]
  evidence_gaps: string[]
  total_iterations: number
  total_tools_run: number
  total_evidence_refs: number
  duration_seconds: number
  finalized_at: string
}

export interface Case {
  id: string
  title: string
  description: string
  status: 'PENDING' | 'RUNNING' | 'COMPLETE' | 'FAILED'
  created_at: string
  findings_count: number
  admission_rate: number
  has_verdict: boolean
}
