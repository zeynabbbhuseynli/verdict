from __future__ import annotations
import asyncio
import uuid
from datetime import datetime
from fastapi import APIRouter, HTTPException, BackgroundTasks
from sqlalchemy import select
from verdict.db.database import AsyncSessionLocal
from verdict.db import models as db
from verdict.models import CaseCreate, CaseResponse

router = APIRouter()


@router.get("/health")
async def health():
    return {"status": "ok", "service": "verdict-backend"}


# ─── Cases ────────────────────────────────────────────────────────────────────

@router.post("/cases", response_model=CaseResponse)
async def create_case(body: CaseCreate):
    case_id = str(uuid.uuid4())
    async with AsyncSessionLocal() as session:
        case = db.Case(
            id=case_id,
            title=body.title,
            description=body.description,
            status="PENDING",
            created_at=datetime.utcnow().isoformat(),
            artifact_manifest=body.artifact_manifest,
            config={"max_iterations": body.max_iterations}
        )
        session.add(case)
        await session.commit()
    return CaseResponse(
        id=case_id,
        title=body.title,
        description=body.description,
        status="PENDING",
        created_at=datetime.utcnow().isoformat(),
        artifact_manifest=body.artifact_manifest
    )


@router.get("/cases/{case_id}")
async def get_case(case_id: str):
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(db.Case).where(db.Case.id == case_id))
        case = result.scalar_one_or_none()
        if not case:
            raise HTTPException(404, "Case not found")

        findings_r = await session.execute(
            select(db.Finding).where(db.Finding.case_id == case_id)
        )
        findings = findings_r.scalars().all()

        verdict_r = await session.execute(
            select(db.Verdict).where(db.Verdict.case_id == case_id)
        )
        verdict = verdict_r.scalar_one_or_none()

        admitted = sum(1 for f in findings if "ADMITTED" in (f.status or ""))
        rate = admitted / len(findings) if findings else 0.0

        return {
            "id": case.id,
            "title": case.title,
            "description": case.description,
            "status": case.status,
            "created_at": case.created_at,
            "artifact_manifest": case.artifact_manifest,
            "findings_count": len(findings),
            "admission_rate": rate,
            "has_verdict": verdict is not None
        }


@router.post("/cases/{case_id}/start")
async def start_investigation(case_id: str, background_tasks: BackgroundTasks):
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(db.Case).where(db.Case.id == case_id))
        case = result.scalar_one_or_none()
        if not case:
            raise HTTPException(404, "Case not found")
        if case.status == "RUNNING":
            raise HTTPException(400, "Investigation already running")

    from verdict.tasks.investigation import run_investigation
    asyncio.create_task(run_investigation(case_id))
    return {"status": "started", "case_id": case_id}


# ─── Findings ─────────────────────────────────────────────────────────────────

@router.get("/cases/{case_id}/findings")
async def get_findings(case_id: str):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(db.Finding).where(db.Finding.case_id == case_id)
        )
        findings = result.scalars().all()

        challenges_r = await session.execute(
            select(db.Challenge).where(db.Challenge.case_id == case_id)
        )
        challenges = {c.finding_id: c for c in challenges_r.scalars().all()}

        rulings_r = await session.execute(
            select(db.Ruling).where(db.Ruling.case_id == case_id)
        )
        rulings = {r.finding_id: r for r in rulings_r.scalars().all()}

        return [
            {
                "id": f.id,
                "title": f.title,
                "description": f.description,
                "artifact_type": f.artifact_type,
                "artifact_ref": f.artifact_ref,
                "mitre_tactic": f.mitre_tactic,
                "mitre_technique": f.mitre_technique,
                "ioc_type": f.ioc_type,
                "ioc_value": f.ioc_value,
                "confidence": f.confidence,
                "status": f.status,
                "event_timestamp": f.event_timestamp,
                "iteration": f.iteration,
                "challenge": {
                    "challenge_type": challenges[f.id].challenge_type,
                    "severity": challenges[f.id].severity,
                    "argument": challenges[f.id].argument,
                    "verdict_recommendation": challenges[f.id].verdict_recommendation,
                } if f.id in challenges else None,
                "ruling": {
                    "status": rulings[f.id].status,
                    "rationale": rulings[f.id].rationale,
                    "correction_required": rulings[f.id].correction_required,
                } if f.id in rulings else None
            }
            for f in findings
        ]


# ─── Verdict ──────────────────────────────────────────────────────────────────

@router.get("/cases/{case_id}/verdict")
async def get_verdict(case_id: str):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(db.Verdict).where(db.Verdict.case_id == case_id)
        )
        v = result.scalar_one_or_none()
        if not v:
            raise HTTPException(404, "Verdict not ready yet")
        return {
            "case_id": v.case_id,
            "threat_classification": v.threat_classification,
            "confidence_level": v.confidence_level,
            "admission_rate": v.admission_rate,
            "bench_opinion": v.bench_opinion,
            "attack_narrative": v.attack_narrative,
            "admitted_findings": v.admitted_findings,
            "rejected_findings": v.rejected_findings,
            "inconclusive_findings": v.inconclusive_findings,
            "containment_actions": v.containment_actions,
            "evidence_gaps": v.evidence_gaps,
            "total_iterations": v.total_iterations,
            "total_tools_run": v.total_tools_run,
            "total_evidence_refs": v.total_evidence_refs,
            "duration_seconds": v.duration_seconds,
            "finalized_at": v.finalized_at
        }


# ─── Audit Log ────────────────────────────────────────────────────────────────

@router.get("/cases/{case_id}/audit-log")
async def get_audit_log(case_id: str, node: str = None, iteration: int = None):
    async with AsyncSessionLocal() as session:
        q = select(db.ExecutionLog).where(db.ExecutionLog.case_id == case_id)
        if node:
            q = q.where(db.ExecutionLog.node == node)
        if iteration is not None:
            q = q.where(db.ExecutionLog.iteration == iteration)
        q = q.order_by(db.ExecutionLog.ts)
        result = await session.execute(q)
        logs = result.scalars().all()
        return [
            {
                "id": l.id, "node": l.node, "iteration": l.iteration,
                "event_type": l.event_type, "message": l.message,
                "payload": l.payload, "finding_id": l.finding_id,
                "tool_name": l.tool_name, "ts": l.ts
            }
            for l in logs
        ]
