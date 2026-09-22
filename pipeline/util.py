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


def load_agent(path):
    """Load an agent file's prose, minus its YAML frontmatter.

    The .claude/agents/*.md files are agent definitions: the frontmatter declares
    `tools: Read, Write, Grep, Glob, ...` and the body is written for a harness
    where those exist. Pasted verbatim into a plain API call they tell the model
    it can search the repo, so it obliges by inventing tool calls and returns a
    transcript instead of a page. Drop the frontmatter here; NO_TOOLS below
    overrides what the body still assumes.
    """
    text = load_text(path)
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            return text[end + 4:].lstrip("\n")
    return text


NO_TOOLS = """## No Tools In This Context

You are called through the API with no tools available:

- Ignore any instruction above to read files, search with Grep or Glob, browse the
  web, or delegate to another agent. Everything you need is in this prompt, and
  there is nothing else to look up.
- Never emit tool calls, tool results, or a note about research you are about to do.
  A reply that opens with "I'll research..." or "Let me read..." is a failed reply.
- Where the guidelines say to return content "using Write or Edit", they mean: put
  the content in your reply, and nothing else."""


def looks_like_mdx(text):
    """Whether a reply is a page, rather than commentary or a faked transcript."""
    stripped = (text or "").lstrip()
    if not stripped.startswith("---"):
        return False
    return stripped.find("\n---", 3) != -1  # frontmatter block is closed


def format_retry_prompt(problem):
    """Corrective turn for a reply that came back in the wrong shape.

    The agent guidelines are written for a tool-equipped harness, so the model
    sometimes follows them into narrating research it cannot do. One plain
    correction recovers that far more safely than trying to cut a page out of a
    transcript, which can splice in content the model quoted from elsewhere.
    """
    return f"""Your previous reply was not usable: {problem}

Reply again with the content only. No preamble, no commentary, no tool calls, no
markdown fences, and no explanation of what you changed."""


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

{load_agent(DOCS_WRITER_PATH)}

## Diataxis Framework

{load_agent(DIATAXIS_PATH)}

## Information Architecture

{load_agent(DOCS_IA_PATH)}

{NO_TOOLS}

{OUTPUT_RULES}"""


def build_review_system_prompt():
    """System prompt for the review step."""
    return f"""You are a documentation reviewer for DeepL's developer documentation.

Review .mdx drafts against the guidelines below and return structured findings as JSON.

## Style Guide (CLAUDE.md)

{load_text(CLAUDE_MD_PATH)}

## Editorial Review Criteria

{load_agent(EDITORIAL_REVIEWER_PATH)}

## Diataxis Framework and Review Criteria

{load_agent(DIATAXIS_PATH)}

## Information Architecture

{load_agent(DOCS_IA_PATH)}

{NO_TOOLS}
"""


def load_planning_context():
    """IA + Diataxis prose for the batch planner, so its routing rules aren't a
    third hand-maintained copy of the content-type rules."""
    return (
        f"## Information Architecture\n\n{load_agent(DOCS_IA_PATH)}\n\n"
        f"## Diataxis Framework\n\n{load_agent(DIATAXIS_PATH)}"
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
