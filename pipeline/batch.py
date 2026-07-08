#!/usr/bin/env python3
"""
Batch runner for IA Phase 2 cleanup tasks.

Iterates over freeform task descriptions, uses Claude to plan each one
(resolve file paths and output targets), then runs each through the full
pipeline: rework → evaluate → review → promote → ship.

Usage:
    # Single task (incremental mode — plan, review, then run):
    python pipeline/batch.py --task "Consolidate translate overview into endpoint page"
    python pipeline/batch.py --task "Retire glossaries overview" --plan
    python pipeline/batch.py --task "Retire glossaries overview" --pause rework

    # Batch mode (all tasks from the TASKS list):
    python pipeline/batch.py --plan              # Plan all tasks, show resolved args
    python pipeline/batch.py --dry-run           # Plan + dry-run each pipeline step
    python pipeline/batch.py                     # Run all tasks, 1 PR each
    python pipeline/batch.py --start 3           # Start from task 3 (0-indexed)
    python pipeline/batch.py --only 1,3,5        # Run specific tasks by index
    # Accumulate on one branch → push → PR → post review suggestions:
    python pipeline/batch.py --branch docs/ia-phase2-reworks
    python pipeline/batch.py --branch docs/ia-phase2-reworks --only 8,9,10,11,12
    python pipeline/batch.py --branch docs/ia-phase2-reworks --no-push  # local review first
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

from util import (
    REPO_ROOT,
    find_latest_run,
    get_docs_changes,
    get_current_branch,
    branch_exists,
    check_gh_available,
    stage_and_commit_docs,
    push_and_create_pr,
)

MODEL = "claude-sonnet-4-6"

# Phase 2 tasks from the IA Proposal (Confluence page 1419116546).
# Each is a freeform description. The planning step resolves file paths.
TASKS = [
    # Task 0 was a monolithic "consolidate all API reference overviews" that failed —
    # it deleted pages without folding content. Use --task for incremental per-section
    # consolidation instead. Example:
    #   python pipeline/batch.py --task "Retire api-reference/translate.mdx: fold unique
    #     content (limits, code examples, model_type guidance) into the endpoint page.
    #     Cut anything already in the OpenAPI spec." --pause rework
    (
        "PLACEHOLDER — use --task for per-section API reference consolidation. "
        "See comment above for example."
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
    """Get the list of all .mdx files in docs/ and api-reference/."""
    result = subprocess.run(
        ["find", "docs", "api-reference", "-name", "*.mdx"],
        capture_output=True, text=True, cwd=REPO_ROOT,
    )
    return sorted(result.stdout.strip().splitlines())


PLAN_SYSTEM_PROMPT = """\
You are a planning assistant for a docs pipeline. Given a freeform task \
description, a list of docs files, and (when provided) the source file content, \
resolve the task into concrete file paths and content routing instructions.

## Diataxis Framework

Every docs page must serve exactly one Diataxis type:
- **Tutorial**: learning-oriented, walks through a complete scenario step by step
- **How-to**: goal-oriented, solves a specific problem ("how to batch-translate texts")
- **Reference**: information-oriented, describes the machinery (parameters, config, specs)
- **Explanation**: understanding-oriented, discusses concepts and design decisions

## Key Rules

1. NEVER route narrative content (code examples, how-tos, explanations, guidance) to \
openapi: endpoint pages under api-reference/. Those are auto-rendered API reference stubs \
and must stay minimal. Supplementary content belongs in docs/ pages.
2. When retiring an overview or narrative page, audit each section of its content:
   - Already covered by an existing docs/ page? → Route to that page (update it)
   - Unique and useful? → Route to an existing docs/ page, or create a new one
   - Restating what the OpenAPI spec already shows (parameter lists, response schemas)? → Discard
   - Generic boilerplate ("learn more", "see the API reference")? → Discard
3. Prefer routing to existing pages over creating new ones.
4. New pages go under docs/<product-family>/ with a clear Diataxis type in mind.

## Output Format

