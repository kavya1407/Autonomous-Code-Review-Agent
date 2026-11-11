"""LangGraph review pipeline construction and compilation."""

from __future__ import annotations

import os
import sqlite3
from typing import Optional
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver

from app.core.config import settings
from app.graph.state import ReviewState
from app.graph.nodes import (
    fetch_pr_node,
    lint_code_node,
    propose_refactor_node,
    apply_changes_node,
    route_after_apply,
)


def create_checkpointer(persistence_type: Optional[str] = None) -> BaseCheckpointSaver:
    """Create persistent checkpointer based on configuration (memory or sqlite)."""
    p_type = persistence_type or settings.persistence_type

    if p_type == "sqlite":
        try:
            from langgraph.checkpoint.sqlite import SqliteSaver

            db_path = settings.checkpoint_db_path
            db_dir = os.path.dirname(db_path)
            if db_dir:
                os.makedirs(db_dir, exist_ok=True)
            conn = sqlite3.connect(db_path, check_same_thread=False)
            return SqliteSaver(conn)
        except Exception:
            # Fallback gracefully to MemorySaver if sqlite setup encounters issue
            return MemorySaver()

    return MemorySaver()


def build_review_graph(checkpointer: Optional[BaseCheckpointSaver] = None):
    """Construct and compile the review workflow StateGraph with HITL interrupt gate.

    Pipeline topology:
        START -> fetch_pr_node -> lint_code_node -> propose_refactor_node
        -> [HITL Interrupt Gate] -> apply_changes_node -> (conditional: END or rollback to propose_refactor_node)
    """
    builder = StateGraph(ReviewState)

    # 1. Register workflow nodes
    builder.add_node("fetch_pr_node", fetch_pr_node)
    builder.add_node("lint_code_node", lint_code_node)
    builder.add_node("propose_refactor_node", propose_refactor_node)
    builder.add_node("apply_changes_node", apply_changes_node)

    # 2. Add sequential transitions
    builder.add_edge(START, "fetch_pr_node")
    builder.add_edge("fetch_pr_node", "lint_code_node")
    builder.add_edge("lint_code_node", "propose_refactor_node")
    builder.add_edge("propose_refactor_node", "apply_changes_node")

    # 3. Add conditional edge from apply_changes_node for human feedback loops
    builder.add_conditional_edges(
        "apply_changes_node",
        route_after_apply,
        {
            END: END,
            "propose_refactor_node": "propose_refactor_node",
        },
    )

    saver = checkpointer if checkpointer is not None else create_checkpointer()

    # 4. Compile with persistent checkpointing and interrupt gate before apply_changes_node
    compiled_graph = builder.compile(
        checkpointer=saver,
        interrupt_before=["apply_changes_node"],
    )
    return compiled_graph


# Global default compiled graph
review_graph = build_review_graph()
