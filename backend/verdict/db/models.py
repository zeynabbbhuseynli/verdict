import uuid
from datetime import datetime
from sqlalchemy import Column, String, Float, Boolean, Integer, DateTime, JSON, Text
from sqlalchemy.dialects.postgresql import UUID
from verdict.db.database import Base


def gen_uuid():
    return str(uuid.uuid4())


class Case(Base):
    __tablename__ = "cases"
    id = Column(String, primary_key=True, default=gen_uuid)
    title = Column(String, nullable=False)
    description = Column(Text, default="")
    status = Column(String, default="PENDING")
    created_at = Column(String, default=lambda: datetime.utcnow().isoformat())
    artifact_manifest = Column(JSON, default={})
    config = Column(JSON, default={})


class Finding(Base):
    __tablename__ = "findings"
    id = Column(String, primary_key=True, default=gen_uuid)
    case_id = Column(String, nullable=False, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    artifact_type = Column(String, nullable=False)
    artifact_ref = Column(String)
    raw_evidence_snippet = Column(Text, default="")
    mitre_tactic = Column(String, default="")
    mitre_technique = Column(String, default="")
    ioc_type = Column(String)
    ioc_value = Column(String)
    confidence = Column(Float, nullable=False)
    status = Column(String, default="PENDING")
    event_timestamp = Column(String)
    found_at = Column(String, default=lambda: datetime.utcnow().isoformat())
    iteration = Column(Integer, default=0)


class Challenge(Base):
    __tablename__ = "challenges"
    id = Column(String, primary_key=True, default=gen_uuid)
    case_id = Column(String, nullable=False, index=True)
    finding_id = Column(String, nullable=False, index=True)
    challenge_type = Column(String, nullable=False)
    argument = Column(Text, nullable=False)
    alternative_explanation = Column(Text, default="")
    missing_evidence = Column(JSON, default=[])
    recommended_tools = Column(JSON, default=[])
    verdict_recommendation = Column(String, nullable=False)
    severity = Column(String, nullable=False)
    iteration = Column(Integer, default=0)
    created_at = Column(String, default=lambda: datetime.utcnow().isoformat())


class Ruling(Base):
    __tablename__ = "rulings"
    id = Column(String, primary_key=True, default=gen_uuid)
    case_id = Column(String, nullable=False, index=True)
    finding_id = Column(String, nullable=False, index=True)
    status = Column(String, nullable=False)
    rationale = Column(Text, nullable=False)
    challenge_response = Column(Text, default="")
    correction_required = Column(Boolean, default=False)
    requested_tools = Column(JSON, default=[])
    requested_evidence = Column(JSON, default=[])
    iteration = Column(Integer, default=0)
    ruled_at = Column(String, default=lambda: datetime.utcnow().isoformat())


class ExecutionLog(Base):
    __tablename__ = "execution_log"
    id = Column(String, primary_key=True, default=gen_uuid)
    case_id = Column(String, nullable=False, index=True)
    node = Column(String, nullable=False)
    iteration = Column(Integer, default=0)
    event_type = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    payload = Column(JSON, default={})
    finding_id = Column(String)
    tool_name = Column(String)
    ts = Column(String, default=lambda: datetime.utcnow().isoformat())


class Verdict(Base):
    __tablename__ = "verdicts"
    id = Column(String, primary_key=True, default=gen_uuid)
    case_id = Column(String, nullable=False, unique=True, index=True)
    threat_classification = Column(String, nullable=False)
    confidence_level = Column(String, nullable=False)
    admission_rate = Column(Float, nullable=False)
    bench_opinion = Column(Text, nullable=False)
    attack_narrative = Column(Text, nullable=False)
    admitted_findings = Column(JSON, default=[])
    rejected_findings = Column(JSON, default=[])
    inconclusive_findings = Column(JSON, default=[])
    containment_actions = Column(JSON, default=[])
    evidence_gaps = Column(JSON, default=[])
    total_iterations = Column(Integer, default=0)
    total_tools_run = Column(Integer, default=0)
    total_evidence_refs = Column(Integer, default=0)
    duration_seconds = Column(Float, default=0.0)
    finalized_at = Column(String, default=lambda: datetime.utcnow().isoformat())
