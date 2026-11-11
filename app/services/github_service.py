"""GitHub API Service.

Handles interaction with the GitHub REST API for:
- Parsing GitHub PR URLs
- Fetching pull request modified files and content
- Committing refactored changes back to the PR branch
Includes a built-in mock mode for offline testing and local sandbox verification.
"""

from __future__ import annotations

import base64
import re
from typing import Dict, Any, Tuple, Optional
import httpx
from app.core.config import settings


def parse_github_pr_url(pr_url: str) -> Tuple[str, str, int]:
    """Parse owner, repo, and pull number from a GitHub PR URL.

    Supported patterns:
    - https://github.com/owner/repo/pull/123
    - https://api.github.com/repos/owner/repo/pulls/123
    - owner/repo#123

    Returns:
        (owner, repo, pull_number)
    """
    web_match = re.search(r"github\.com/([^/]+)/([^/]+)/pull/(\d+)", pr_url)
    if web_match:
        return web_match.group(1), web_match.group(2), int(web_match.group(3))

    api_match = re.search(r"repos/([^/]+)/([^/]+)/pulls/(\d+)", pr_url)
    if api_match:
        return api_match.group(1), api_match.group(2), int(api_match.group(3))

    short_match = re.match(r"^([^/]+)/([^#]+)#(\d+)$", pr_url.strip())
    if short_match:
        return short_match.group(1), short_match.group(2), int(short_match.group(3))

    raise ValueError(f"Invalid GitHub PR URL format: '{pr_url}'")


class GitHubService:
    """Service client for GitHub API operations."""

    def __init__(self, token: Optional[str] = None, base_url: str = "https://api.github.com"):
        self.token = token or settings.github_token
        self.base_url = base_url.rstrip("/")
        # In-memory mock store for test cases and offline runs
        self._mock_prs: Dict[str, Dict[str, Any]] = {}
        self._mock_commits: list[Dict[str, Any]] = []

    def register_mock_pr(
        self,
        pr_url: str,
        files: Dict[str, str],
        branch: str = "feature/refactor-branch",
        head_sha: str = "0123456789abcdef",
    ) -> None:
        """Register a mock pull request for isolated testing and offline dev."""
        self._mock_prs[pr_url] = {
            "files": files,
            "branch": branch,
            "head_sha": head_sha,
        }

    def fetch_pr_files(self, pr_url: str) -> Dict[str, str]:
        """Fetch modified files and their contents from the target PR."""
        # 1. Check in-memory mock store first
        if pr_url in self._mock_prs:
            return self._mock_prs[pr_url]["files"].copy()

        # 2. If token is missing or dummy/mock, return synthetic files or error
        if not self.token or self.token.startswith("mock_") or settings.llm_provider == "mock":
            # If we don't have a registered mock, produce a default test PR payload
            return {
                "calculator.py": (
                    "import math, sys\n"
                    "def calculate_total( items,tax_rate ):\n"
                    "    total=0\n"
                    "    for i in items:\n"
                    "        total=total+i\n"
                    "    return total+(total*tax_rate)\n"
                )
            }

        # 3. Call live GitHub REST API
        owner, repo, pull_number = parse_github_pr_url(pr_url)
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "Authorization": f"Bearer {self.token}",
        }

        with httpx.Client(base_url=self.base_url, headers=headers, timeout=15.0) as client:
            # Get list of files
            files_resp = client.get(f"/repos/{owner}/{repo}/pulls/{pull_number}/files")
            files_resp.raise_for_status()
            files_data = files_resp.json()

            code_contents: Dict[str, str] = {}
            for item in files_data:
                filename = item.get("filename", "")
                raw_url = item.get("raw_url")
                contents_url = item.get("contents_url")

                # Fetch raw file content
                if raw_url:
                    content_resp = client.get(raw_url)
                    content_resp.raise_for_status()
                    code_contents[filename] = content_resp.text
                elif contents_url:
                    content_resp = client.get(contents_url)
                    content_resp.raise_for_status()
                    file_blob = content_resp.json()
                    raw_content = base64.b64decode(file_blob.get("content", "")).decode("utf-8")
                    code_contents[filename] = raw_content

            return code_contents

    def commit_changes(
        self,
        pr_url: str,
        refactored_code: Dict[str, str],
        commit_message: str = "style: automated code review and refactoring",
    ) -> Dict[str, Any]:
        """Commit approved refactored code back to the GitHub PR branch."""
        # 1. Handle mock mode
        if pr_url in self._mock_prs or not self.token or self.token.startswith("mock_"):
            commit_record = {
                "status": "committed",
                "commit_sha": "a1b2c3d4e5f67890mockcommit",
                "pr_url": pr_url,
                "files_updated": list(refactored_code.keys()),
                "message": commit_message,
            }
            self._mock_commits.append(commit_record)
            if pr_url in self._mock_prs:
                # Update files in mock store
                self._mock_prs[pr_url]["files"].update(refactored_code)
            return commit_record

        # 2. Live GitHub REST API update
        owner, repo, pull_number = parse_github_pr_url(pr_url)
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "Authorization": f"Bearer {self.token}",
        }

        with httpx.Client(base_url=self.base_url, headers=headers, timeout=15.0) as client:
            # Get PR head branch
            pr_resp = client.get(f"/repos/{owner}/{repo}/pulls/{pull_number}")
            pr_resp.raise_for_status()
            pr_info = pr_resp.json()
            branch = pr_info["head"]["ref"]

            updated_files = []
            for filepath, content in refactored_code.items():
                # Get current file SHA on branch if it exists
                get_url = f"/repos/{owner}/{repo}/contents/{filepath}?ref={branch}"
                current_sha = None
                file_get_resp = client.get(get_url)
                if file_get_resp.status_code == 200:
                    current_sha = file_get_resp.json().get("sha")

                encoded_content = base64.b64encode(content.encode("utf-8")).decode("utf-8")
                payload: Dict[str, Any] = {
                    "message": commit_message,
                    "content": encoded_content,
                    "branch": branch,
                }
                if current_sha:
                    payload["sha"] = current_sha

                put_url = f"/repos/{owner}/{repo}/contents/{filepath}"
                put_resp = client.put(put_url, json=payload)
                put_resp.raise_for_status()
                updated_files.append(filepath)

            return {
                "status": "committed",
                "branch": branch,
                "files_updated": updated_files,
                "message": commit_message,
            }


# Default singleton instance
github_service = GitHubService()