Output valid JSON with these fields:
- "sources": list of file paths to read as input (must exist in the file list)
- "targets": list of file paths to write as output (can be existing or new paths)
- "retire": list of file paths to delete after the task (pages being retired/merged away). \
Only include files that should be REMOVED, not files being rewritten in place.
- "label": short kebab-case label for this run (e.g. "retire-translate-overview")
- "routing": detailed instruction for the content writer explaining what specific content \
goes to which target and what to discard. Name the sections/topics from the source and \
their destinations. This becomes the writer's primary instruction, so be specific.
- "discard": list of content descriptions being intentionally dropped, with reasons \
(e.g. "Parameter list for /v2/translate — duplicated by OpenAPI spec auto-rendering")

Rules:
- All paths are relative to the repo root (e.g. "docs/getting-started/about.mdx")
- Sources must be actual files from the provided file list
- Targets that are existing files will be overwritten with new content (their current \
content is loaded as source context automatically)
- Targets that don't exist yet will be created
- For retire tasks, the source being retired goes in "retire", and the files \
absorbing its content go in both "sources" and "targets"
- For rework/expand tasks where a page is rewritten in place, source and target are the same path
- When retiring overview/narrative pages from a directory, also check for child pages \
that serve as overviews (e.g. sidebarTitle: 'Overview', or narrative pages without an \
openapi: frontmatter field in an otherwise endpoint-focused directory). Include those \
in "retire" too.
- Output ONLY the JSON object, no explanation"""


def print_plan(index, task, plan):
    """Display a planned task's details."""
    print(f"  [{index}] {task[:80]}...")
    print(f"      sources: {plan['sources']}")
    print(f"      targets: {plan['targets']}")
    if plan.get("retire"):
        print(f"      retire:  {plan['retire']}")
    print(f"      label:   {plan['label']}")
    if plan.get("routing"):
        routing = plan["routing"]
        if isinstance(routing, dict):
            for path, instruction in routing.items():
                print(f"      route → {path}:")
                print(f"               {instruction[:120]}...")
        else:
            for line in str(routing).split("\n")[:5]:
                print(f"      routing: {line}")
    if plan.get("discard"):
        for item in plan["discard"]:
            print(f"      discard: {item[:100]}...")


def load_source_content(task_description):
    """Try to extract file paths mentioned in the task and load their content."""
    content_blocks = []
    for token in task_description.replace(",", " ").split():
        token = token.strip(":()")
        if token.endswith(".mdx") and (REPO_ROOT / token).exists():
            text = (REPO_ROOT / token).read_text(encoding="utf-8")
            content_blocks.append(f"### {token}\n```mdx\n{text}\n```")
    return "\n\n".join(content_blocks)


