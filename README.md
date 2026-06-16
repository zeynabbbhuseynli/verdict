# VERDICT: Multi Agent DFIR Courtroom

> Replay the Breach. Cross Examine the Evidence.
> Built for the SANS Find Evil! Hackathon

## Overview

VERDICT is a multi agent digital forensics and incident response platform where AI agents investigate, challenge, cross examine, and rule on forensic evidence before issuing a final verdict.

Traditional forensic tools generate findings. VERDICT puts those findings on trial.

Every claim must survive adversarial review before being admitted into evidence.

```text
INVESTIGATOR → CHALLENGER → JUDGE → SELF CORRECTION ENGINE → VERDICT
```

The result is a transparent and auditable investigation process that produces findings, confidence scores, MITRE ATT&CK mappings, containment recommendations, and a final bench opinion.

## The Four Agents

### Investigator

Analyzes forensic artifacts and generates findings with confidence scores and MITRE ATT&CK mappings.

### Challenger

Acts like a defense attorney by attacking findings, identifying weak evidence, false positives, missing context, and alternative explanations.

### Judge

Evaluates findings and challenges before issuing rulings:

```text
ADMITTED
ADMITTED WITH CAVEAT
REJECTED
DEFERRED
```

### Self Correction Engine

When evidence is insufficient, additional investigation is performed and findings are re evaluated before a final ruling is issued.

## Why VERDICT?

Most AI security tools generate answers.

VERDICT generates arguments.

Instead of trusting a single model output, evidence must survive investigation, challenge, judicial review, and self correction before reaching a conclusion.

This approach creates a more transparent and defensible incident response workflow.

## Demo Scenario

VERDICT includes a simulated ransomware investigation involving:

* Spear phishing
* PowerShell execution
* Credential dumping
* Persistence mechanisms
* Command and control activity
* Lateral movement
* Data exfiltration
* Ransomware deployment

The final result is a complete breach assessment with supporting evidence and an auditable reasoning trail.

## Architecture

```text
Browser
Upload → Courtroom Live Stream → Verdict

           ↓

FastAPI Backend
LangGraph Multi Agent Workflow

           ↓

Investigator
     ↓
Challenger
     ↓
Judge
     ↓
Self Correction Engine
     ↓
Final Verdict

           ↓

PostgreSQL
Redis
MCP Tool Server
Google Gemini 2.5 Flash
```

## Technologies

* Google Gemini 2.5 Flash
* LangGraph
* FastAPI
* React
* PostgreSQL
* Redis
* Docker
* MITRE ATT&CK
* Digital Forensics
* Incident Response

## Quick Start

```bash
git clone https://github.com/zeynabbbhuseynli/verdict.git
cd verdict
cp .env.example .env
```

Add your Gemini API key to `.env`:

```env
GOOGLE_API_KEY=your_gemini_api_key_here
```

Start the platform:

```bash
docker compose up --build
```

Run the demo case:

```bash
python demo/scripts/seed_demo_case.py
```

Open:

```text
http://localhost:3000
```

## Repository

https://github.com/zeynabbbhuseynli/verdict

## Hackathon

Built for the SANS Find Evil! Hackathon to explore how multi agent systems can improve forensic reasoning, evidence validation, and incident response decision making.

