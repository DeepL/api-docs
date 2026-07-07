#!/usr/bin/env python3
"""
Batch runner for IA Phase 2 cleanup tasks.

Iterates over freeform task descriptions, uses Claude to plan each one
(resolve file paths and output targets), then runs each through the full
pipeline: rework → evaluate → review → promote → ship.

Usage:
    python pipeline/batch.py --plan              # Plan all tasks, show resolved args
    python pipeline/batch.py --dry-run           # Plan + dry-run each pipeline step
    python pipeline/batch.py                     # Run all tasks end-to-end
    python pipeline/batch.py --start 3           # Start from task 3 (0-indexed)
    python pipeline/batch.py --only 1,3,5        # Run specific tasks by index
    python pipeline/batch.py --skip ship         # Skip the ship step (local review only)
    python pipeline/batch.py --skip ship,post_review
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

try:
    import anthropic
except ImportError:
    print("Install the Anthropic SDK: pip install anthropic")
    sys.exit(1)


REPO_ROOT = Path(__file__).resolve().parent.parent
MODEL = "claude-sonnet-4-6"

# Phase 2 tasks from the IA Proposal (Confluence page 1419116546).
# Each is a freeform description. The planning step resolves file paths.
TASKS = [
    (
        "Consolidate API Reference overviews: remove standalone overview pages "
        "from the API Reference tab. Fold any useful content into the first "
        "endpoint page of each group or into the Documentation tab overview. "
        "No more narrative pages in the API Reference."
    ),
    (
        "Consolidate onboarding: rework Introduction as orientation page "
        "(absorb About content). Rework Your First API Request as the single "
        "canonical tutorial (absorb best of DeepL 101). Retire About and DeepL 101 (redirect)."
    ),
    (
        "Consolidate error handling: rework Error Handling (Going to Production) "
        "as single authoritative page. Rework Document Translations to cover "
        "doc-specific issues only, link to Error Handling for HTTP errors. "
        "Dedup Pre-production checklist (replace inline error content with links)."
    ),
    (
        "Merge XML + Structured Content into one 'Handle XML content' how-to. "
        "Cut duplication. Retire the standalone XML page (redirect)."
    ),
    (
        "Split Tag Handling v2: keep explanation as 'How tag handling works'. "
        "Extract migration how-to into Handle XML content or a separate page."
    ),
    (
        "Merge CORS + Proxy: rework Solve CORS errors as concise how-to "
        "(diagnose, options, pick one). Merge proxy implementation into "
        "Build a translation proxy cookbook. Cross-link."
    ),
    (
        "Split Custom Instructions: keep how-to as 'Write effective instructions'. "
        "Fold reference content (constraints, supported languages) into "
        "API Reference Style Rules overview."
    ),
    (
        "Retire Authentication page: fold how-to content (get key, set header, verify) "
        "into Your First API Request. Move reference content (auth model, free vs paid "
        "endpoints, key types) into the Admin API overview. Retire page (redirect)."
    ),
    (
        "Rework Manage API keys: strip reference content (CSV spec, time periods). "
        "Keep how-to walkthrough with screenshots. Fold relevant FAQ as tips."
    ),
    (
        "Rework Translate text (Translation Beginner's Guide): rework as product-specific "
        "tutorial under Text Translation. Cut overlap with Your First API Request."
    ),
    (
        "Rework Set up a glossary (Glossaries in the Real World): rework as focused "
        "tutorial. Keep scenario-based approach, tighten scope."
    ),
    (
        "Rework Solve CORS errors: rework as how-to format — diagnose the error, "
        "understand options, pick one. Link to proxy cookbook."
    ),
    "Rework Handle HTML content: rework as focused how-to.",
    "Rework DeepL CLI: focus on setup + first use. Cut feature reference.",
    "Rework MCP Server: focus on setup.",
    (
        "Expand Google Sheets cookbook: currently 1 paragraph + GitHub link. "
        "Expand into real walkthrough with inline steps."
    ),
    (
        "Expand Usage Dashboard (Usage Analytics Dashboard): currently a showcase. "
        "Rework as step-by-step how-to."
    ),
    (
        "Expand Detect Languages (Language Detection): currently 3 sentences. "
        "Expand as how-to. Incorporate Detect Language beta content when public."
    ),
]


def get_docs_listing():
    """Get the list of all .mdx files in the docs directory."""
    result = subprocess.run(
        ["find", "docs", "-name", "*.mdx"],
        capture_output=True, text=True, cwd=REPO_ROOT,
    )
    return sorted(result.stdout.strip().splitlines())


PLAN_SYSTEM_PROMPT = """\
You are a planning assistant for a docs pipeline. Given a freeform task \
description and a list of docs files, resolve the task into concrete file paths.

