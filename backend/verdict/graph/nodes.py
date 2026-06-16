from __future__ import annotations
import json
import re
import uuid
import asyncio
import httpx
from datetime import datetime
import google.generativeai as genai
from google.generativeai.types import GenerationConfig
from verdict.config import MCP_SERVER_URL, MODEL, GOOGLE_API_KEY
from verdict.agents.prompts import (
    INVESTIGATOR_SYSTEM, CHALLENGER_SYSTEM,
    JUDGE_SYSTEM, SELF_CORRECTION_SYSTEM
)
from verdict.graph.state import VerdictState
from verdict.graph.events import emit

genai.configure(api_key=GOOGLE_API_KEY)


async def call_llm(system_prompt: str, user_message: str, max_tokens: int = 4096) -> str:
    """Call Gemini with a system prompt + user message. Adds a small delay to
    respect the free-tier rate limit (15 RPM on gemini-1.5-flash)."""
    await asyncio.sleep(2)          # ~15 RPM safe margin
    model = genai.GenerativeModel(
        model_name=MODEL,
        system_instruction=system_prompt
    )
    response = await model.generate_content_async(
        user_message,
        generation_config=GenerationConfig(max_output_tokens=max_tokens)
    )
    return response.text


# ─── Utilities ───────────────────────────────────────────────────────────────

def extract_json(text: str):
    """Robustly extract JSON from Claude responses."""
    text = re.sub(r'```json\s*', '', text)
    text = re.sub(r'```\s*', '', text)
    text = text.strip()
    try:
        return json.loads(text)
    except Exception:
        pass
    # Try finding array or object
    for pattern in [r'(\[[\s\S]*\])', r'(\{[\s\S]*\})']:
        m = re.search(pattern, text)
        if m:
            try:
                return json.loads(m.group(1))
            except Exception:
                pass
    return []


def make_log(node: str, event_type: str, message: str,
             iteration: int = 0, payload: dict = None,
             tool_name: str = None, finding_id: str = None) -> dict:
    return {
        "id": str(uuid.uuid4()),
        "node": node,
        "event_type": event_type,
        "message": message,
        "iteration": iteration,
        "payload": payload or {},
        "tool_name": tool_name,
        "finding_id": finding_id,
        "ts": datetime.utcnow().isoformat()
    }


def select_tools(manifest: dict) -> list[str]:
    tools = []
    if manifest.get("has_memory_dump"):
        tools += ["volatility_pslist", "volatility_malfind"]
    if manifest.get("has_logs"):
        tools += ["hayabusa_scan"]
    if manifest.get("has_pcap"):
        tools += ["zeek_analyze"]
    if manifest.get("has_disk_image"):
        tools += ["fls_timeline"]
    return tools


async def call_tool(tool_name: str, manifest: dict) -> dict:
    """Call the MCP server for a SIFT tool result."""
    async with httpx.AsyncClient(timeout=30.0) as http:
        r = await http.post(f"{MCP_SERVER_URL}/tools/{tool_name}",
                            json={"manifest": manifest})
        r.raise_for_status()
        return r.json()


def format_tool_results(results: list[dict]) -> str:
    parts = []
    for r in results:
        tool = r.get("tool", "unknown")
        output = json.dumps(r.get("output", {}), indent=2)
        parts.append(f"=== {tool.upper()} OUTPUT ===\n{output}\n")
    return "\n".join(parts)


# ─── Node 1: Investigator ────────────────────────────────────────────────────

