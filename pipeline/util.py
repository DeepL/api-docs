"""Shared utilities for the docs pipeline."""

import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent

STAGE_PATTERNS = [
    "docs/**/*.mdx",
    "api-reference/**/*.mdx",
    "docs.json",
]


def run_cmd(cmd, check=True, capture=True, **kwargs):
    """Run a subprocess command and return the result."""
    result = subprocess.run(
        cmd,
        capture_output=capture,
        text=True,
        cwd=kwargs.pop("cwd", REPO_ROOT),
        **kwargs,
    )
    if check and result.returncode != 0:
        stderr = result.stderr.strip() if result.stderr else ""
        raise RuntimeError(f"Command failed: {' '.join(cmd)}\n{stderr}")
    return result


def find_latest_run():
    """Find the most recent draft run directory."""
    drafts_dir = REPO_ROOT / "pipeline" / "drafts"
    if not drafts_dir.exists():
        return None
    runs = sorted(
        [d for d in drafts_dir.iterdir() if d.is_dir()],
        key=lambda d: d.stat().st_mtime,
    )
    return runs[-1] if runs else None


def get_docs_changes():
    """Get the list of docs-related changed files from git status."""
    result = run_cmd(["git", "status", "--porcelain"], check=False)
    if result.returncode != 0:
        return []
    changes = []
    for line in result.stdout.strip().splitlines():
        if not line:
            continue
        filepath = line[3:].strip()
        if " -> " in filepath:
            filepath = filepath.split(" -> ")[1]
        if filepath.startswith(("docs/", "api-reference/")) or filepath == "docs.json":
            changes.append(filepath)
    return changes


def get_current_branch():
    """Get the current git branch name."""
    result = run_cmd(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    return result.stdout.strip()


def branch_exists(branch_name):
    """Check if a local branch already exists."""
    result = run_cmd(["git", "rev-parse", "--verify", branch_name], check=False)
    return result.returncode == 0


def check_gh_available():
    """Check that the gh CLI is installed and authenticated."""
    result = run_cmd(["which", "gh"], check=False)
    if result.returncode != 0:
        return False, "gh CLI not found. Install it: https://cli.github.com/"
    result = run_cmd(["gh", "auth", "status"], check=False)
    if result.returncode != 0:
        return False, "gh CLI not authenticated. Run: gh auth login"
    return True, ""


def stage_and_commit_docs(commit_msg):
    """Stage docs changes and commit. Returns (success, num_files)."""
    for pattern in STAGE_PATTERNS:
        run_cmd(["git", "add", pattern], check=False)

    staged = run_cmd(["git", "diff", "--cached", "--name-only"])
    if not staged.stdout.strip():
        return False, 0

    num_files = len(staged.stdout.strip().splitlines())
    run_cmd(["git", "commit", "-m", commit_msg])
    return True, num_files


def push_and_create_pr(branch, title, body):
    """Push branch and create/find a PR. Returns PR URL or None on failure."""
    result = run_cmd(["git", "push", "-u", "origin", branch], check=False)
    if result.returncode != 0:
        return None

    # Check if a PR already exists for this branch
    existing = run_cmd(
        ["gh", "pr", "view", branch, "--json", "url", "-q", ".url"],
        check=False,
    )
    if existing.returncode == 0 and existing.stdout.strip():
        return existing.stdout.strip()

    result = run_cmd(
        ["gh", "pr", "create", "--title", title, "--body", body, "--base", "main"],
        check=False,
    )
    if result.returncode != 0:
        print(f"PR creation failed: {result.stderr.strip()}")
        return None

    return result.stdout.strip()