Output valid JSON with these fields:
- "sources": list of file paths to read as input (must exist in the file list)
- "targets": list of file paths to write as output (can be existing or new paths)
- "retire": list of file paths to delete after the task (pages being retired/merged away). \
Only include files that should be REMOVED, not files being rewritten in place.
- "label": short kebab-case label for this run (e.g. "consolidate-onboarding")

Rules:
- All paths are relative to the repo root (e.g. "docs/getting-started/about.mdx")
- Sources must be actual files from the provided file list
- Targets that are existing files will be overwritten with new content
- Targets that don't exist yet will be created
- For retire tasks, the source being retired goes in "retire", and the files \
absorbing its content go in both "sources" and "targets"
- For rework/expand tasks where a page is rewritten in place, source and target are the same path
- Output ONLY the JSON object, no explanation"""


def plan_task(client, task_description, docs_files):
    """Use Claude to resolve a freeform task into structured pipeline args."""
    file_list = "\n".join(docs_files)

    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=PLAN_SYSTEM_PROMPT,
        messages=[{
            "role": "user",
            "content": (
                f"## Task\n\n{task_description}\n\n"
                f"## Available docs files\n\n```\n{file_list}\n```"
            ),
        }],
    )

    text = response.content[0].text.strip()

    # Strip markdown code fences if present
    if "```" in text:
        # Find content between first ``` and last ```
        start = text.index("```")
        first_newline = text.index("\n", start)
        end = text.rindex("```")
        text = text[first_newline + 1:end].strip()

    # Find the JSON object in the response
    brace_start = text.find("{")
    brace_end = text.rfind("}")
    if brace_start != -1 and brace_end != -1:
        text = text[brace_start:brace_end + 1]

    return json.loads(text)


def run_pipeline(plan, task_description, dry_run=False, skip_steps=None):
    """Run the full pipeline for a single planned task.

    Returns True on success, False on failure.
    """
    skip_steps = skip_steps or set()

    cmd = [
        sys.executable, str(REPO_ROOT / "pipeline" / "run.py"),
        "rework", "rework",
        "--source", *plan["sources"],
        "--instruction", task_description,
        "--label", plan["label"],
    ]

    if plan["targets"]:
        cmd.extend(["--target", *plan["targets"]])

    if dry_run:
        cmd.append("--dry-run")

    for step in skip_steps:
        cmd.extend(["--skip", step])

    print(f"\n{'='*60}")
    print(f"  CMD: {' '.join(cmd)}")
    print(f"{'='*60}\n")

    result = subprocess.run(cmd, cwd=REPO_ROOT)

    if result.returncode != 0:
        return False

    # Write retire.json if there are pages to delete
    if plan.get("retire") and not dry_run:
        drafts_dir = REPO_ROOT / "pipeline" / "drafts"
        if drafts_dir.exists():
            runs = sorted(
                [d for d in drafts_dir.iterdir() if d.is_dir()],
                key=lambda d: d.stat().st_mtime,
            )
            if runs:
                retire_path = runs[-1] / "retire.json"
                if not retire_path.exists():
                    retire_path.write_text(json.dumps(plan["retire"], indent=2))
                    print(f"  Pages to retire: {', '.join(plan['retire'])}")

    return True


def checkout_base_branch(base_branch):
    """Switch back to the base branch after shipping a task."""
    result = subprocess.run(
        ["git", "checkout", base_branch],
        capture_output=True, text=True, cwd=REPO_ROOT,
    )
    if result.returncode != 0:
        print(f"  Warning: could not checkout {base_branch}: {result.stderr.strip()}")
        return False
    return True


def main():
    parser = argparse.ArgumentParser(description="Batch runner for IA Phase 2 tasks")
    parser.add_argument("--plan", action="store_true", help="Plan only, show resolved args")
    parser.add_argument("--dry-run", action="store_true", help="Plan + dry-run each step")
    parser.add_argument("--start", type=int, default=0, help="Start from this task index")
    parser.add_argument("--only", help="Comma-separated task indices to run (e.g. 1,3,5)")
    parser.add_argument("--skip", help="Comma-separated pipeline steps to skip (e.g. ship,post_review)")
    args = parser.parse_args()

    skip_steps = set(args.skip.split(",")) if args.skip else set()

    if args.only:
        task_indices = [int(i) for i in args.only.split(",")]
    else:
        task_indices = list(range(args.start, len(TASKS)))

    # Record base branch to return to after each task ships
    result = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        capture_output=True, text=True, cwd=REPO_ROOT,
    )
    base_branch = result.stdout.strip()
    print(f"Base branch: {base_branch}")

    # Get docs file listing for planning
    docs_files = get_docs_listing()
    print(f"Found {len(docs_files)} docs files\n")

    client = anthropic.Anthropic()

    # Plan all selected tasks
    plans = {}
    print("Planning tasks...\n")
    for i in task_indices:
        if i >= len(TASKS):
            print(f"  Skipping index {i} (out of range)")
            continue
        task = TASKS[i]
        print(f"  [{i}] {task[:80]}...")
        try:
            plan = plan_task(client, task, docs_files)
            plans[i] = plan
            print(f"      sources: {plan['sources']}")
            print(f"      targets: {plan['targets']}")
            if plan.get("retire"):
                print(f"      retire:  {plan['retire']}")
            print(f"      label:   {plan['label']}")
        except Exception as e:
            print(f"      ERROR: {e}")
        print()

    if args.plan:
        print("\nPlan complete. Use --dry-run to test or run without flags to execute.")
        return 0

    # Execute each task
    succeeded = []
    failed = []

    for i in task_indices:
        if i not in plans:
            continue

        plan = plans[i]
        task = TASKS[i]

        print(f"\n{'#'*60}")
        print(f"  TASK [{i}]: {task[:70]}...")
        print(f"  Label: {plan['label']}")
        print(f"{'#'*60}")

        # Verify we're on the base branch
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, cwd=REPO_ROOT,
        )
        current = result.stdout.strip()
        if current != base_branch:
            print(f"  Switching from {current} to {base_branch}")
            if not checkout_base_branch(base_branch):
                print(f"  SKIPPING task {i}: could not return to base branch")
                failed.append(i)
                continue

        success = run_pipeline(
            plan, task,
            dry_run=args.dry_run,
            skip_steps=skip_steps,
        )

        if success:
            succeeded.append(i)
            # After ship creates a new branch, switch back
            if "ship" not in skip_steps and not args.dry_run:
                checkout_base_branch(base_branch)
        else:
            failed.append(i)
            print(f"\n  Task [{i}] FAILED. Returning to base branch.")
            checkout_base_branch(base_branch)
            # Clean up any uncommitted changes from promote
            subprocess.run(
                ["git", "checkout", "--", "docs/", "docs.json"],
                capture_output=True, cwd=REPO_ROOT,
            )

    # Summary
    print(f"\n{'='*60}")
    print(f"  BATCH COMPLETE")
    print(f"  Succeeded: {len(succeeded)}/{len(plans)} — {succeeded}")
    if failed:
        print(f"  Failed:    {len(failed)} — {failed}")
    print(f"{'='*60}")

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
