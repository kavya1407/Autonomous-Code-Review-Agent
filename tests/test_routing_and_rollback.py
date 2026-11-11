"""Advanced Routing, State Rollback, and Multi-turn Review Tests."""

import uuid
from langgraph.checkpoint.memory import MemorySaver
from app.graph.workflow import build_review_graph
from app.services.github_service import GitHubService


def test_multi_turn_review_feedback_loop():
    """Verify that multiple successive human review feedback turns are correctly handled."""
    checkpointer = MemorySaver()
    graph = build_review_graph(checkpointer=checkpointer)

    thread_id = f"thread-multi-{uuid.uuid4()}"
    config = {"configurable": {"thread_id": thread_id}}

    mock_github = GitHubService(token="mock_token")
    pr_url = "https://github.com/mock-org/multi-turn-repo/pull/5"
    mock_github.register_mock_pr(
        pr_url,
        {
            "service.py": (
                "import os, sys\n"
                "def process_data(data):\n"
                "    out=[]\n"
                "    for x in data:\n"
                "        out.append(x * 2)\n"
                "    return out\n"
            )
        },
    )

    # 1. Initial Webhook Ingestion & First Pass
    init_state = {
        "pr_url": pr_url,
        "code_contents": {},
        "lint_errors": "",
        "refactored_code": {},
        "is_approved": None,
        "reviewer_feedback": None,
        "history": [],
    }
    graph.invoke(init_state, config=config)
    assert graph.get_state(config).next == ("apply_changes_node",)

    # 2. First Review: Reject with feedback to use list comprehension
    graph.update_state(
        config,
        {
            "is_approved": False,
            "reviewer_feedback": "Use list comprehensions instead of loops",
        },
    )
    graph.invoke(None, config=config)

    snap1 = graph.get_state(config)
    assert snap1.next == ("apply_changes_node",)
    assert snap1.values.get("is_approved") is False
    assert snap1.values.get("reviewer_feedback") == "Use list comprehensions instead of loops"

    # 3. Second Review: Reject with another directive
    graph.update_state(
        config,
        {
            "is_approved": False,
            "reviewer_feedback": "Ensure strict type annotations and docstrings",
        },
    )
    graph.invoke(None, config=config)

    snap2 = graph.get_state(config)
    assert snap2.next == ("apply_changes_node",)
    assert snap2.values.get("reviewer_feedback") == "Ensure strict type annotations and docstrings"

    # 4. Final Review: Approve
    graph.update_state(config, {"is_approved": True})
    graph.invoke(None, config=config)

    final_snap = graph.get_state(config)
    assert final_snap.next == ()
    assert final_snap.values.get("is_approved") is True

    # Assert history contains all intermediate feedback steps and final commit
    events = final_snap.values.get("history", [])
    apply_events = [e for e in events if e.get("node") == "apply_changes_node"]
    assert len(apply_events) == 3  # Two rejections + one final approval commit
    assert apply_events[0]["status"] == "rejected_rerouting"
    assert apply_events[1]["status"] == "rejected_rerouting"
    assert apply_events[2]["status"] == "committed"


def test_checkpoint_history_tracking():
    """Verify that graph checkpointer maintains state history snapshots."""
    checkpointer = MemorySaver()
    graph = build_review_graph(checkpointer=checkpointer)

    thread_id = f"thread-history-{uuid.uuid4()}"
    config = {"configurable": {"thread_id": thread_id}}

    init_state = {
        "pr_url": "https://github.com/mock-org/history-test/pull/10",
        "code_contents": {"main.py": "x = 1\n"},
        "lint_errors": "",
        "refactored_code": {},
        "is_approved": None,
        "reviewer_feedback": None,
        "history": [],
    }

    graph.invoke(init_state, config=config)

    # Fetch history snapshots from checkpointer
    history_snapshots = list(graph.get_state_history(config))
    assert len(history_snapshots) > 1

    # Verify latest checkpoint points to interrupt before apply_changes_node
    latest = history_snapshots[0]
    assert latest.next == ("apply_changes_node",)
