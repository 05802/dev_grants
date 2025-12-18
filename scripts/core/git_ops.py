"""
Git operations helper for GrantOps.

Provides utilities for branching, committing, and managing Git state
within GitHub Actions workflows.
"""

import subprocess
from pathlib import Path
from typing import Optional


def get_repo_root() -> Path:
    """Get the repository root directory."""
    current = Path(__file__).resolve()
    return current.parent.parent.parent


def run_git(args: list[str], check: bool = True) -> subprocess.CompletedProcess:
    """
    Run a git command in the repository root.

    Args:
        args: Git command arguments (without 'git' prefix)
        check: Whether to raise on non-zero exit

    Returns:
        CompletedProcess with stdout/stderr
    """
    return subprocess.run(
        ["git"] + args,
        cwd=get_repo_root(),
        capture_output=True,
        text=True,
        check=check,
    )


def get_current_branch() -> str:
    """Get the name of the current Git branch."""
    result = run_git(["rev-parse", "--abbrev-ref", "HEAD"])
    return result.stdout.strip()


def branch_exists(branch_name: str) -> bool:
    """Check if a branch exists (locally or remotely)."""
    result = run_git(
        ["rev-parse", "--verify", branch_name],
        check=False
    )
    return result.returncode == 0


def create_branch(branch_name: str, checkout: bool = True) -> bool:
    """
    Create a new branch and optionally check it out.

    Args:
        branch_name: Name for the new branch
        checkout: Whether to checkout the branch after creation

    Returns:
        True if branch was created, False if it already existed
    """
    if branch_exists(branch_name):
        if checkout:
            run_git(["checkout", branch_name])
        return False

    if checkout:
        run_git(["checkout", "-b", branch_name])
    else:
        run_git(["branch", branch_name])

    return True


def checkout_branch(branch_name: str) -> None:
    """Checkout an existing branch."""
    run_git(["checkout", branch_name])


def commit_changes(
    files: list[str],
    message: str,
    author: Optional[str] = None,
) -> str:
    """
    Stage files and create a commit.

    Args:
        files: List of file paths (relative to repo root) to stage
        message: Commit message
        author: Optional author string (format: "Name <email>")

    Returns:
        The commit SHA
    """
    # Stage files
    for file in files:
        run_git(["add", file])

    # Build commit command
    commit_args = ["commit", "-m", message]
    if author:
        commit_args.extend(["--author", author])

    run_git(commit_args)

    # Get the commit SHA
    result = run_git(["rev-parse", "HEAD"])
    return result.stdout.strip()


def push_branch(branch_name: Optional[str] = None, set_upstream: bool = True) -> None:
    """
    Push the current or specified branch to origin.

    Args:
        branch_name: Branch to push (default: current branch)
        set_upstream: Whether to set upstream tracking
    """
    if branch_name is None:
        branch_name = get_current_branch()

    push_args = ["push"]
    if set_upstream:
        push_args.extend(["-u", "origin", branch_name])
    else:
        push_args.extend(["origin", branch_name])

    run_git(push_args)


def get_changed_files() -> list[str]:
    """Get list of modified/untracked files."""
    # Get modified files
    result = run_git(["status", "--porcelain"])
    files = []
    for line in result.stdout.strip().split("\n"):
        if line:
            # Format is "XY filename" where X is index status, Y is worktree status
            files.append(line[3:])
    return files


def generate_branch_name(prefix: str, identifier: str, version: int = 1) -> str:
    """
    Generate a branch name following GrantOps conventions.

    Args:
        prefix: Branch prefix (e.g., 'draft', 'eval')
        identifier: Section or task identifier
        version: Version number

    Returns:
        Branch name like 'draft/project_narrative-v1'
    """
    return f"{prefix}/{identifier}-v{version}"


def get_next_version(prefix: str, identifier: str) -> int:
    """
    Find the next available version number for a branch.

    Args:
        prefix: Branch prefix
        identifier: Section identifier

    Returns:
        Next available version number
    """
    result = run_git(["branch", "-a"], check=False)
    branches = result.stdout.strip().split("\n")

    pattern = f"{prefix}/{identifier}-v"
    max_version = 0

    for branch in branches:
        branch = branch.strip().replace("* ", "").replace("remotes/origin/", "")
        if pattern in branch:
            try:
                version = int(branch.split("-v")[-1])
                max_version = max(max_version, version)
            except ValueError:
                continue

    return max_version + 1
