#!/usr/bin/env python3
"""
Seed the demo case for VERDICT hackathon presentation.
Run: python demo/scripts/seed_demo_case.py
"""
import requests
import sys
import time

API = "http://localhost:8000/api/v1"


def seed():
    print("\n⚖  VERDICT Demo Seeder")
    print("─" * 40)

    # Health check
    try:
        r = requests.get(f"{API}/health", timeout=5)
        r.raise_for_status()
        print("✓ Backend is online")
    except Exception as e:
        print(f"✗ Backend not reachable: {e}")
        print("  Run: docker compose up -d")
        sys.exit(1)

    # Create the demo case
    print("\n→ Creating demo case...")
    r = requests.post(f"{API}/cases", json={
        "title": "Ransomware Incident — WORKSTATION01 (Demo)",
        "description": (
            "Pre-built ransomware scenario. "
            "Artifacts: Windows memory dump, EVTX event logs, network PCAP, disk image. "
            "Attack chain: spearphishing → PowerShell dropper → lsass dump → C2 → lateral movement → exfil → ransomware."
        ),
        "max_iterations": 3,
        "artifact_manifest": {
            "has_memory_dump": True,
            "has_disk_image": True,
            "has_pcap": True,
            "has_logs": True
        }
    })

    if r.status_code != 200:
        print(f"✗ Failed to create case: {r.text}")
        sys.exit(1)

    case_id = r.json()["id"]
    print(f"✓ Case created: {case_id[:8]}...")

    # Start the investigation
    print("\n→ Starting investigation pipeline...")
    r = requests.post(f"{API}/cases/{case_id}/start")
    if r.status_code != 200:
        print(f"✗ Failed to start: {r.text}")
        sys.exit(1)
    print("✓ Investigation started (LangGraph pipeline running)")

    print(f"\n🏛  Open the courtroom at:")
    print(f"   http://localhost:3000/courtroom/{case_id}")
    print(f"\n   Or go to http://localhost:3000 and it will appear as a running case.")
    print(f"\n📊  Watch the live evidence log stream as agents debate the findings.")
    print(f"    The investigation typically completes in 2-4 minutes.\n")

    return case_id


if __name__ == "__main__":
    seed()
