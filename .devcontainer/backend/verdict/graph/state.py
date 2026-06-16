from __future__ import annotations
from typing import TypedDict, List, Optional, Annotated
import operator


class VerdictState(TypedDict):
    # Case metadata
    case_id: str
    artifact_manifest: dict
    start_time: float
    max_iterations: int

    # Agent outputs
    investigator_report: Optional[dict]   # {findings: [...], tool_results: [...]}
    challenge_report: Optional[dict]      # {challenges: [...]}
    judge_rulings: List[dict]

    # Self-correction tracking
    correction_iterations: List[dict]
    current_iteration: int

    # Execution log (append-only via operator.add)
    execution_log: Annotated[List[dict], operator.add]

    # Termination
    final_verdict: Optional[dict]
    admission_rate: float
    tools_run_count: int
