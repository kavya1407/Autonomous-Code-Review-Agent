"""Custom Python Execution Sandbox Tool.

Runs code quality, linting (flake8), and formatting (black) checks
inside an isolated temporary filesystem sandbox.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from typing import Dict, Any
from langchain_core.tools import tool


def execute_sandbox_lint(code_string: str, run_black: bool = True) -> Dict[str, Any]:
    """Execute flake8 and optional black check inside a temporary sandbox directory.

    Args:
        code_string: The Python code to analyze.
        run_black: Whether to also run black formatting check.

    Returns:
        Dict containing stdout, stderr, exit codes, and whether errors were found.
    """
    if not code_string or not code_string.strip():
        return {
            "passed": True,
            "flake8_output": "",
            "black_output": "",
            "summary": "Empty code string provided. No linting errors.",
        }

    with tempfile.TemporaryDirectory(prefix="sandbox_linter_") as temp_dir:
        temp_file_path = os.path.join(temp_dir, "submission.py")
        with open(temp_file_path, "w", encoding="utf-8") as f:
            f.write(code_string)

        python_bin = sys.executable

        # 1. Run flake8
        flake8_proc = subprocess.run(
            [python_bin, "-m", "flake8", "--max-line-length=100", temp_file_path],
            capture_output=True,
            text=True,
            timeout=15,
        )
        # Normalize file path in output for clean reporting
        flake8_out = flake8_proc.stdout.replace(temp_file_path, "submission.py")
        flake8_err = flake8_proc.stderr.strip()

        # 2. Run black --check
        black_out = ""
        black_err = ""
        black_failed = False
        if run_black:
            black_proc = subprocess.run(
                [python_bin, "-m", "black", "--check", "--diff", temp_file_path],
                capture_output=True,
                text=True,
                timeout=15,
            )
            black_out = black_proc.stdout.replace(temp_file_path, "submission.py")
            black_err = black_proc.stderr.replace(temp_file_path, "submission.py")
            black_failed = black_proc.returncode != 0

        has_flake8_errors = flake8_proc.returncode != 0 or bool(flake8_out.strip())
        passed = not has_flake8_errors and not black_failed

        summary_lines = []
        if passed:
            summary_lines.append("PASSED: No linting or formatting errors detected.")
        else:
            if has_flake8_errors:
                summary_lines.append("[FLAKE8 ISSUES]")
                summary_lines.append(flake8_out.strip())
                if flake8_err:
                    summary_lines.append(f"Errors: {flake8_err}")
            if black_failed:
                summary_lines.append("[BLACK FORMATTING REQUIRED]")
                if black_out.strip():
                    summary_lines.append(black_out.strip())
                elif black_err.strip():
                    summary_lines.append(black_err.strip())

        return {
            "passed": passed,
            "has_flake8_errors": has_flake8_errors,
            "black_failed": black_failed,
            "flake8_output": flake8_out.strip(),
            "black_output": black_out.strip(),
            "summary": "\n".join(summary_lines),
        }


@tool
def run_linter_tool(code_string: str) -> str:
    """Writes python code to a temporary file and runs flake8 analysis inside a secure sandbox.

    Args:
        code_string: Python source code string to be analyzed.

    Returns:
        Formatted string containing stdout, stderr, and detected linting/formatting errors.
    """
    try:
        result = execute_sandbox_lint(code_string=code_string, run_black=True)
        return result["summary"]
    except subprocess.TimeoutExpired:
        return "ERROR: Linter execution timed out inside sandbox."
    except Exception as exc:
        return f"ERROR: Sandbox execution failed with exception: {exc}"