async def run_investigator(state: VerdictState) -> dict:
    case_id = state["case_id"]
    manifest = state["artifact_manifest"]
    iteration = state["current_iteration"]
    tools_run = select_tools(manifest)
    logs = []

    await emit(case_id, make_log("investigator", "AGENT_STARTED",
        "⚖ Investigator online — selecting forensic tools", iteration))

    # Run all SIFT tools via MCP server
    tool_results = []
    for tool_name in tools_run:
        log = make_log("investigator", "TOOL_INVOKED",
                       f"Running {tool_name}...", iteration, tool_name=tool_name)
        logs.append(log)
        await emit(case_id, log)
        try:
            output = await call_tool(tool_name, manifest)
            tool_results.append({"tool": tool_name, "output": output})
            done_log = make_log("investigator", "TOOL_COMPLETED",
                                f"✓ {tool_name} completed", iteration,
                                payload={"keys": list(output.keys())},
                                tool_name=tool_name)
            logs.append(done_log)
            await emit(case_id, done_log)
        except Exception as e:
            err_log = make_log("investigator", "TOOL_FAILED",
                               f"✗ {tool_name} failed: {e}", iteration, tool_name=tool_name)
            logs.append(err_log)
            await emit(case_id, err_log)

    analysis_log = make_log("investigator", "AGENT_RUNNING",
        "Investigator is analyzing tool outputs with Claude...", iteration)
    logs.append(analysis_log)
    await emit(case_id, analysis_log)

    # Claude analyses the tool output
    tool_text = format_tool_results(tool_results)
    raw_text = await call_llm(
        INVESTIGATOR_SYSTEM,
        f"Analyze the following forensic tool outputs and identify all findings.\n"
        f"Return ONLY a JSON array of finding objects.\n\n{tool_text}"
    )

    raw_findings = extract_json(raw_text)
    if not isinstance(raw_findings, list):
        raw_findings = []

    # Attach IDs
    findings = []
    for f in raw_findings:
        f["id"] = f.get("id") or str(uuid.uuid4())
        f["case_id"] = case_id
        f["iteration"] = iteration
        f["status"] = "PENDING"
        f["found_at"] = datetime.utcnow().isoformat()
        findings.append(f)

    done = make_log("investigator", "FINDINGS_CREATED",
                    f"Investigator identified {len(findings)} findings",
                    iteration, payload={"count": len(findings)})
    logs.append(done)
    await emit(case_id, done)

    return {
        "investigator_report": {"findings": findings, "tool_results": tool_results},
        "execution_log": logs,
        "tools_run_count": state.get("tools_run_count", 0) + len(tools_run)
    }


# ─── Node 2: Challenger ──────────────────────────────────────────────────────

async def run_challenger(state: VerdictState) -> dict:
    case_id = state["case_id"]
    iteration = state["current_iteration"]
    findings = state["investigator_report"]["findings"]
    logs = []

    start_log = make_log("challenger", "AGENT_STARTED",
        f"⚔ Challenger online — attacking {len(findings)} findings", iteration)
    logs.append(start_log)
    await emit(case_id, start_log)

    findings_text = json.dumps(findings, indent=2)
    raw_text = await call_llm(
        CHALLENGER_SYSTEM,
        f"Challenge each of the following findings. "
        f"Return ONLY a JSON array of challenge objects.\n\n"
        f"FINDINGS:\n{findings_text}"
    )

    raw_challenges = extract_json(raw_text)
    if not isinstance(raw_challenges, list):
        raw_challenges = []

    challenges = []
    for c in raw_challenges:
        c["id"] = c.get("id") or str(uuid.uuid4())
        c["case_id"] = case_id
        c["iteration"] = iteration
        challenges.append(c)

    for ch in challenges:
        finding_title = next(
            (f["title"] for f in findings if f["id"] == ch.get("finding_id")), "unknown"
        )
        log = make_log("challenger", "CHALLENGE_ISSUED",
                       f"⚔ {ch.get('severity','?')} challenge on: {finding_title[:50]}",
                       iteration, payload={"type": ch.get("challenge_type")},
                       finding_id=ch.get("finding_id"))
        logs.append(log)
        await emit(case_id, log)

    done = make_log("challenger", "AGENT_COMPLETE",
                    f"Challenger filed {len(challenges)} challenges", iteration)
    logs.append(done)
    await emit(case_id, done)

    return {
        "challenge_report": {"challenges": challenges},
        "execution_log": logs
    }


# ─── Node 3: Judge ───────────────────────────────────────────────────────────

async def run_judge(state: VerdictState) -> dict:
    case_id = state["case_id"]
    iteration = state["current_iteration"]
    findings = state["investigator_report"]["findings"]
    challenges = state["challenge_report"]["challenges"]
    logs = []

    start_log = make_log("judge", "AGENT_STARTED",
        "🔨 Judge online — evaluating findings and challenges", iteration)
    logs.append(start_log)
    await emit(case_id, start_log)

    # Build paired input for judge
    pairs = []
    challenge_map = {c.get("finding_id"): c for c in challenges}
    for f in findings:
        ch = challenge_map.get(f["id"], {})
        pairs.append({"finding": f, "challenge": ch})

    pairs_text = json.dumps(pairs, indent=2)
    raw_text = await call_llm(
        JUDGE_SYSTEM,
        f"Rule on each finding+challenge pair. "
        f"Return ONLY a JSON object with 'rulings' array and 'bench_opinion' string.\n\n"
        f"PAIRS:\n{pairs_text}"
    )

    result = extract_json(raw_text)
    if isinstance(result, dict):
        raw_rulings = result.get("rulings", [])
        bench_opinion = result.get("bench_opinion", "")
    else:
        raw_rulings = []
        bench_opinion = ""

    rulings = []
    for r in raw_rulings:
        r["id"] = r.get("id") or str(uuid.uuid4())
        r["case_id"] = case_id
        r["iteration"] = iteration
        r["ruled_at"] = datetime.utcnow().isoformat()
        rulings.append(r)

    # Emit a log per ruling
    for ruling in rulings:
        finding_title = next(
            (f["title"] for f in findings if f["id"] == ruling.get("finding_id")), "unknown"
        )
        status = ruling.get("status", "?")
        emoji = {"ADMITTED": "✓", "ADMITTED_WITH_CAVEAT": "~", "REJECTED": "✗", "DEFERRED": "⏳"}.get(status, "?")
        log = make_log("judge", "RULING_ISSUED",
                       f"{emoji} {status}: {finding_title[:50]}",
                       iteration, payload={"status": status},
                       finding_id=ruling.get("finding_id"))
        logs.append(log)
        await emit(case_id, log)

    admitted = sum(1 for r in rulings if "ADMITTED" in r.get("status", ""))
    admission_rate = admitted / len(rulings) if rulings else 0.0

    rate_log = make_log("judge", "ADMISSION_RATE",
                        f"Admission rate: {admission_rate:.0%} ({admitted}/{len(rulings)})",
                        iteration, payload={"rate": admission_rate})
    logs.append(rate_log)
    await emit(case_id, rate_log)

    return {
        "judge_rulings": rulings,
        "admission_rate": admission_rate,
        "current_iteration": iteration + 1,
        "execution_log": logs,
        "_bench_opinion": bench_opinion  # carried to finalize
    }


