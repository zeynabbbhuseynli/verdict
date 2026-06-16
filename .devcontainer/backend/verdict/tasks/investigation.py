from __future__ import annotations
import time
import json
import asyncio
from sqlalchemy import select, update
from verdict.db.database import AsyncSessionLocal
from verdict.db import models as db
from verdict.graph.workflow import verdict_graph
from verdict.graph.state import VerdictState
from verdict.graph.events import emit, get_redis


async def run_investigation(case_id: str):
    """Main investigation pipeline — called as an asyncio task."""
    async with AsyncSessionLocal() as session:
        # Mark case as RUNNING
        await session.execute(
            update(db.Case).where(db.Case.id == case_id).values(status="RUNNING")
        )
        await session.commit()

        # Load case
        result = await session.execute(select(db.Case).where(db.Case.id == case_id))
        case = result.scalar_one_or_none()
        if not case:
            return

    initial_state: VerdictState = {
        "case_id": case_id,
        "artifact_manifest": case.artifact_manifest or {},
        "start_time": time.time(),
        "max_iterations": case.config.get("max_iterations", 3),
        "investigator_report": None,
        "challenge_report": None,
        "judge_rulings": [],
        "correction_iterations": [],
        "current_iteration": 0,
        "execution_log": [],
        "final_verdict": None,
        "admission_rate": 0.0,
        "tools_run_count": 0,
    }

    try:
        final_state = await verdict_graph.ainvoke(initial_state)
        await persist_results(case_id, final_state)
        await mark_case_complete(case_id, "COMPLETE")
    except Exception as e:
        import traceback
        traceback.print_exc()
        await emit(case_id, {
            "node": "system", "event_type": "ERROR",
            "message": f"Investigation failed: {e}",
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "iteration": 0, "payload": {}
        })
        await mark_case_complete(case_id, "FAILED")


async def persist_results(case_id: str, state: VerdictState):
    """Save all agent outputs to the database."""
    async with AsyncSessionLocal() as session:
        report = state.get("investigator_report") or {}
        findings = report.get("findings", [])

        for f in findings:
            ruling = next(
                (r for r in state.get("judge_rulings", []) if r.get("finding_id") == f["id"]),
                None
            )
            status = ruling.get("status", "PENDING") if ruling else "PENDING"

            db_finding = db.Finding(
                id=f["id"], case_id=case_id,
                title=f.get("title", ""),
                description=f.get("description", ""),
                artifact_type=f.get("artifact_type", "PROCESS"),
                artifact_ref=f.get("artifact_ref", ""),
                raw_evidence_snippet=f.get("raw_evidence_snippet", ""),
                mitre_tactic=f.get("mitre_tactic", ""),
                mitre_technique=f.get("mitre_technique", ""),
                ioc_type=f.get("ioc_type"),
                ioc_value=f.get("ioc_value"),
                confidence=f.get("confidence", 0.0),
                status=status,
                event_timestamp=f.get("event_timestamp"),
                iteration=f.get("iteration", 0)
            )
            session.add(db_finding)

        challenge_report = state.get("challenge_report") or {}
        for c in challenge_report.get("challenges", []):
            db_challenge = db.Challenge(
                id=c["id"], case_id=case_id,
                finding_id=c.get("finding_id", ""),
                challenge_type=c.get("challenge_type", "ALT_HYPOTHESIS"),
                argument=c.get("argument", ""),
                alternative_explanation=c.get("alternative_explanation", ""),
                missing_evidence=c.get("missing_evidence", []),
                recommended_tools=c.get("recommended_tools", []),
                verdict_recommendation=c.get("verdict_recommendation", "NEEDS_MORE_EVIDENCE"),
                severity=c.get("severity", "MINOR"),
                iteration=c.get("iteration", 0)
            )
            session.add(db_challenge)

        for r in state.get("judge_rulings", []):
            db_ruling = db.Ruling(
                id=r["id"], case_id=case_id,
                finding_id=r.get("finding_id", ""),
                status=r.get("status", "PENDING"),
                rationale=r.get("rationale", ""),
                challenge_response=r.get("challenge_response", ""),
                correction_required=r.get("correction_required", False),
                requested_tools=r.get("requested_tools", []),
                requested_evidence=r.get("requested_evidence", []),
                iteration=r.get("iteration", 0)
            )
            session.add(db_ruling)

        for log in state.get("execution_log", []):
            db_log = db.ExecutionLog(
                id=log.get("id", ""),
                case_id=case_id,
                node=log.get("node", "system"),
                iteration=log.get("iteration", 0),
                event_type=log.get("event_type", ""),
                message=log.get("message", ""),
                payload=log.get("payload", {}),
                finding_id=log.get("finding_id"),
                tool_name=log.get("tool_name"),
                ts=log.get("ts", "")
            )
            session.add(db_log)

        verdict = state.get("final_verdict")
        if verdict:
            db_verdict = db.Verdict(
                id=verdict["id"], case_id=case_id,
                threat_classification=verdict.get("threat_classification", "SUSPICIOUS"),
                confidence_level=verdict.get("confidence_level", "LOW"),
                admission_rate=verdict.get("admission_rate", 0.0),
                bench_opinion=verdict.get("bench_opinion", ""),
                attack_narrative=verdict.get("attack_narrative", ""),
                admitted_findings=verdict.get("admitted_findings", []),
                rejected_findings=verdict.get("rejected_findings", []),
                inconclusive_findings=verdict.get("inconclusive_findings", []),
                containment_actions=verdict.get("containment_actions", []),
                evidence_gaps=verdict.get("evidence_gaps", []),
                total_iterations=verdict.get("total_iterations", 0),
                total_tools_run=verdict.get("total_tools_run", 0),
                total_evidence_refs=verdict.get("total_evidence_refs", 0),
                duration_seconds=verdict.get("duration_seconds", 0.0),
                finalized_at=verdict.get("finalized_at", "")
            )
            session.add(db_verdict)

        await session.commit()


async def mark_case_complete(case_id: str, status: str):
    async with AsyncSessionLocal() as session:
        await session.execute(
            update(db.Case).where(db.Case.id == case_id).values(status=status)
        )
        await session.commit()
