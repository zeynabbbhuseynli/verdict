from __future__ import annotations
from pydantic import BaseModel, Field
from typing import List, Optional, Literal, Any
from datetime import datetime
import uuid


def new_id() -> str:
    return str(uuid.uuid4())


# ─── Finding ────────────────────────────────────────────────────────────────

class Finding(BaseModel):
    id: str = Field(default_factory=new_id)
    case_id: str
    title: str
    description: str
    artifact_type: Literal["PROCESS", "FILE", "REGISTRY", "NETWORK", "LOG_EVENT", "MEMORY"]
    artifact_ref: str
    raw_evidence_snippet: str
    mitre_tactic: str
    mitre_technique: str
    ioc_type: Optional[str] = None
    ioc_value: Optional[str] = None
    confidence: float
    status: Literal[
        "PENDING", "ADMITTED", "ADMITTED_WITH_CAVEAT",
        "REJECTED", "DEFERRED", "INCONCLUSIVE"
    ] = "PENDING"
    event_timestamp: Optional[str] = None
    found_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    iteration: int = 0


# ─── Challenge ──────────────────────────────────────────────────────────────

class Challenge(BaseModel):
    id: str = Field(default_factory=new_id)
    finding_id: str
    case_id: str
    challenge_type: Literal[
        "FALSE_POSITIVE", "ALT_HYPOTHESIS", "EVIDENCE_GAP",
        "TIMESTAMP_ANOMALY", "TOOL_RELIABILITY", "CHAIN_OF_CUSTODY"
    ]
    argument: str
    alternative_explanation: str
    missing_evidence: List[str] = []
    recommended_tools: List[str] = []
    verdict_recommendation: Literal["SUSTAINED", "OVERRULED", "NEEDS_MORE_EVIDENCE"]
    severity: Literal["FATAL", "MAJOR", "MINOR"]
    iteration: int = 0


# ─── Ruling ─────────────────────────────────────────────────────────────────

class JudgeRuling(BaseModel):
    id: str = Field(default_factory=new_id)
    finding_id: str
    case_id: str
    status: Literal["ADMITTED", "ADMITTED_WITH_CAVEAT", "REJECTED", "DEFERRED"]
    rationale: str
    challenge_response: str
    correction_required: bool
    requested_tools: List[str] = []
    requested_evidence: List[str] = []
    iteration: int = 0
    ruled_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


# ─── Timeline ────────────────────────────────────────────────────────────────

class TimelineEvent(BaseModel):
    id: str = Field(default_factory=new_id)
    case_id: str
    timestamp: str
    event_type: str
    description: str
    finding_ids: List[str] = []
    confidence: float
    mitre_tactic: str
    data_source: str


class AttackTimeline(BaseModel):
    case_id: str
    events: List[TimelineEvent] = []
    attack_phases: List[str] = []
    estimated_dwell_time: Optional[str] = None
    patient_zero: Optional[str] = None


# ─── Correction ──────────────────────────────────────────────────────────────

class CorrectionIteration(BaseModel):
    id: str = Field(default_factory=new_id)
    case_id: str
    finding_id: str
    iteration: int
    trigger_reason: str
    tools_run: List[str] = []
    old_confidence: float
    new_confidence: float
    old_status: str
    new_status: str
    ts: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


# ─── Log Entry ───────────────────────────────────────────────────────────────

class LogEntry(BaseModel):
    id: str = Field(default_factory=new_id)
    case_id: str
    node: Literal["investigator", "challenger", "judge", "self_correction", "system"]
    iteration: int = 0
    event_type: str
    message: str
    payload: dict = {}
    finding_id: Optional[str] = None
    tool_name: Optional[str] = None
    ts: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


# ─── Final Verdict ───────────────────────────────────────────────────────────

class FinalVerdict(BaseModel):
    id: str = Field(default_factory=new_id)
    case_id: str
    threat_classification: Literal["CONFIRMED_BREACH", "LIKELY_BREACH", "SUSPICIOUS", "BENIGN"]
    confidence_level: Literal["HIGH", "MEDIUM", "LOW"]
    admission_rate: float
    bench_opinion: str
    attack_narrative: str
    admitted_findings: List[str] = []
    rejected_findings: List[str] = []
    inconclusive_findings: List[str] = []
    containment_actions: List[str] = []
    evidence_gaps: List[str] = []
    total_iterations: int
    total_tools_run: int
    total_evidence_refs: int
    duration_seconds: float
    finalized_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


# ─── Case ─────────────────────────────────────────────────────────────────────

class CaseCreate(BaseModel):
    title: str
    description: str = ""
    max_iterations: int = 3
    artifact_manifest: dict = {
        "has_memory_dump": True,
        "has_disk_image": True,
        "has_pcap": True,
        "has_logs": True
    }


class CaseResponse(BaseModel):
    id: str
    title: str
    status: str
    description: str = ""
    created_at: str
    artifact_manifest: dict = {}


# ─── API responses ────────────────────────────────────────────────────────────

class InvestigatorReport(BaseModel):
    findings: List[Finding]
    tool_results: List[dict]


class ChallengeReport(BaseModel):
    challenges: List[Challenge]


class FullCaseState(BaseModel):
    case_id: str
    status: str
    findings: List[Finding] = []
    challenges: List[Challenge] = []
    rulings: List[JudgeRuling] = []
    timeline: Optional[AttackTimeline] = None
    verdict: Optional[FinalVerdict] = None
    admission_rate: float = 0.0
    current_iteration: int = 0
