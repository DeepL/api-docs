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


# --------------------------------------------------------------------------- #
# Prompt assembly — the ONE place output behavior is controlled.               #
#                                                                              #
# Every pipeline step that talks to the model builds its prompt here, from the #
# agent files below. To change how docs read, edit those files — not the       #
# Python. The .md files are human-usable on their own (they're the same        #
# instructions a person authoring or reviewing docs by hand would follow).     #
# --------------------------------------------------------------------------- #

AGENTS_DIR = REPO_ROOT / ".claude" / "agents"
CLAUDE_MD_PATH = REPO_ROOT / "CLAUDE.md"
DOCS_WRITER_PATH = AGENTS_DIR / "docs-writer.md"      # how to write
DIATAXIS_PATH = AGENTS_DIR / "diataxis.md"            # the four content types
DOCS_IA_PATH = AGENTS_DIR / "docs-ia.md"              # site structure + placement
EDITORIAL_REVIEWER_PATH = AGENTS_DIR / "editorial-reviewer.md"  # review rubric


def load_text(path):
    try:
        return Path(path).read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


OUTPUT_RULES = """## Output Format

- Output ONLY the .mdx file content. No commentary, no explanation, no markdown fences.
- Start with frontmatter (---). Every page MUST have `title` and `description`
  (description under 160 chars, specific, not generic).
- Serve the Diataxis type appropriate for the page (overview/landing pages are exempt).
- Never invent API parameters or behavior. Only document what the source content or the
  OpenAPI spec provides."""


def build_authoring_system_prompt(role):
    """System prompt for any step that WRITES docs (generate, rework).

    All substance comes from the agent files so there is a single place to change it.
    """
    return f"""{role}

You write .mdx files for a Mintlify-powered docs site. The docs-writer guidelines are
your primary instructions. CLAUDE.md provides general writing principles. When they
conflict, the docs-writer guidelines win.

## Style Guide (CLAUDE.md)

{load_text(CLAUDE_MD_PATH)}

## Docs Writer Guidelines

{load_text(DOCS_WRITER_PATH)}

## Diataxis Framework

{load_text(DIATAXIS_PATH)}

## Information Architecture

{load_text(DOCS_IA_PATH)}

{OUTPUT_RULES}"""


def build_review_system_prompt():
    """System prompt for the review step."""
    return f"""You are a documentation reviewer for DeepL's developer documentation.

Review .mdx drafts against the guidelines below and return structured findings as JSON.

## Style Guide (CLAUDE.md)

{load_text(CLAUDE_MD_PATH)}

## Editorial Review Criteria

{load_text(EDITORIAL_REVIEWER_PATH)}

## Diataxis Framework and Review Criteria

{load_text(DIATAXIS_PATH)}

## Information Architecture

{load_text(DOCS_IA_PATH)}
"""


def load_planning_context():
    """IA + Diataxis prose for the batch planner, so its routing rules aren't a
    third hand-maintained copy of the content-type rules."""
    return (
        f"## Information Architecture\n\n{load_text(DOCS_IA_PATH)}\n\n"
        f"## Diataxis Framework\n\n{load_text(DIATAXIS_PATH)}"
    )


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
