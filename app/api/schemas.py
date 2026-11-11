"""API Request and Response Pydantic Schemas."""

from __future__ import annotations

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class PullRequestNested(BaseModel):
    """GitHub Pull Request nested object."""
    html_url: Optional[str] = None
    number: Optional[int] = None
    head: Optional[Dict[str, Any]] = None
    base: Optional[Dict[str, Any]] = None


class RepositoryNested(BaseModel):
    """GitHub Repository nested object."""
    html_url: Optional[str] = None
    full_name: Optional[str] = None


class GitHubWebhookPayload(BaseModel):
    """Webhook payload schema for incoming GitHub pull request events.

    Accepts both official GitHub webhook payloads and simplified test payloads.
    """
    action: Optional[str] = "opened"
    # Official GitHub webhook payload structure
    pull_request: Optional[PullRequestNested] = None
    repository: Optional[RepositoryNested] = None

    # Flattened payload structure (for testing & simulations)
    pr_url: Optional[str] = None
    repository_url: Optional[str] = None
    branch: Optional[str] = None

    def resolve_pr_url(self) -> str:
        """Resolve PR URL from either flattened or nested GitHub payload fields."""
        if self.pr_url:
            return self.pr_url
        if self.pull_request and self.pull_request.html_url:
            return self.pull_request.html_url
        if self.repository and self.repository.html_url and self.pull_request and self.pull_request.number:
            return f"{self.repository.html_url}/pull/{self.pull_request.number}"
        if self.repository_url:
            return f"{self.repository_url.rstrip('/')}/pull/1"
        return "https://github.com/mock-org/mock-repo/pull/1"


class WebhookResponse(BaseModel):
    """Response returned upon receiving and initiating PR review pipeline."""
    thread_id: str
    pr_url: str
    status: str
    next_step: Optional[str] = None
    lint_errors_found: bool
    refactored_files: List[str]
    message: str


class ReviewApprovalRequest(BaseModel):
    """Payload schema for human approval or rejection with feedback."""
    approved: bool = Field(..., description="True to approve commit, False to reject with feedback.")
    feedback: Optional[str] = Field(None, description="Optional reviewer feedback directive.")


class ReviewApprovalResponse(BaseModel):
    """Response returned after processing human reviewer feedback or approval."""
    thread_id: str
    approved: bool
    status: str
    next_step: Optional[str] = None
    message: str
    refactored_code: Optional[Dict[str, str]] = None
    commit_details: Optional[Dict[str, Any]] = None


class ReviewThreadStateResponse(BaseModel):
    """Response returning full state and audit history for an active review thread."""
    thread_id: str
    pr_url: str
    next_nodes: List[str]
    is_approved: Optional[bool]
    reviewer_feedback: Optional[str]
    lint_errors: str
    refactored_files: List[str]
    history: List[Dict[str, Any]]
