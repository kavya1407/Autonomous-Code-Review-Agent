"""Review pipeline state schema definition."""

from __future__ import annotations

from typing import Dict, List, Optional, Any, TypedDict


class ReviewState(TypedDict, total=False):
    """LangGraph review pipeline state schema.

    Attributes:
        pr_url: Target GitHub pull request URL.
        code_contents: Mapping of file path to original source code string.
        lint_errors: Aggregated flake8 and black linting diagnostics.
        refactored_code: Mapping of file path to proposed refactored code string.
        is_approved: Human reviewer decision (True = approved, False = rejected, None = pending).
        reviewer_feedback: Human reviewer textual feedback and directives.
        history: Chronological log of audit events, agent actions, and commit records.
    """

    pr_url: str
    code_contents: Dict[str, str]
    lint_errors: str
    refactored_code: Dict[str, str]
    is_approved: Optional[bool]
    reviewer_feedback: Optional[str]
    history: List[Dict[str, Any]]
