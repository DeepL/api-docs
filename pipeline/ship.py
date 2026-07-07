#!/usr/bin/env python3
"""
Ship pipeline-generated docs as a PR for human review.

Final step in the pipeline: after promote.py copies generated docs to their
canonical paths and updates docs.json, this script packages everything into
a branch and opens a PR via `gh`.

Usage:
    python pipeline/ship.py --run pipeline/drafts/20260706-192742
    python pipeline/ship.py --latest
    python pipeline/ship.py --latest --dry-run
    python pipeline/ship.py --latest --branch docs/my-custom-branch
    python pipeline/ship.py --latest --yes          # skip push confirmation
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent

STAGE_PATTERNS = [
    "docs/**/*.mdx",
    "docs.json",
]


def run(cmd, check=True, capture=True, **kwargs):
    """Run a subprocess command and return the result."""
    result = subprocess.run(
        cmd,
        capture_output=capture,
        text=True,
        cwd=REPO_ROOT,
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


def load_report(run_dir):
    """Load report.json from a run directory."""
    report_path = run_dir / "report.json"
    if not report_path.exists():
        return None
    with open(report_path) as f:
        return json.load(f)


def get_docs_changes():
    """Get the list of docs-related changed files from git status."""
    result = run(["git", "status", "--porcelain"], check=False)
    if result.returncode != 0:
        return []
    changes = []
    for line in result.stdout.strip().splitlines():
        if not line:
            continue
        # status is first two chars, then a space, then the path
        filepath = line[3:].strip()
        # Handle renames: "old -> new"
        if " -> " in filepath:
            filepath = filepath.split(" -> ")[1]
        if filepath.startswith("docs/") or filepath == "docs.json":
            changes.append(filepath)
    return changes


def get_current_branch():
    """Get the current git branch name."""
    result = run(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    return result.stdout.strip()


def branch_exists(branch_name):
    """Check if a local branch already exists."""
    result = run(["git", "rev-parse", "--verify", branch_name], check=False)
    return result.returncode == 0


def check_gh_available():
    """Check that the gh CLI is installed and authenticated."""
    result = run(["which", "gh"], check=False)
    if result.returncode != 0:
        return False, "gh CLI not found. Install it: https://cli.github.com/"
    result = run(["gh", "auth", "status"], check=False)
    if result.returncode != 0:
        return False, "gh CLI not authenticated. Run: gh auth login"
    return True, ""


def build_commit_message(report, run_id):
    """Build a structured commit message from the report."""
    generated = report.get("generated", [])
    families = sorted(set(
        g["gap"].get("family", "unknown")
        for g in generated
        if g.get("gap")
    ))

    family_str = ", ".join(families) if families else "docs"
    subject = f"docs: add generated pages from pipeline run {run_id}"

    body_lines = [f"Generated {len(generated)} pages for: {family_str}"]
    for g in generated:
        path = g.get("path", "")
        desc = g.get("gap", {}).get("description", "")
        if path:
            body_lines.append(f"  - {path}: {desc}")

    return subject + "\n\n" + "\n".join(body_lines)


def build_pr_body(report, run_id, changed_files):
    """Build the PR description body."""
    generated = report.get("generated", [])
    errors = report.get("errors", [])

    # Pages section
    page_lines = []
    for g in generated:
        path = g.get("path", "")
        gap = g.get("gap", {})
        family = gap.get("family", "")
        gap_type = gap.get("type", "")
        action = g.get("action", "")

        label = ""
        if gap_type == "undocumented_product":
            label = f"{family} overview (new)"
        elif gap_type == "missing_orientation":
            label = f"{family} overview (new)"
        elif gap_type == "missing_tutorial":
            label = f"{family} tutorial (new)"
        elif gap_type == "thin_page":
            label = "expanded thin page"
        elif gap_type == "missing_code_examples":
            label = "added code examples"
        elif gap_type == "missing_description":
            label = "added frontmatter description"
        else:
            label = gap_type

        if path:
            page_lines.append(f"- `{path}` — {label}")

    pages_section = "\n".join(page_lines) if page_lines else "- (none)"

    # Quality checks
    quality_lines = []
    if errors:
        quality_lines.append(f"- Generation errors: {len(errors)}")
        for e in errors[:5]:
            quality_lines.append(f"  - {e.get('error', 'unknown')}")
    else:
        quality_lines.append("- Generation: all pages generated successfully")

    quality_section = "\n".join(quality_lines)

    families = sorted(set(
        g["gap"].get("family", "unknown")
        for g in generated
        if g.get("gap")
    ))

    body = f"""## Summary
Generated documentation pages from the agentic docs pipeline (run `{run_id}`).

Families: {", ".join(families) if families else "N/A"}
Model: {report.get("model", "N/A")}

### Pages added/updated
{pages_section}

### Quality checks
{quality_section}

## How to review
1. Check out this branch and run `mint dev` to preview locally
2. Review each page for accuracy and tone
3. Verify navigation in docs.json makes sense

