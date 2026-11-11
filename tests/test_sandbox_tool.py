"""Unit tests for the custom execution sandbox tool."""

from app.tools.linter import run_linter_tool, execute_sandbox_lint


def test_sandbox_detects_flake8_errors():
    """Verify that unused imports and formatting violations are flagged."""
    bad_code = (
        "import sys, os\n"  # multiple imports on one line, unused
        "def bad_func( x,y ):\n"  # bad whitespace
        "    result=x+y\n"  # missing whitespace around operator
        "    return result\n"
    )

    result = execute_sandbox_lint(bad_code)
    assert not result["passed"]
    assert result["has_flake8_errors"]
    assert "submission.py" in result["summary"]
    # Should flag multiple imports (E401) or unused import (F401)
    assert "F401" in result["summary"] or "E401" in result["summary"] or "E2" in result["summary"]


def test_sandbox_detects_syntax_errors():
    """Verify that Python syntax errors are caught cleanly."""
    syntax_error_code = "def broken_func(\n    return 42\n"

    result = execute_sandbox_lint(syntax_error_code)
    assert not result["passed"]
    assert "SyntaxError" in result["summary"] or "E999" in result["summary"]


def test_sandbox_passes_clean_code():
    """Verify that properly formatted code with no violations passes."""
    clean_code = (
        '"""Clean module docstring."""\n\n\n'
        "def add(a: int, b: int) -> int:\n"
        '    """Add two numbers."""\n'
        "    return a + b\n"
    )

    result = execute_sandbox_lint(clean_code, run_black=False)
    assert result["passed"]
    assert "PASSED" in result["summary"]


def test_langchain_tool_invocation():
    """Verify that the tool decorator allows standard LangChain tool invocation."""
    code_with_issue = "import os\n"  # Unused import
    output = run_linter_tool.invoke({"code_string": code_with_issue})

    assert isinstance(output, str)
    assert "F401" in output or "FLAKE8" in output
