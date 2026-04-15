"""GitHub PR tools — SRP: pull request creation only."""
import os
from github import Github, GithubException
from langchain_core.tools import tool


@tool
def create_pull_request(
    branch_name: str,
    title: str,
    body: str,
    base_branch: str = "main",
) -> str:
    """
    Open a GitHub Pull Request from *branch_name* into *base_branch*.

    Returns the URL of the created PR.

    Args:
        branch_name:  Head branch with the fix (e.g. ``fix/issue-42-add-guard``).
        title:        PR title (typically mirrors the issue title).
        body:         PR description — include a ``Closes #N`` reference so
                      GitHub auto-closes the issue when the PR merges.
        base_branch:  Target branch (default ``main``).
    """
    try:
        token = os.environ.get("GITHUB_TOKEN")
        if not token:
            raise EnvironmentError("GITHUB_TOKEN environment variable is not set.")

        repo_name = os.environ.get("GITHUB_REPOSITORY")
        if not repo_name:
            raise EnvironmentError("GITHUB_REPOSITORY environment variable is not set.")

        client = Github(token)
        repo = client.get_repo(repo_name)
        pr = repo.create_pull(
            title=title,
            body=body,
            head=branch_name,
            base=base_branch,
        )
        return f"Pull Request opened: {pr.html_url}"

    except GithubException as exc:
        return f"GitHub API error while creating PR: {exc.data}"
    except Exception as exc:
        return f"Error creating PR: {exc}"


def get_pr_tools() -> list:
    """Return GitHub PR LangChain tools."""
    return [create_pull_request]
