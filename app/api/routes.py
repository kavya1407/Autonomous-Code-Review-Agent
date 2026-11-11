"""FastAPI Route Handlers for GitHub Webhooks and Review Approvals."""

from __future__ import annotations

import uuid
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, status
from app.api.schemas import (
    GitHubWebhookPayload,
    WebhookResponse,
    ReviewApprovalRequest,
    ReviewApprovalResponse,
    ReviewThreadStateResponse,
)
from app.graph.workflow import review_graph

router = APIRouter(prefix="/api", tags=["Code Review"])


@router.post(
    "/webhooks/github",
    response_model=WebhookResponse,
    status_code=status.HTTP_201_CREATED,
    summary="GitHub Webhook Ingestion Endpoint",
    description="Receives PR event payloads from GitHub, extracts repository parameters, and triggers a new LangGraph review thread execution.",
)
async def github_webhook_endpoint(payload: GitHubWebhookPayload) -> WebhookResponse:
    """Ingest GitHub pull request webhook event and run review pipeline up to approval gate."""
    pr_url = payload.resolve_pr_url()
    thread_id = f"review-{uuid.uuid4()}"
    config = {"configurable": {"thread_id": thread_id}}

    init_state = {
        "pr_url": pr_url,
        "code_contents": {},
        "lint_errors": "",
        "refactored_code": {},
        "is_approved": None,
        "reviewer_feedback": None,
        "history": [],
    }

    # Run pipeline until HITL interrupt gate
    review_graph.invoke(init_state, config=config)

    snapshot = review_graph.get_state(config)
    next_node = snapshot.next[0] if snapshot.next else None
    values = snapshot.values

    return WebhookResponse(
        thread_id=thread_id,
        pr_url=pr_url,
        status="paused_for_approval" if snapshot.next else "completed",
        next_step=next_node,
        lint_errors_found=bool(values.get("lint_errors")),
        refactored_files=list(values.get("refactored_code", {}).keys()),
        message="Pull request ingested. Linter executed in sandbox and paused at approval gate.",
    )


@router.post(
    "/reviews/{thread_id}/approve",
    response_model=ReviewApprovalResponse,
    summary="Review Approval & Feedback Decision Endpoint",
    description="Accepts approval payloads (containing approved: true/false and optional feedback: str) to update checkpointer state and resume the review thread.",
)
async def review_approval_endpoint(
    thread_id: str,
    payload: ReviewApprovalRequest,
) -> ReviewApprovalResponse:
    """Process human reviewer approval or rejection with feedback directive."""
    config = {"configurable": {"thread_id": thread_id}}
    snapshot = review_graph.get_state(config)

    if not snapshot.values:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Review thread with id '{thread_id}' was not found.",
        )

    if not payload.approved:
        # Rejection loop: update state with feedback and trigger re-route to propose_refactor_node
        feedback_text = payload.feedback or "Reviewer rejected changes. Please improve code quality."
        review_graph.update_state(
            config,
            {
                "is_approved": False,
                "reviewer_feedback": feedback_text,
            },
        )

        # Resume thread execution
        review_graph.invoke(None, config=config)

        updated_snapshot = review_graph.get_state(config)
        next_step = updated_snapshot.next[0] if updated_snapshot.next else None

        return ReviewApprovalResponse(
            thread_id=thread_id,
            approved=False,
            status="paused_for_approval" if updated_snapshot.next else "completed",
            next_step=next_step,
            message="Feedback recorded. Refactoring proposal regenerated and paused at approval gate.",
            refactored_code=updated_snapshot.values.get("refactored_code"),
        )
    else:
        # Approval: mark approved and resume thread to execute apply_changes_node
        review_graph.update_state(
            config,
            {"is_approved": True},
        )

        # Resume thread execution
        review_graph.invoke(None, config=config)

        final_snapshot = review_graph.get_state(config)
        history: List[Dict[str, Any]] = final_snapshot.values.get("history", [])

        commit_record = None
        for event in reversed(history):
            if event.get("node") == "apply_changes_node" and event.get("status") == "committed":
                commit_record = event.get("commit_result")
                break

        return ReviewApprovalResponse(
            thread_id=thread_id,
            approved=True,
            status="completed",
            next_step=None,
            message="Changes approved. Refactored code successfully committed to repository branch.",
            refactored_code=final_snapshot.values.get("refactored_code"),
            commit_details=commit_record,
        )


@router.get(
    "/reviews/{thread_id}/state",
    response_model=ReviewThreadStateResponse,
    summary="Get Review Thread State Snapshot",
    description="Retrieve the current checkpoint state, values, next nodes, and audit history.",
)
async def get_review_state_endpoint(thread_id: str) -> ReviewThreadStateResponse:
    """Inspect checkpoint state for a given thread."""
    config = {"configurable": {"thread_id": thread_id}}
    snapshot = review_graph.get_state(config)

    if not snapshot.values:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Review thread with id '{thread_id}' was not found.",
        )

    values = snapshot.values
    return ReviewThreadStateResponse(
        thread_id=thread_id,
        pr_url=values.get("pr_url", ""),
        next_nodes=list(snapshot.next),
        is_approved=values.get("is_approved"),
        reviewer_feedback=values.get("reviewer_feedback"),
        lint_errors=values.get("lint_errors", ""),
        refactored_files=list(values.get("refactored_code", {}).keys()),
        history=values.get("history", []),
    )
