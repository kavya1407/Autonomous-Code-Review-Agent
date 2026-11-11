"""Integration and state routing tests for the LangGraph review pipeline."""

import uuid
from langgraph.checkpoint.memory import MemorySaver
from app.graph.workflow import build_review_graph
from app.services.github_service import github_service


def test_pipeline_ingestion_and_interrupt_gate():
    """Verify PR ingestion, linting, proposal generation, and pausing at HITL gate."""
    checkpointer = MemorySaver()
    graph = build_review_graph(checkpointer=checkpointer)

    thread_id = f"thread-{uuid.uuid4()}"
    config = {"configurable": {"thread_id": thread_id}}

    pr_url = "https://github.com/mock-org/repo/pull/101"
    github_service.register_mock_pr(
        pr_url,
        {
            "calc.py": (
                "import sys, os\n"
                "def calculate_total( items,tax_rate ):\n"
                "    total=0\n"
                "    for i in items:\n"
                "        total=total+i\n"
                "    return total+(total*tax_rate)\n"
            )
        },
    )

    init_state = {
        "pr_url": pr_url,
        "code_contents": {},
        "lint_errors": "",
        "refactored_code": {},
        "is_approved": None,
        "reviewer_feedback": None,
        "history": [],
    }

    # Initial execution
    graph.invoke(init_state, config=config)

    # Inspect state snapshot
    snapshot = graph.get_state(config)

    # 1. Pipeline reached and paused at interrupt gate
    assert snapshot.next == ("apply_changes_node",)

    # 2. State has populated code contents, lint errors, and initial refactored draft
    values = snapshot.values
    assert "calc.py" in values["code_contents"]
    assert "F401" in values["lint_errors"] or "FLAKE8" in values["lint_errors"] or "E401" in values["lint_errors"]
    assert "calc.py" in values["refactored_code"]

    # 3. Not yet approved or committed
    assert values.get("is_approved") is None


def test_rejection_feedback_loop_and_draft_update():
    """Verify that human feedback re-routes to propose_refactor_node and updates draft."""
    checkpointer = MemorySaver()
    graph = build_review_graph(checkpointer=checkpointer)

    thread_id = f"thread-{uuid.uuid4()}"
    config = {"configurable": {"thread_id": thread_id}}

    pr_url = "https://github.com/mock-org/repo/pull/102"
    github_service.register_mock_pr(
        pr_url,
        {
            "calc.py": (
                "def calculate_total(items, tax_rate):\n"
                "    total = 0\n"
                "    for i in items:\n"
                "        total += i\n"
                "    return total + (total * tax_rate)\n"
            )
        },
    )

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
    snapshot = graph.get_state(config)
    assert snapshot.next == ("apply_changes_node",)

    # Reviewer rejects with explicit directive
    feedback_str = "Use list comprehensions instead of loops"
    graph.update_state(config, {"is_approved": False, "reviewer_feedback": feedback_str})

    # Resume graph execution
    graph.invoke(None, config=config)

    # State after rejection loop
    new_snapshot = graph.get_state(config)

    # Graph must re-halt at write gate
    assert new_snapshot.next == ("apply_changes_node",)

    # Refactored code must have incorporated reviewer feedback
    refactored_calc = new_snapshot.values["refactored_code"]["calc.py"]
    assert "sum([item for item in items])" in refactored_calc or "list comprehension" in refactored_calc.lower()


def test_approval_commits_changes_and_finishes_pipeline():
    """Verify that approving triggers apply_changes_node, commits changes, and reaches END."""
    checkpointer = MemorySaver()
    graph = build_review_graph(checkpointer=checkpointer)

    thread_id = f"thread-{uuid.uuid4()}"
    config = {"configurable": {"thread_id": thread_id}}

    pr_url = "https://github.com/mock-org/repo/pull/103"
    github_service.register_mock_pr(
        pr_url,
        {"app.py": "def foo(): pass\n"},
    )

    init_state = {
        "pr_url": pr_url,
        "code_contents": {},
        "lint_errors": "",
        "refactored_code": {},
        "is_approved": None,
        "reviewer_feedback": None,
        "history": [],
    }

    # Initial run -> paused
    graph.invoke(init_state, config=config)
    assert graph.get_state(config).next == ("apply_changes_node",)

    # Approve
    graph.update_state(config, {"is_approved": True})
    graph.invoke(None, config=config)

    final_snapshot = graph.get_state(config)
    # Execution completed
    assert final_snapshot.next == ()

    # Audit history contains commit
    commit_events = [
        ev for ev in final_snapshot.values.get("history", [])
        if ev.get("node") == "apply_changes_node" and ev.get("status") == "committed"
    ]
    assert len(commit_events) == 1
    assert "commit_result" in commit_events[0]
