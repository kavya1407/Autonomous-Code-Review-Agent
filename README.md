# Autonomous Code Review & Refactoring Agent with LangGraph

- **Repository**: [https://github.com/kavya1407/Autonomous-Code-Review-Agent](https://github.com/kavya1407/Autonomous-Code-Review-Agent)

[![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.12%20%7C%203.14-blue.svg)](https://www.python.org/)
[![LangGraph](https://img.shields.io/badge/LangGraph-StateGraph%20HITL-orange.svg)](https://github.com/langchain-ai/langgraph)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-green.svg)](https://fastapi.tiangolo.com/)
[![Tests](https://img.shields.io/badge/pytest-passing%20(17%2F17)-brightgreen.svg)]()

Autonomous Code Review & Refactoring Agent built with **LangGraph**, **FastAPI**, and a **Sandboxed Python Linter Execution Tool**. The system reviews incoming Pull Requests, executes static analysis and linting (`flake8`, `black --check`) inside an isolated filesystem sandbox, proposes functional-preserving refactorings using LLM agents, enforces strict Human-in-the-Loop (HITL) approval gates before mutating repositories, and supports feedback iteration loops with state rollbacks.

---

## Architecture Overview

```mermaid
flowchart TD
    A([GitHub PR Webhook / API Ingestion]) --> B[fetch_pr_node\nPull modified files via GitHub REST API]
    B --> C[lint_code_node\nExecute flake8/black in Isolated Sandbox]
    C --> D[propose_refactor_node\nLLM Generates Refactoring Proposal]
    D --> E{HITL Interrupt Gate\ninterrupt_before=['apply_changes_node']}
    
    E -- "Human Review: Feedback / Rejected\n(approved=False)" --> F[apply_changes_node\nRecord Rejection Event]
    F -- "Loop Back with Reviewer Directives" --> D
    
    E -- "Human Review: Approved\n(approved=True)" --> G[apply_changes_node\nCommit Refactored Code to Branch]
    G --> H([END: PR Successfully Updated])
```

### Core Architecture Highlights
1. **LangGraph State Machine**: A typed state machine tracking `pr_url`, `code_contents`, `lint_errors`, `refactored_code`, `is_approved`, `reviewer_feedback`, and chronological audit `history`.
2. **Persistent Checkpointer**: State threads are backed by `MemorySaver` or `SqliteSaver`, enabling full state persistence, resuming, and state history tracking across webhook events.
3. **HITL Interrupt Gates**: Execution halts before `apply_changes_node` using `interrupt_before=["apply_changes_node"]`, ensuring code changes are never committed without explicit human authorization.
4. **Feedback & Rollback Loop**: When a human engineer requests modifications (`approved: false, feedback: "..."`), the state records the feedback, triggers the feedback re-route, and regenerates the refactored code without committing changes.
5. **Secure Execution Sandbox**: A custom LangChain `@tool` isolates target Python code inside temporary sandboxes, executing `flake8` and `black --check` with subprocess timeouts and capturing stdout/stderr safely.

---

## Project Structure

```text
Autonomous_Code_Review/
├── .env.example                     # Environment template
├── .gitignore                       # Git ignore configuration
├── Dockerfile                       # Multi-stage production container
├── docker-compose.yml               # Container orchestration
├── main.py                          # Top-level ASGI entrypoint (uvicorn main:app --reload)
├── openapi.json                     # Exported OpenAPI 3.1.0 specification
├── pytest.ini                       # Test suite configuration
├── requirements.txt                 # Pinned dependencies
├── README.md                        # Project documentation & verification guide
├── app/
│   ├── __init__.py
│   ├── main.py                      # FastAPI application setup & CORS configuration
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes.py                # Webhooks, approvals, and thread inspection routes
│   │   └── schemas.py               # Pydantic request & response models
│   ├── core/
│   │   ├── __init__.py
│   │   └── config.py                # BaseSettings configuration with .env integration
│   ├── graph/
│   │   ├── __init__.py
│   │   ├── nodes.py                 # Graph nodes (fetch, lint, refactor, apply)
│   │   ├── state.py                 # ReviewState TypedDict schema
│   │   └── workflow.py              # StateGraph builder, compile, checkpointer setup
│   ├── services/
│   │   ├── __init__.py
│   │   ├── github_service.py        # GitHub REST API client & mock store
│   │   └── refactor_service.py      # LLM refactoring prompt & deterministic fallback
│   └── tools/
│       ├── __init__.py
│       └── linter.py                # LangChain @tool execution sandbox for flake8/black
└── tests/
    ├── __init__.py
    ├── test_api_endpoints.py        # Test Cases 1, 2, 3 verification via TestClient
    ├── test_github_service.py       # GitHub URL parsing & mock repo operations
    ├── test_graph_pipeline.py       # StateGraph pause gates, feedback loops, approvals
    ├── test_refactor_service.py     # Prompt extraction & feedback instruction tests
    ├── test_routing_and_rollback.py # Multi-turn review loops & checkpointer history
    └── test_sandbox_tool.py         # Sandbox flake8/syntax/black error isolation tests
```

---

## Installation & Setup

### 1. Prerequisites
- Python 3.11+
- Git

### 2. Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Edit `.env` to configure your API keys:
```ini
# GitHub Configuration
GITHUB_TOKEN=ghp_your_personal_access_token_here

# LLM Configuration
OPENAI_API_KEY=sk-your_openai_api_key_here
OPENAI_MODEL_NAME=gpt-4o-mini
LLM_PROVIDER=mock    # Use "mock" for offline deterministic testing, or "openai" for live LLM

# Server Configuration
APP_ENV=development
HOST=0.0.0.0
PORT=8000
DEBUG=True

# Persistence Configuration
PERSISTENCE_TYPE=memory    # "memory" or "sqlite"
CHECKPOINT_DB_PATH=./data/checkpoints.sqlite
```

### 3. Install Dependencies
```bash
# Create and activate virtual environment
python -m venv .venv
# Windows:
.\.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# Install requirements
pip install -r requirements.txt
```

### 4. Run the FastAPI Server
Start the development server with live reload:
```bash
uvicorn main:app --reload
```
The server will start at `http://127.0.0.1:8000`.

---

## Interactive API Documentation
- **Swagger UI**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
- **OpenAPI JSON**: [http://127.0.0.1:8000/openapi.json](http://127.0.0.1:8000/openapi.json) (or file `openapi.json` in repository root).

---

## Verification & Validation Test Cases Walkthrough

### Test Case 1: Webhook PR Ingestion, Linting, & HITL Pause Gate
Simulate an incoming GitHub PR webhook event:
```bash
curl -X POST "http://127.0.0.1:8000/api/webhooks/github" \
     -H "Content-Type: application/json" \
     -d '{
       "pr_url": "https://github.com/octocat/Hello-World/pull/42",
       "repository_url": "https://github.com/octocat/Hello-World",
       "branch": "feature/tax-fix"
     }'
```
**Expected Behavior**:
1. Server initializes a new thread (e.g. `review-c9b3f0...`).
2. `fetch_pr_node` retrieves modified PR files.
3. `lint_code_node` analyzes the Python code inside the isolated sandbox (`flake8`, `black`).
4. `propose_refactor_node` crafts the refactored code draft.
5. The execution **halts immediately before `apply_changes_node`** due to `interrupt_before=["apply_changes_node"]`.
6. Response status: `201 Created` with `status: "paused_for_approval"` and `next_step: "apply_changes_node"`.

---

### Test Case 2: Feedback Input & Refactoring Proposal Re-route Loop
Reject the draft and provide explicit engineering directives:
```bash
curl -X POST "http://127.0.0.1:8000/api/reviews/{thread_id}/approve" \
     -H "Content-Type: application/json" \
     -d '{
       "approved": false,
       "feedback": "Use list comprehensions instead of loops"
     }'
```
**Expected Behavior**:
1. Server writes `is_approved = False` and `reviewer_feedback = "Use list comprehensions instead of loops"` into the checkpointer state.
2. The graph loops back to `propose_refactor_node`.
3. The refactoring engine regenerates the code using the feedback (transforming loops into comprehensions).
4. The graph re-reaches the write gate and **pauses again** before `apply_changes_node`.
5. Response contains regenerated `refactored_code` demonstrating the incorporated feedback.

---

### Test Case 3: Approval and Git Commit Write Back
Submit an approval decision to authorize repository mutation:
```bash
curl -X POST "http://127.0.0.1:8000/api/reviews/{thread_id}/approve" \
     -H "Content-Type: application/json" \
     -d '{
       "approved": true
     }'
```
**Expected Behavior**:
1. Server updates checkpointer with `is_approved = True`.
2. Graph resumes and executes `apply_changes_node`.
3. The refactored code is committed back to the target branch via GitHub REST API.
4. The pipeline transitions to `END`, completing the thread (`next: ()`).
5. Response returns `status: "completed"` with commit details (`commit_sha`, `files_updated`).

---

## Running Automated Tests

Run the full automated test suite with pytest:
```bash
pytest
```
Run with verbose output and coverage:
```bash
pytest -v -s
```

### Test Coverage Highlights
- `tests/test_api_endpoints.py`: End-to-end integration test verifying Test Cases 1, 2, and 3 via FastAPI `TestClient`.
- `tests/test_graph_pipeline.py`: Unit tests for graph execution, interrupt gates, rejection rollback loops, and completion.
- `tests/test_sandbox_tool.py`: Subprocess sandbox isolation, detecting flake8 unused imports (`F401`), syntax errors (`E999`), and clean code verification.
- `tests/test_routing_and_rollback.py`: Multi-turn rejection loops and checkpoint history inspection.
- `tests/test_github_service.py`: PR URL parsing and mock repository operations.
- `tests/test_refactor_service.py`: LLM message composition and feedback handling.

---

## Docker Deployment

Build and run using Docker Compose:
```bash
docker-compose up --build
```
Or build and run the Docker container directly:
```bash
docker build -t autonomous-code-review-agent .
docker run -p 8000:8000 --env-file .env autonomous-code-review-agent
```
Check health:
```bash
curl http://localhost:8000/health
```
