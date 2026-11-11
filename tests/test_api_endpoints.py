"""Integration tests for FastAPI endpoints verifying Test Cases 1, 2, and 3."""

import pytest
from fastapi.testclient import TestClient
from main import app
from app.services.github_service import github_service


@pytest.fixture
def client():
    """Create FastAPI TestClient fixture."""
    return TestClient(app)


def test_health_check(client):
    """Verify health endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "persistence_type" in data


def test_complete_review_workflow_testcases_1_2_3(client):
    """End-to-End integration test covering Test Cases 1, 2, and 3:

    Test Case 1: Webhook PR Ingestion, Linting, & HITL Pause Gate
    Test Case 2: Feedback Input & Refactoring Proposal Re-route Loop
    Test Case 3: Approval and Git commit write back
    """
    pr_url = "https://github.com/test-org/calculator-repo/pull/42"

    # Register initial problematic code in mock PR store
    github_service.register_mock_pr(
        pr_url,
        {
            "calc.py": (
                "import math, sys\n"
                "def calculate_total( items,tax_rate ):\n"
                "    total=0\n"
                "    for i in items:\n"
                "        total=total+i\n"
                "    return total+(total*tax_rate)\n"
            )
        },
        branch="feature/calc-feature",
    )

    # -------------------------------------------------------------
    # Test Case 1: Webhook PR Ingestion, Linting, & HITL Pause Gate
    # -------------------------------------------------------------
    webhook_payload = {
        "pr_url": pr_url,
        "repository_url": "https://github.com/test-org/calculator-repo",
        "branch": "feature/calc-feature",
    }

    resp1 = client.post("/api/webhooks/github", json=webhook_payload)
    assert resp1.status_code == 201
    data1 = resp1.json()

    thread_id = data1["thread_id"]
    assert thread_id.startswith("review-")
    assert data1["status"] == "paused_for_approval"
    assert data1["next_step"] == "apply_changes_node"
    assert data1["lint_errors_found"] is True
    assert "calc.py" in data1["refactored_files"]

    # Verify state endpoint reflects pause
    state_resp1 = client.get(f"/api/reviews/{thread_id}/state")
    assert state_resp1.status_code == 200
    state1 = state_resp1.json()
    assert state1["next_nodes"] == ["apply_changes_node"]

    # -------------------------------------------------------------
    # Test Case 2: Feedback Input & Refactoring Proposal Re-route Loop
    # -------------------------------------------------------------
    rejection_payload = {
        "approved": False,
        "feedback": "Use list comprehensions instead of loops",
    }

    resp2 = client.post(f"/api/reviews/{thread_id}/approve", json=rejection_payload)
    assert resp2.status_code == 200
    data2 = resp2.json()

    assert data2["approved"] is False
    assert data2["status"] == "paused_for_approval"
    assert data2["next_step"] == "apply_changes_node"

    # Verify that proposal was regenerated incorporating the feedback
    refactored_code = data2["refactored_code"]["calc.py"]
    assert "sum([item for item in items])" in refactored_code or "comprehension" in refactored_code.lower()

    # -------------------------------------------------------------
    # Test Case 3: Approval and Git commit write back
    # -------------------------------------------------------------
    approval_payload = {
        "approved": True,
    }

    resp3 = client.post(f"/api/reviews/{thread_id}/approve", json=approval_payload)
    assert resp3.status_code == 200
    data3 = resp3.json()

    assert data3["approved"] is True
    assert data3["status"] == "completed"
    assert data3["next_step"] is None
    assert data3["commit_details"] is not None
    assert data3["commit_details"]["status"] == "committed"

    # Verify final thread state shows completion
    state_resp3 = client.get(f"/api/reviews/{thread_id}/state")
    assert state_resp3.status_code == 200
    state3 = state_resp3.json()
    assert state3["next_nodes"] == []
    assert state3["is_approved"] is True


def test_review_approval_nonexistent_thread(client):
    """Verify 404 status code when accessing a non-existent review thread."""
    resp = client.post(
        "/api/reviews/non-existent-thread-id/approve",
        json={"approved": True},
    )
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()