# ─── Node 4: Self-Correction ─────────────────────────────────────────────────

async def run_self_correction(state: VerdictState) -> dict:
    case_id = state["case_id"]
    iteration = state["current_iteration"]
    findings = state["investigator_report"]["findings"]
    rulings = state["judge_rulings"]
    logs = []
    corrections = list(state.get("correction_iterations", []))
    tools_run_count = state.get("tools_run_count", 0)

    deferred = [r for r in rulings if r.get("status") in ("DEFERRED", "REJECTED")
                and r.get("correction_required")]

    start_log = make_log("self_correction", "CORRECTION_STARTED",
        f"🔄 Self-Correction Engine: addressing {len(deferred)} deferred findings",
        iteration)
    logs.append(start_log)
    await emit(case_id, start_log)

    updated_findings = {f["id"]: f.copy() for f in findings}

    for ruling in deferred:
        finding_id = ruling.get("finding_id")
        original = updated_findings.get(finding_id)
        if not original:
            continue

        req_tools = ruling.get("requested_tools", [])
        if not req_tools:
            req_tools = select_tools(state["artifact_manifest"])[:2]

        tool_log = make_log("self_correction", "TOOL_INVOKED",
            f"Running {len(req_tools)} additional tool(s) for: {original['title'][:40]}",
            iteration, finding_id=finding_id)
        logs.append(tool_log)
        await emit(case_id, tool_log)

        # Gather new evidence from requested tools
        new_results = []
        for tool_name in req_tools:
            try:
                output = await call_tool(tool_name, state["artifact_manifest"])
                new_results.append({"tool": tool_name, "output": output})
                tools_run_count += 1
                tl = make_log("self_correction", "TOOL_COMPLETED",
                              f"✓ {tool_name} returned new evidence",
                              iteration, tool_name=tool_name, finding_id=finding_id)
                logs.append(tl)
                await emit(case_id, tl)
            except Exception as e:
                el = make_log("self_correction", "TOOL_FAILED",
                              f"✗ {tool_name} failed: {e}", iteration)
                logs.append(el)
                await emit(case_id, el)

        # Ask Gemini to re-investigate with new evidence
        new_evidence_text = format_tool_results(new_results)
        raw_text = await call_llm(
            SELF_CORRECTION_SYSTEM,
            f"Re-investigate the following finding given new forensic evidence.\n"
            f"Judge's reason for requesting more: {ruling.get('rationale', '')}\n"
            f"Requested additional evidence: {ruling.get('requested_evidence', [])}\n\n"
            f"ORIGINAL FINDING:\n{json.dumps(original, indent=2)}\n\n"
            f"NEW TOOL OUTPUTS:\n{new_evidence_text}\n\n"
            f"Return ONLY a JSON object representing the updated finding.",
            max_tokens=2048
        )

        updated = extract_json(raw_text)
        if isinstance(updated, dict) and updated:
            # Preserve ID and case_id
            updated["id"] = finding_id
            updated["case_id"] = case_id
            updated["iteration"] = iteration
            updated["status"] = "PENDING"
            old_conf = original.get("confidence", 0)
            new_conf = updated.get("confidence", old_conf)
            updated_findings[finding_id] = updated

            corrections.append({
                "id": str(uuid.uuid4()),
                "case_id": case_id,
                "finding_id": finding_id,
                "iteration": iteration,
                "trigger_reason": ruling.get("rationale", ""),
                "tools_run": req_tools,
                "old_confidence": old_conf,
                "new_confidence": new_conf,
                "old_status": ruling.get("status", ""),
                "new_status": "PENDING",
                "ts": datetime.utcnow().isoformat()
            })

            direction = "↑" if new_conf > old_conf else "↓" if new_conf < old_conf else "→"
            corr_log = make_log("self_correction", "CORRECTION_COMPLETED",
                f"Finding updated: confidence {old_conf:.2f} {direction} {new_conf:.2f}",
                iteration, finding_id=finding_id,
                payload={"old": old_conf, "new": new_conf})
            logs.append(corr_log)
            await emit(case_id, corr_log)

    # Rebuild findings list with updates
    new_findings_list = [updated_findings.get(f["id"], f) for f in findings]

    return {
        "investigator_report": {
            **state["investigator_report"],
            "findings": new_findings_list
        },
        "correction_iterations": corrections,
        "execution_log": logs,
        "tools_run_count": tools_run_count
    }


