# VERDICT — Forensic Courtroom Intelligence System

> *Replay the Breach. Cross-Examine the Evidence.*
> SANS "Find Evil!" Hackathon

---

## What it is

VERDICT is a multi-agent forensic reasoning system where 4 AI agents run an adversarial courtroom process on forensic evidence:

```
INVESTIGATOR → CHALLENGER → JUDGE → SELF-CORRECTION ENGINE → VERDICT
```

Every finding must survive cross-examination before being admitted into evidence. Weak findings trigger additional investigation. The final verdict includes a bench opinion, MITRE ATT&CK mapping, containment actions, and full audit trail.

---

## Quick Start (3 steps)

```bash
# 1. Clone & configure
cp .env.example .env
# Add your Anthropic API key to .env

# 2. Start everything
docker compose up -d

# 3. Seed the demo case (ransomware scenario)
python demo/scripts/seed_demo_case.py
# → Opens http://localhost:3000/courtroom/<case-id>
```

Or just open **http://localhost:3000** and click **Launch Demo Case**.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Browser (localhost:3000)                  │
│  Upload → Courtroom (live WS) → Verdict                     │
└────────────────────┬────────────────────────────────────────┘
                     │ HTTP / WebSocket
┌────────────────────▼────────────────────────────────────────┐
│              FastAPI Backend (localhost:8000)                │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │           LangGraph Pipeline                         │   │
│  │                                                     │   │
│  │  investigate → challenge → judge ──┐                │   │
│  │      ↑                             │                │   │
│  │      └── self_correct ←────────────┘ (if DEFERRED) │   │
│  │                        └──────────→ finalize        │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  Each agent calls: Google Gemini API (gemini-1.5-flash)     │
└──────┬──────────────────────────────────┬───────────────────┘
       │                                  │
       │ HTTP                    Redis pub/sub
       ▼                                  ▼
┌──────────────┐              ┌───────────────────┐
│  MCP Server  │              │  WebSocket clients│
│  (port 8001) │              │  (browser)        │
│              │              └───────────────────┘
│  Mock SIFT   │
│  Tools:      │
│  • volatility│
│  • hayabusa  │
│  • zeek      │
│  • fls/tsk   │
└──────────────┘
```

### Services

| Service     | Port | Description                          |
|-------------|------|--------------------------------------|
| frontend    | 3000 | React + Vite + Tailwind              |
| backend     | 8000 | FastAPI + LangGraph pipeline         |
| mcp-server  | 8001 | Mock SIFT tools (HTTP REST)          |
| postgres    | 5432 | Case/findings/verdicts storage       |
| redis       | 6379 | WebSocket pub/sub event bus          |

---

## The 4 Agents

### Agent 1 — Investigator
Receives forensic tool output (Volatility, Hayabusa, Zeek, FLS timeline) and produces structured findings with MITRE ATT&CK mapping and per-finding confidence scores.

### Agent 2 — Challenger
Attacks every finding as a defense attorney would: false positives, tool reliability issues, missing corroborating evidence, timestamp anomalies. Files `FATAL/MAJOR/MINOR` challenges.

### Agent 3 — Judge
Rules on each finding+challenge pair: `ADMITTED`, `ADMITTED_WITH_CAVEAT`, `REJECTED`, or `DEFERRED` (with specific tools requested). Produces the bench opinion.

### Agent 4 — Self-Correction Engine
When findings are DEFERRED, runs the judge's requested tools and re-investigates. Confidence updates are tracked. The loop runs up to `max_iterations` (default: 3).

---

## Demo Scenario

**Ransomware attack on WORKSTATION01**

| Time   | Event                                          |
|--------|------------------------------------------------|
| T-72h  | Spearphishing → Excel macro executes           |
| T-71h  | PowerShell dropper downloads stage2.dll        |
| T-70h  | Fake lsass.exe dumps credentials               |
| T-69h  | DLL injected into real lsass.exe (Mimikatz)    |
| T-68h  | Scheduled task persistence created             |
| T-67h  | C2 beacon to 45.77.23.108 every 5 minutes      |
| T-48h  | Lateral movement to FILESERVER01               |
| T-6h   | 156MB data exfiltrated via HTTPS               |
| T-0    | Ransomware deployed, files encrypted           |

The Investigator finds ~9 findings. The Challenger attacks several. The Judge defers 2-3 for additional tools. The Self-Correction Engine resolves them. Final verdict: `CONFIRMED_BREACH`.

---

## Swapping in Real SIFT Tools

The MCP server (`mcp-server/verdict_sift_server/server.py`) maps tool names to outputs. To use real tools, replace the mock returns in `mock_data.py` with actual subprocess calls:

```python
# Replace this:
return TOOL_OUTPUTS["volatility_pslist"]

# With something like:
import subprocess, json
result = subprocess.run(
    ["python3", "/opt/volatility3/vol.py", "-f", memory_path,
     "windows.pslist.PsList", "--output", "json"],
    capture_output=True, text=True
)
return json.loads(result.stdout)
```

No changes needed to the agents, graph, or frontend.

---

## File Structure

```
verdict/
├── docker-compose.yml
├── .env.example
├── backend/
│   ├── Dockerfile
│   └── verdict/
│       ├── config.py           # env vars
│       ├── main.py             # FastAPI app
│       ├── models.py           # Pydantic models
│       ├── agents/
│       │   └── prompts.py      # All 4 agent system prompts
│       ├── graph/
│       │   ├── state.py        # VerdictState TypedDict
│       │   ├── nodes.py        # Agent implementations
│       │   ├── workflow.py     # LangGraph graph + conditional edges
│       │   └── events.py       # Redis pub/sub emitter
│       ├── api/
│       │   ├── router.py       # REST endpoints
│       │   └── websocket.py    # Live stream endpoint
│       ├── db/
│       │   ├── database.py     # SQLAlchemy async engine
│       │   └── models.py       # ORM models
│       └── tasks/
│           └── investigation.py # Pipeline runner + DB persistence
├── mcp-server/
│   ├── Dockerfile
│   └── verdict_sift_server/
│       ├── server.py           # FastAPI tool server
│       └── mock_data.py        # Realistic ransomware scenario data
├── frontend/
│   └── src/
│       ├── pages/
│       │   ├── Upload.tsx      # Case creation
│       │   ├── Courtroom.tsx   # Live investigation view
│       │   └── Verdict.tsx     # Final verdict + findings table
│       ├── hooks/
│       │   └── useLiveStream.ts # WebSocket hook
│       └── types/index.ts      # TypeScript interfaces
└── demo/
    └── scripts/
        └── seed_demo_case.py   # Demo launcher
```

---

## API Endpoints

```
POST /api/v1/cases                  Create case
POST /api/v1/cases/{id}/start       Start investigation
GET  /api/v1/cases/{id}             Case status + stats
GET  /api/v1/cases/{id}/findings    All findings with challenges/rulings
GET  /api/v1/cases/{id}/verdict     Final verdict
GET  /api/v1/cases/{id}/audit-log   Full execution log
WS   /ws/cases/{id}/live            Real-time event stream
```
