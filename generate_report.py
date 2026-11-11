"""Generate PDF submission report for Autonomous Code Review & Refactoring Agent."""

from fpdf import FPDF


class ProjectReportPDF(FPDF):
    def header(self):
        self.set_font("helvetica", "B", 10)
        self.set_text_color(100, 100, 100)
        self.cell(0, 8, "Autonomous Code Review & Refactoring Agent | Assessment Report", align="R", new_x="LMARGIN", new_y="NEXT")
        self.line(10, 17, 200, 17)
        self.ln(4)

    def footer(self):
        self.set_y(-15)
        self.set_font("helvetica", "I", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")


def build_pdf():
    pdf = ProjectReportPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # Title Banner
    pdf.set_font("helvetica", "B", 18)
    pdf.set_text_color(24, 43, 73)
    pdf.cell(0, 10, "Autonomous Code Review & Refactoring Agent", new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("helvetica", "B", 12)
    pdf.set_text_color(70, 130, 180)
    pdf.cell(0, 7, "Practical Assessment Report - LangGraph, FastAPI, Docker", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    # Metadata Table
    pdf.set_font("helvetica", "", 9)
    pdf.set_text_color(40, 40, 40)
    meta = [
        ("Candidate Name:", "Kavyashree Manthri"),
        ("GitHub Repository:", "https://github.com/kavya1407/Autonomous-Code-Review-Agent"),
        ("Assessment Topic:", "Topic 2 - Autonomous Code Intelligence: Build an AI-Powered Agent"),
        ("Tech Stack:", "Python, LangGraph, FastAPI, GitHub REST API, Docker, pytest, flake8, black"),
        ("Test Results:", "17 / 17 Automated Tests Passing (100%)"),
    ]
    for label, val in meta:
        pdf.set_font("helvetica", "B", 9)
        pdf.cell(42, 6, label)
        pdf.set_font("helvetica", "", 9)
        pdf.cell(0, 6, val, new_x="LMARGIN", new_y="NEXT")

    pdf.ln(5)

    # 1. Project Overview & Business Context
    pdf.set_font("helvetica", "B", 13)
    pdf.set_text_color(24, 43, 73)
    pdf.cell(0, 8, "1. Executive Summary & Business Context", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("helvetica", "", 9.5)
    pdf.set_text_color(40, 40, 40)
    pdf.multi_cell(
        0,
        5.2,
        "Enterprise development teams require automated systems to review incoming Pull Requests (PRs), "
        "execute linters inside sandboxed environments, propose refactoring templates, and require human engineer "
        "confirmations before mutating repositories. This project implements an end-to-end autonomous agent using "
        "LangGraph, featuring stateful transitions, persistent checkpointers, Human-in-the-Loop (HITL) interrupt gates, "
        "and a secure subprocess linter sandbox.",
    )
    pdf.ln(4)

    # 2. Architecture & LangGraph Pipeline
    pdf.set_font("helvetica", "B", 13)
    pdf.set_text_color(24, 43, 73)
    pdf.cell(0, 8, "2. LangGraph Stateful Pipeline Architecture", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("helvetica", "", 9.5)
    pdf.set_text_color(40, 40, 40)
    pdf.multi_cell(
        0,
        5.2,
        "The review pipeline is constructed as a LangGraph StateGraph tracking 'pr_url', 'code_contents', 'lint_errors', "
        "'refactored_code', 'is_approved', 'reviewer_feedback', and chronological audit 'history'.\n\n"
        "Workflow Nodes:\n"
        "- fetch_pr_node: Pulls modified files from GitHub PR via REST API.\n"
        "- lint_code_node: Runs flake8 and black --check inside a temporary filesystem sandbox.\n"
        "- propose_refactor_node: Invokes LLM (or deterministic engine) to resolve errors and apply feedback.\n"
        "- apply_changes_node: Commits approved code back to the branch via GitHub API.\n\n"
        "HITL Interrupt Gate: Execution pauses before repository mutation using interrupt_before=['apply_changes_node']. "
        "When feedback is provided instead of approval, the state machine rolls back to propose_refactor_node, regenerates "
        "the proposal incorporating reviewer directives, and repauses at the write gate.",
    )
    pdf.ln(4)

    # 3. Custom Execution Sandbox Tool
    pdf.set_font("helvetica", "B", 13)
    pdf.set_text_color(24, 43, 73)
    pdf.cell(0, 8, "3. Custom Python Execution Sandbox Tool", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("helvetica", "", 9.5)
    pdf.set_text_color(40, 40, 40)
    pdf.multi_cell(
        0,
        5.2,
        "Implemented via LangChain's @tool decorator in 'run_linter_tool'. The tool creates an isolated temporary "
        "directory via tempfile.TemporaryDirectory, writes source code, and spawns subprocesses for flake8 and black "
        "with strict 15-second execution timeouts. It isolates execution from the host and safely captures stdout and stderr.",
    )
    pdf.ln(4)

    # Page 2
    pdf.add_page()

    # 4. FastAPI Endpoints & Webhook Integration
    pdf.set_font("helvetica", "B", 13)
    pdf.set_text_color(24, 43, 73)
    pdf.cell(0, 8, "4. FastAPI Endpoints & Integration", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("helvetica", "", 9.5)
    pdf.set_text_color(40, 40, 40)
    endpoints = [
        ("POST /api/webhooks/github", "Ingests PR events, extracts parameters, and triggers stateful thread."),
        ("POST /api/reviews/{thread_id}/approve", "Accepts approval/rejection with optional feedback to resume or rollback thread."),
        ("GET /api/reviews/{thread_id}/state", "Inspects active checkpoint state, next nodes, and history log."),
        ("GET /health", "System health and persistence configuration status."),
    ]
    for ep, desc in endpoints:
        pdf.set_font("helvetica", "B", 9)
        pdf.cell(75, 6, ep)
        pdf.set_font("helvetica", "", 9)
        pdf.cell(0, 6, desc, new_x="LMARGIN", new_y="NEXT")

    pdf.ln(5)

    # 5. Verification & Test Case Validation
    pdf.set_font("helvetica", "B", 13)
    pdf.set_text_color(24, 43, 73)
    pdf.cell(0, 8, "5. Verification & Validation Results", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("helvetica", "", 9.5)
    pdf.set_text_color(40, 40, 40)
    pdf.multi_cell(
        0,
        5.2,
        "All three required project verification workflows were executed and validated:\n\n"
        "1. Test Case 1 (Webhook Ingestion & HITL Gate): PR webhook received, linter executed inside sandbox, "
        "and execution successfully halted before apply_changes_node with status 'paused_for_approval'.\n\n"
        "2. Test Case 2 (Feedback & Proposal Re-route): Reviewer rejected with 'Use list comprehensions instead of loops'. "
        "The graph re-routed to propose_refactor_node, regenerated draft with sum([item for item in items]), "
        "and repaused before the write gate.\n\n"
        "3. Test Case 3 (Approval & Commit Write Back): Reviewer approved with approved=true. Graph resumed, executed "
        "apply_changes_node, committed changes to GitHub branch, and completed thread with status 'completed'.",
    )
    pdf.ln(5)

    # 6. Automated Test Suite Summary
    pdf.set_font("helvetica", "B", 13)
    pdf.set_text_color(24, 43, 73)
    pdf.cell(0, 8, "6. Automated Test Suite (17 / 17 Passing)", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("helvetica", "", 9.5)
    pdf.set_text_color(40, 40, 40)
    pdf.multi_cell(
        0,
        5.2,
        "- tests/test_sandbox_tool.py: Verified flake8 error detection (F401, E401), syntax errors (E999), and clean code.\n"
        "- tests/test_graph_pipeline.py: Verified LangGraph interrupt gates, rejection rollback loops, and completion.\n"
        "- tests/test_api_endpoints.py: Verified Test Cases 1, 2, 3 end-to-end via FastAPI TestClient.\n"
        "- tests/test_routing_and_rollback.py: Verified multi-turn review feedback and checkpointer history snapshots.\n"
        "- tests/test_github_service.py: Verified PR URL parsing and mock commit operations.\n"
        "- tests/test_refactor_service.py: Verified markdown extraction and feedback instruction handling.",
    )
    pdf.ln(6)

    # 7. Deliverables Checklist
    pdf.set_font("helvetica", "B", 13)
    pdf.set_text_color(24, 43, 73)
    pdf.cell(0, 8, "7. Submission Checklist", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("helvetica", "", 9.5)
    pdf.set_text_color(40, 40, 40)
    checklist = [
        ("[x] GitHub Public Repository Link", "https://github.com/kavya1407/Autonomous-Code-Review-Agent"),
        ("[x] OpenAPI Specification", "openapi.json included in repository root"),
        ("[x] README Documentation", "Full architecture diagram, setup, and test verification guide"),
        ("[x] Docker Infrastructure", "Dockerfile and docker-compose.yml configured"),
        ("[x] Git Commits", "10 progressive commits demonstrating incremental milestones"),
    ]
    for chk, dtl in checklist:
        pdf.set_font("helvetica", "B", 9)
        pdf.cell(65, 5.5, chk)
        pdf.set_font("helvetica", "", 9)
        pdf.cell(0, 5.5, dtl, new_x="LMARGIN", new_y="NEXT")

    out_path = "Autonomous_Code_Review_Project_Report.pdf"
    pdf.output(out_path)
    print(f"Generated PDF: {out_path}")


if __name__ == "__main__":
    build_pdf()