---
Generated by the agentic docs pipeline (`pipeline/generate.py`)"""

    return body


def main():
    parser = argparse.ArgumentParser(
        description="Ship pipeline-generated docs as a PR"
    )
    run_group = parser.add_mutually_exclusive_group(required=True)
    run_group.add_argument(
        "--run",
        help="Path to the draft run directory (e.g. pipeline/drafts/20260706-192742)",
    )
    run_group.add_argument(
        "--latest", action="store_true",
        help="Auto-pick the most recent run",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Show what would happen without doing it",
    )
    parser.add_argument(
        "--branch",
        help="Custom branch name (default: auto-generate from run ID)",
    )
    parser.add_argument(
        "--yes", action="store_true",
        help="Skip push confirmation prompt",
    )
    args = parser.parse_args()

    # --- Resolve run directory ---
    if args.latest:
        run_dir = find_latest_run()
        if not run_dir:
            print("Error: no runs found in pipeline/drafts/")
            return 1
        print(f"Using latest run: {run_dir.relative_to(REPO_ROOT)}")
    else:
        run_dir = Path(args.run)
        if not run_dir.is_absolute():
            run_dir = REPO_ROOT / run_dir
        if not run_dir.exists():
            print(f"Error: run directory not found: {run_dir}")
            return 1

    run_id = run_dir.name

    # --- Load report ---
    report = load_report(run_dir)
    if not report:
        print(f"Warning: no report.json in {run_dir.relative_to(REPO_ROOT)}, proceeding without it")
        report = {"generated": [], "errors": [], "run_id": run_id, "model": "unknown"}

    # --- Pre-flight checks ---
    print("Pre-flight checks...")

    # Check for docs changes
    changed_files = get_docs_changes()
    if not changed_files:
        print("Error: no docs-related changes in working tree.")
        print("Run promote.py first to copy drafts to their canonical paths.")
        return 1
    print(f"  Found {len(changed_files)} docs-related changed files")

    # Check gh CLI
    gh_ok, gh_err = check_gh_available()
    if not gh_ok:
        print(f"Error: {gh_err}")
        return 1
    print("  gh CLI: OK")

    # --- Determine branch ---
    current_branch = get_current_branch()
    branch_name = args.branch or f"docs/pipeline-{run_id}"
    need_new_branch = current_branch in ("main", "master")

    if not need_new_branch and current_branch != branch_name:
        # Already on a feature branch, use it
        branch_name = current_branch
        print(f"  Using current branch: {branch_name}")
    elif need_new_branch:
        print(f"  Will create branch: {branch_name}")
    else:
        print(f"  On branch: {branch_name}")

    # --- Build commit message and PR body ---
    commit_msg = build_commit_message(report, run_id)
    pr_title = f"docs: pipeline-generated pages ({', '.join(sorted(set(g['gap'].get('family', '?') for g in report.get('generated', []) if g.get('gap'))))})"
    if len(pr_title) > 70:
        families = sorted(set(
            g["gap"].get("family", "?")
            for g in report.get("generated", [])
            if g.get("gap")
        ))
        pr_title = f"docs: pipeline-generated pages ({len(families)} families)"
    pr_body = build_pr_body(report, run_id, changed_files)

    # --- Dry run ---
    if args.dry_run:
        print("\n--- DRY RUN ---\n")
        print(f"Branch: {branch_name}")
        print(f"Files to stage ({len(changed_files)}):")
        for f in changed_files:
            print(f"  {f}")
        print(f"\nCommit message:\n{commit_msg}")
        print(f"\nPR title: {pr_title}")
        print(f"\nPR body:\n{pr_body}")
        print("\n--- END DRY RUN ---")
        return 0

    # --- Create branch ---
    if need_new_branch:
        if branch_exists(branch_name):
            print(f"Error: branch {branch_name} already exists locally.")
            print(f"Use --branch to pick a different name, or switch to it with git checkout.")
            return 1
        print(f"Creating branch: {branch_name}")
        run(["git", "checkout", "-b", branch_name])

    # --- Stage and commit ---
    print("Staging docs files...")
    for pattern in STAGE_PATTERNS:
        run(["git", "add", pattern], check=False)

    # Verify something is staged
    staged = run(["git", "diff", "--cached", "--name-only"])
    if not staged.stdout.strip():
        print("Error: nothing staged after git add. Check that changed files match staging patterns.")
        return 1

    staged_files = staged.stdout.strip().splitlines()
    print(f"  Staged {len(staged_files)} files")

    print("Committing...")
    run(["git", "commit", "-m", commit_msg])
    print("  Committed.")

    # --- Push ---
    if not args.yes:
        print(f"\nReady to push branch '{branch_name}' and create a PR.")
        try:
            answer = input("Push and create PR? [y/N] ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\nAborted.")
            return 1
        if answer not in ("y", "yes"):
            print("Aborted. Your commit is saved locally.")
            print(f"To push later: git push -u origin {branch_name}")
            return 0

    print(f"Pushing branch: {branch_name}")
    run(["git", "push", "-u", "origin", branch_name])

    # --- Create PR ---
    print("Creating PR...")
    result = run([
        "gh", "pr", "create",
        "--title", pr_title,
        "--body", pr_body,
    ])

    pr_url = result.stdout.strip()
    print(f"\nPR created: {pr_url}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