# ─── Node 5: Finalize ────────────────────────────────────────────────────────

async def run_finalize(state: VerdictState) -> dict:
    import time
    case_id = state["case_id"]
    rulings = state["judge_rulings"]
    findings = state["investigator_report"]["findings"]
    iteration = state["current_iteration"]
    logs = []

    await emit(case_id, make_log("system", "VERDICT_BUILDING",
        "⚖ Compiling final verdict...", iteration))

    admitted = [r["finding_id"] for r in rulings if "ADMITTED" in r.get("status", "")]
    rejected = [r["finding_id"] for r in rulings if r.get("status") == "REJECTED"]
    inconclusive = [
        f["id"] for f in findings
        if f["id"] not in admitted and f["id"] not in rejected
    ]

    rate = len(admitted) / len(rulings) if rulings else 0.0
    avg_conf = sum(f.get("confidence", 0) for f in findings) / len(findings) if findings else 0

    if rate >= 0.8 and avg_conf >= 0.75:
        threat_class = "CONFIRMED_BREACH"
        conf_level = "HIGH"
    elif rate >= 0.6 or avg_conf >= 0.60:
        threat_class = "LIKELY_BREACH"
        conf_level = "MEDIUM"
    elif rate >= 0.3:
        threat_class = "SUSPICIOUS"
        conf_level = "LOW"
    else:
        threat_class = "BENIGN"
        conf_level = "LOW"

    bench_opinion = state.get("_bench_opinion", "")
    if not bench_opinion:
        bench_opinion = (
            f"The evidence, after {iteration} iteration(s) of adversarial review, "
            f"supports a {threat_class.replace('_', ' ').lower()} classification. "
            f"{len(admitted)} of {len(rulings)} findings were admitted into evidence."
        )

    attack_narrative = "\n".join(
        f["description"] for f in findings if f["id"] in admitted
    )

    containment = []
    evidence_gaps = []
    for f in findings:
        if f["id"] in admitted:
            tactic = f.get("mitre_tactic", "")
            if "Persistence" in tactic:
                containment.append("Remove identified scheduled tasks and registry run keys")
            if "Credential" in tactic:
                containment.append("Reset all domain credentials — LSASS was accessed")
            if "Command" in tactic:
                containment.append(f"Block outbound connections to {f.get('ioc_value', 'identified C2 IPs')}")
            if "Exfil" in tactic:
                containment.append("Identify and scope all data that may have been exfiltrated")
        elif f["id"] in inconclusive:
            evidence_gaps.append(f.get("title", "Unknown finding") + " — insufficient corroborating evidence")

    elapsed = time.time() - state.get("start_time", time.time())
    verdict = {
        "id": str(uuid.uuid4()),
        "case_id": case_id,
        "threat_classification": threat_class,
        "confidence_level": conf_level,
        "admission_rate": rate,
        "bench_opinion": bench_opinion,
        "attack_narrative": attack_narrative,
        "admitted_findings": admitted,
        "rejected_findings": rejected,
        "inconclusive_findings": inconclusive,
        "containment_actions": list(set(containment)),
        "evidence_gaps": evidence_gaps,
        "total_iterations": iteration,
        "total_tools_run": state.get("tools_run_count", 0),
        "total_evidence_refs": len(findings),
        "duration_seconds": elapsed,
        "finalized_at": datetime.utcnow().isoformat()
    }

    verdict_log = make_log("system", "VERDICT_ISSUED",
        f"🏛 VERDICT: {threat_class} | Admission rate: {rate:.0%}",
        iteration, payload={"verdict": threat_class, "rate": rate})
    logs.append(verdict_log)
    await emit(case_id, verdict_log)

    return {"final_verdict": verdict, "execution_log": logs}
