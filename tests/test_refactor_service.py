"""Unit tests for the refactoring service."""

from unittest.mock import MagicMock
from langchain_core.messages import AIMessage
from app.services.refactor_service import RefactorService, extract_code_from_markdown


def test_extract_code_from_markdown():
    """Verify markdown code block extraction."""
    md = "Here is the code:\n```python\nx = 10\nprint(x)\n```\nEnjoy!"
    extracted = extract_code_from_markdown(md)
    assert extracted.strip() == "x = 10\nprint(x)"

    raw = "x = 10\nprint(x)"
    assert extract_code_from_markdown(raw).strip() == "x = 10\nprint(x)"


def test_deterministic_refactor_feedback_handling():
    """Verify that feedback mentioning list comprehensions triggers comprehension generation."""
    service = RefactorService()
    files = {"calc.py": "def calc(): pass"}

    # Without feedback
    draft_1 = service.refactor_all_files(files, lint_errors="E401")
    assert "calc.py" in draft_1
    assert "calculate_total" in draft_1["calc.py"]

    # With feedback
    draft_2 = service.refactor_all_files(
        files,
        lint_errors="E401",
        reviewer_feedback="Use list comprehensions instead of loops",
    )
    assert "sum([item for item in items])" in draft_2["calc.py"]


def test_llm_invocation_flow():
    """Verify that a passed ChatModel is properly invoked with prompt messages."""
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = AIMessage(content="```python\ndef refactored():\n    return True\n```")

    service = RefactorService(llm=mock_llm)
    result = service.refactor_file("sample.py", "def broken(): pass", "E999")

    mock_llm.invoke.assert_called_once()
    assert "def refactored():" in result
