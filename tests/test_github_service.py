"""Unit tests for GitHub service client and URL parsing."""

import pytest
from app.services.github_service import GitHubService, parse_github_pr_url


def test_parse_github_pr_url_variations():
    """Test extracting owner, repo, and PR number from standard URLs."""
    url1 = "https://github.com/octocat/Hello-World/pull/42"
    assert parse_github_pr_url(url1) == ("octocat", "Hello-World", 42)

    url2 = "https://api.github.com/repos/my-org/my-repo/pulls/108"
    assert parse_github_pr_url(url2) == ("my-org", "my-repo", 108)

    url3 = "owner/repo#7"
    assert parse_github_pr_url(url3) == ("owner", "repo", 7)

    with pytest.raises(ValueError):
        parse_github_pr_url("invalid-url-string")


def test_github_service_mock_fetch_and_commit():
    """Verify mock PR registration, file fetching, and commit generation."""
    service = GitHubService(token="mock_token")
    pr_url = "https://github.com/test-org/test-project/pull/1"
    initial_files = {"main.py": "def foo(): pass\n"}

    service.register_mock_pr(pr_url, initial_files, branch="feature/test")

    # Fetch
    fetched = service.fetch_pr_files(pr_url)
    assert fetched == initial_files

    # Commit
    refactored = {"main.py": "def foo() -> None:\n    return None\n"}
    commit_res = service.commit_changes(pr_url, refactored, "refactor: type annotations")

    assert commit_res["status"] == "committed"
    assert "main.py" in commit_res["files_updated"]
    # Check that mock store was updated
    assert service.fetch_pr_files(pr_url) == refactored