def plan_task(client, task_description, docs_files):
    """Use Claude to resolve a freeform task into structured pipeline args."""
    file_list = "\n".join(docs_files)

    source_content = load_source_content(task_description)
    source_block = ""
    if source_content:
        source_block = f"\n\n## Source file content (for content audit)\n\n{source_content}"

    response = client.messages.create(
        model=MODEL,
        max_tokens=2048,
        system=PLAN_SYSTEM_PROMPT,
        messages=[{
            "role": "user",
            "content": (
                f"## Task\n\n{task_description}\n\n"
                f"## Available docs files\n\n```\n{file_list}\n```"
                f"{source_block}"
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


def build_instruction(plan, task_description):
    """Build a rework instruction from the plan's routing field."""
    routing = plan.get("routing")
    if not routing:
        return task_description

    if isinstance(routing, str):
        return routing

    parts = [task_description, ""]
    for path, instruction in routing.items():
        parts.append(f"## Target: {path}")
        parts.append(instruction)
        parts.append("")

    discard = plan.get("discard")
    if discard:
        parts.append("## Content to discard")
        for item in discard:
            parts.append(f"- {item}")

    return "\n".join(parts)


def run_pipeline(plan, task_description, dry_run=False, skip_steps=None, pause_after=None):
    """Run the full pipeline for a single planned task.

    Returns the run directory path on success, None on failure.
    """
    skip_steps = skip_steps or set()

    pre_run_latest = find_latest_run()

    cmd = [
        sys.executable, str(REPO_ROOT / "pipeline" / "run.py"),
        "rework", "rework",
        "--source", *plan["sources"],
        "--instruction", build_instruction(plan, task_description),
        "--label", plan["label"],
    ]

    if plan["targets"]:
        cmd.extend(["--target", *plan["targets"]])

    if plan.get("retire"):
        cmd.extend(["--retire", *plan["retire"]])

    if dry_run:
        cmd.append("--dry-run")

    for step in skip_steps:
        cmd.extend(["--skip", step])

    if pause_after:
        cmd.extend(["--pause", pause_after])

    print(f"\n{'='*60}")
    print(f"  CMD: {' '.join(cmd)}")
    print(f"{'='*60}\n")

    result = subprocess.run(cmd, cwd=REPO_ROOT)

    if result.returncode != 0:
        return None

    # Find the run directory that was just created
    run_dir = find_latest_run()
    if run_dir == pre_run_latest:
        run_dir = None

    # Write retire.json if there are pages to delete
    if plan.get("retire") and not dry_run and run_dir:
        retire_path = run_dir / "retire.json"
        if not retire_path.exists():
            retire_path.write_text(json.dumps(plan["retire"], indent=2))
            print(f"  Pages to retire: {', '.join(plan['retire'])}")

    return run_dir


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


def commit_promoted_changes(task_index, task_description):
    """Stage and commit docs changes after promote, for --branch mode."""
    changed = get_docs_changes()
    if not changed:
        print(f"  No docs changes to commit for task [{task_index}]")
        return

    short_desc = task_description.split(":")[0] if ":" in task_description else task_description[:60]
    msg = f"docs: {short_desc.lower().strip()}\n\nTask [{task_index}]: {task_description[:200]}"

    ok, num_files = stage_and_commit_docs(msg)
    if ok:
        print(f"  Committed {num_files} file(s) for task [{task_index}]")


def main():
    parser = argparse.ArgumentParser(description="Batch runner for IA Phase 2 tasks")
    parser.add_argument("--plan", action="store_true", help="Plan and save to pipeline/batch-plan.json")
    parser.add_argument("--from-plan", dest="from_plan", help="Load a saved plan instead of re-planning")
    parser.add_argument("--dry-run", action="store_true", help="Plan + dry-run each step")
    parser.add_argument("--start", type=int, default=0, help="Start from this task index")
    parser.add_argument("--only", help="Comma-separated task indices to run (e.g. 1,3,5)")
    parser.add_argument("--skip", help="Comma-separated pipeline steps to skip (e.g. ship,post_review)")
    parser.add_argument(
        "--branch",
        help="Accumulate all tasks on one branch (skips ship/post_review, commits after each promote)",
    )
    parser.add_argument(
        "--no-push", dest="no_push", action="store_true",
        help="With --branch: stop after committing, don't push/PR/post-review",
    )
    parser.add_argument(
        "--task",
        help="Run a single freeform task description (instead of the TASKS list)",
    )
    parser.add_argument(
        "--pause",
        help="Pause after this pipeline step for manual review (e.g. --pause rework)",
    )
    args = parser.parse_args()

    skip_steps = set(args.skip.split(",")) if args.skip else set()
    if args.branch:
        skip_steps.update(["ship", "post_review"])

    # Single-task mode: override the task list
    if args.task:
        TASKS.clear()
        TASKS.append(args.task)
        task_indices = [0]
    elif args.only:
        task_indices = [int(i) for i in args.only.split(",")]
    else:
        task_indices = list(range(args.start, len(TASKS)))

    base_branch = get_current_branch()
    print(f"Base branch: {base_branch}")

    # --branch mode: create or switch to accumulation branch
    if args.branch and not args.plan and not args.dry_run:
        if branch_exists(args.branch):
            subprocess.run(["git", "checkout", args.branch], cwd=REPO_ROOT)
            print(f"Switched to existing branch: {args.branch}")
        else:
            subprocess.run(["git", "checkout", "-b", args.branch], cwd=REPO_ROOT)
            print(f"Created branch: {args.branch}")

    plan_file = REPO_ROOT / "pipeline" / "batch-plan.json"

    if args.from_plan:
        # Load saved plan
        plan_path = Path(args.from_plan)
        if not plan_path.is_absolute():
            plan_path = REPO_ROOT / plan_path
        with open(plan_path) as f:
            saved = json.load(f)
        plans = {entry["index"]: entry["plan"] for entry in saved if entry["index"] in task_indices}
        print(f"Loaded {len(plans)} task plan(s) from {plan_path}\n")
        for i in sorted(plans):
            plan = plans[i]
            print_plan(i, TASKS[i], plan)
        print()
    else:
        # Plan with Claude
        docs_files = get_docs_listing()
        print(f"Found {len(docs_files)} docs files\n")

        client = anthropic.Anthropic()

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
                print_plan(i, task, plan)
            except Exception as e:
                print(f"      ERROR: {e}")
            print()

        # Save plan to file
        saved = [{"index": i, "task": TASKS[i], "plan": plans[i]} for i in sorted(plans)]
        plan_file.write_text(json.dumps(saved, indent=2))
        print(f"Plan saved to {plan_file.relative_to(REPO_ROOT)}")

    if args.plan:
        print(f"Review/edit the plan, then run with --from-plan {plan_file.relative_to(REPO_ROOT)}")
        return 0

    # Execute each task
    succeeded = []
    failed = []
    results = []  # track run directories for post-review

    for i in task_indices:
        if i not in plans:
            continue

        plan = plans[i]
        task = TASKS[i]

        print(f"\n{'#'*60}")
        print(f"  TASK [{i}]: {task[:70]}...")
        print(f"  Label: {plan['label']}")
        print(f"{'#'*60}")

        if not plan.get("sources"):
            print(f"  SKIPPED: no source files (this task may need manual handling)")
            failed.append(i)
            continue

        # In per-PR mode, verify we're on the base branch
        if not args.branch:
            current = get_current_branch()
            if current != base_branch:
                print(f"  Switching from {current} to {base_branch}")
                if not checkout_base_branch(base_branch):
                    print(f"  SKIPPING task {i}: could not return to base branch")
                    failed.append(i)
                    continue

        run_dir = run_pipeline(
            plan, task,
            dry_run=args.dry_run,
            skip_steps=skip_steps,
            pause_after=args.pause,
        )

        if run_dir:
            succeeded.append(i)
            results.append({
                "index": i,
                "label": plan["label"],
                "run_dir": str(run_dir.relative_to(REPO_ROOT)),
            })
            if args.branch and not args.dry_run:
                commit_promoted_changes(i, task)
            elif "ship" not in skip_steps and not args.dry_run:
                checkout_base_branch(base_branch)
        else:
            failed.append(i)
            print(f"\n  Task [{i}] FAILED.")
            # Clean up any uncommitted changes from promote
            subprocess.run(
                ["git", "checkout", "--", "docs/", "docs.json"],
                capture_output=True, cwd=REPO_ROOT,
            )
            if not args.branch:
                print(f"  Returning to base branch.")
                checkout_base_branch(base_branch)

    # Summary
    print(f"\n{'='*60}")
    print(f"  BATCH COMPLETE")
    print(f"  Succeeded: {len(succeeded)}/{len(plans)} — {succeeded}")
    if failed:
        print(f"  Failed:    {len(failed)} — {failed}")
    print(f"{'='*60}")

    # --branch mode: push, create PR, post review suggestions
    if args.branch and succeeded and not args.dry_run:
        if args.no_push:
            print(f"\n  All changes on branch: {args.branch}")
            print(f"  Review with: git log --oneline main..{args.branch}")
            return 1 if failed else 0

        # Build PR body
        body_lines = ["## IA Phase 2 tasks\n"]
        for entry in results:
            body_lines.append(f"- `{entry['label']}` (task [{entry['index']}])")
        if failed:
            body_lines.append(f"\n## Failed tasks\n")
            for i in failed:
                body_lines.append(f"- task [{i}]: {TASKS[i][:80]}")
        body = "\n".join(body_lines)

        print(f"\nPushing and creating PR...")
        pr_url = push_and_create_pr(
            args.branch,
            f"docs: IA Phase 2 — {len(results)} tasks",
            body,
        )
        if not pr_url:
            print("Failed to push or create PR.")
            return 1
        print(f"PR created: {pr_url}")

        # Post "consider" suggestions from each task's review
        pr_number = pr_url.rstrip("/").split("/")[-1]
        print(f"\nPosting review suggestions to PR #{pr_number}...")
        for entry in results:
            run_dir = REPO_ROOT / entry["run_dir"]
            review_report = run_dir / "review-report.json"
            if not review_report.exists():
                continue
            print(f"  [{entry['index']}] {entry['label']}")
            subprocess.run(
                [sys.executable, str(REPO_ROOT / "pipeline" / "post_review.py"),
                 "--run", str(run_dir), "--pr", str(pr_number)],
                cwd=REPO_ROOT,
            )

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
