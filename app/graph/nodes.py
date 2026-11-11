"""Graph node implementations for autonomous code review pipeline."""

from __future__ import annotations

import datetime
from typing import Dict, Any, List
from langgraph.graph import END
from app.graph.state import ReviewState
from app.services.github_service import github_service
from app.services.refactor_service import refactor_service
from app.tools.linter import execute_sandbox_lint


def _create_event(node_name: str, details: Dict[str, Any]) -> Dict[str, Any]:
    """Helper to produce a structured history event record."""
    return {
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "node": node_name,
        **details,
    }


def fetch_pr_node(state: ReviewState) -> Dict[str, Any]:
    """Connect to GitHub API, pull modified PR files, and store in graph state."""
    pr_url = state.get("pr_url", "")
    code_contents = github_service.fetch_pr_files(pr_url)

    history: List[Dict[str, Any]] = list(state.get("history", []))
    history.append(
        _create_event(
            "fetch_pr_node",
            {
                "pr_url": pr_url,
                "files_count": len(code_contents),
                "files": list(code_contents.keys()),
                "status": "success",
            },
        )
    )

    return {
        "code_contents": code_contents,
        "history": history,
    }


def lint_code_node(state: ReviewState) -> Dict[str, Any]:
    """Execute code formatting and linting tools inside a secure execution sandbox."""
    code_contents = state.get("code_contents", {})
    lint_reports: List[str] = []

    for filename, code in code_contents.items():
        if filename.endswith(".py"):
            res = execute_sandbox_lint(code_string=code, run_black=True)
            if not res["passed"]:
                lint_reports.append(f"--- File: {filename} ---\n{res['summary']}")

    aggregated_errors = "\n\n".join(lint_reports).strip()
    history: List[Dict[str, Any]] = list(state.get("history", []))
    history.append(
        _create_event(
            "lint_code_node",
            {
                "lint_errors_found": bool(aggregated_errors),
                "status": "success",
            },
        )
    )

    return {
        "lint_errors": aggregated_errors,
        "history": history,
    }


def propose_refactor_node(state: ReviewState) -> Dict[str, Any]:
    """Invoke LLM to generate refactored code blocks resolving lint errors and feedback."""
    code_contents = state.get("code_contents", {})
    lint_errors = state.get("lint_errors", "")
    reviewer_feedback = state.get("reviewer_feedback")

    refactored_code = refactor_service.refactor_all_files(
        code_contents=code_contents,
        lint_errors=lint_errors,
        reviewer_feedback=reviewer_feedback,
    )

    history: List[Dict[str, Any]] = list(state.get("history", []))
    history.append(
        _create_event(
            "propose_refactor_node",
            {
                "refactored_files": list(refactored_code.keys()),
                "incorporated_feedback": reviewer_feedback,
                "status": "success",
            },
        )
    )

    return {
        "refactored_code": refactored_code,
        "history": history,
    }


def apply_changes_node(state: ReviewState) -> Dict[str, Any]:
    """Commit approved refactored code back to GitHub branch or record rejection loop."""
    is_approved = state.get("is_approved")
    pr_url = state.get("pr_url", "")
    refactored_code = state.get("refactored_code", {})
    history: List[Dict[str, Any]] = list(state.get("history", []))

    if is_approved is True:
        commit_result = github_service.commit_changes(
            pr_url=pr_url,
            refactored_code=refactored_code,
        )
        history.append(
            _create_event(
                "apply_changes_node",
                {
                    "action": "commit",
                    "status": "committed",
                    "commit_result": commit_result,
                },
            )
        )
    else:
        # Rejected or pending feedback loop
        history.append(
            _create_event(
                "apply_changes_node",
                {
                    "action": "feedback_reroute",
                    "status": "rejected_rerouting",
                    "reviewer_feedback": state.get("reviewer_feedback"),
                },
            )
        )

    return {"history": history}


def route_after_apply(state: ReviewState) -> str:
    """Determine whether to conclude review pipeline or loop back to propose_refactor_node."""
    if state.get("is_approved") is True:
        return END
    return "propose_refactor_node"
