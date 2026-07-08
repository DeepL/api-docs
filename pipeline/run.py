#!/usr/bin/env python3
"""
Run the full docs pipeline end-to-end: generate or rework → evaluate → review → promote → ship → post_review.

Chains the individual scripts in sequence, passing the run directory between steps.
Stops on failure at any step. Each step's output is printed in real time.

Usage:
    # Full pipeline for new pages (Phase 3)
    python pipeline/run.py generate --section admin --force

    # Full pipeline for rework (Phase 2)
    python pipeline/run.py rework consolidate \
        --source docs/getting-started/intro.mdx docs/getting-started/about.mdx \
        --target docs/getting-started/intro.mdx \
        --instruction "Rework Introduction as orientation, absorb About"

    # Resume from a specific step on an existing run
    python pipeline/run.py --resume review --latest
    python pipeline/run.py --resume promote pipeline/drafts/20260706-192742

    # Pause after rework for manual review before continuing
    python pipeline/run.py rework consolidate --source ... --pause rework

    # Skip steps
    python pipeline/run.py generate --section admin --skip post_review

    # Dry run (passes --dry-run to every step)
    python pipeline/run.py generate --section admin --dry-run
"""

import argparse
import subprocess
import sys
from pathlib import Path

from util import REPO_ROOT, find_latest_run


STEPS = ["generate", "evaluate", "review", "promote", "ship", "post_review"]

STEP_SCRIPTS = {
    "generate": "generate.py",
    "rework": "rework.py",
    "evaluate": "evaluate.py",
    "review": "review.py",
    "promote": "promote.py",
    "ship": "ship.py",
    "post_review": "post_review.py",
}


def run_step(step_name, args, run_dir=None, dry_run=False):
    """Run a single pipeline step. Returns (success, run_dir)."""
    script = REPO_ROOT / "pipeline" / STEP_SCRIPTS[step_name]
    cmd = [sys.executable, str(script)]

    if step_name == "generate":
        cmd.extend(args)
    elif step_name == "rework":
        cmd.extend(args)
    elif step_name in ("evaluate", "review"):
        if run_dir:
            cmd.append(str(run_dir))
        else:
            cmd.append("--latest")
        if dry_run:
            cmd.append("--dry-run")
    elif step_name == "promote":
        if run_dir:
            cmd.append(str(run_dir))
        else:
            cmd.append("--latest")
        if dry_run:
            cmd.append("--dry-run")
    elif step_name == "ship":
        if run_dir:
            cmd.extend(["--run", str(run_dir)])
        else:
            cmd.append("--latest")
        if dry_run:
            cmd.append("--dry-run")
        else:
            cmd.append("--yes")
    elif step_name == "post_review":
        if run_dir:
            cmd.extend(["--run", str(run_dir)])
        else:
            cmd.append("--latest")
        if dry_run:
            cmd.append("--dry-run")

    print(f"\n{'='*60}")
    print(f"  STEP: {step_name}")
    print(f"  CMD:  {' '.join(cmd)}")
    print(f"{'='*60}\n")

    result = subprocess.run(cmd, cwd=REPO_ROOT)
    return result.returncode == 0


def parse_args():
    """Custom arg parsing to handle the two modes (generate vs rework) plus pipeline flags."""
    pipeline_flags = []
    mode_args = []
    resume_step = None
    run_dir = None
    skip_steps = set()
    pause_after = set()
    dry_run = False

    args = sys.argv[1:]
    i = 0

    while i < len(args):
        arg = args[i]

        if arg == "--resume":
            i += 1
            if i < len(args):
                resume_step = args[i]
            i += 1
            # Next arg might be a run dir or --latest
            if i < len(args) and args[i] == "--latest":
                run_dir = find_latest_run()
                i += 1
            elif i < len(args) and not args[i].startswith("--"):
                path = Path(args[i])
                if not path.is_absolute():
                    path = REPO_ROOT / path
                run_dir = path
                i += 1
            continue

        if arg == "--skip":
            i += 1
            if i < len(args):
                skip_steps.add(args[i])
            i += 1
            continue

        if arg == "--pause":
            i += 1
            if i < len(args):
                pause_after.add(args[i])
            i += 1
            continue

        mode_args.append(arg)
        i += 1

    # Detect --dry-run anywhere in args (it's both a pipeline flag and passed to steps)
    if "--dry-run" in mode_args:
        dry_run = True

    if not mode_args and not resume_step:
        print("Usage: python pipeline/run.py [generate|rework] [args...]")
        print("       python pipeline/run.py --resume <step> [--latest|<run_dir>]")
        print()
        print("Examples:")
        print("  python pipeline/run.py generate --section admin --force")
        print("  python pipeline/run.py rework expand --source docs/translate/text/detect-languages.mdx --instruction 'Expand'")
        print("  python pipeline/run.py --resume review --latest")
        print("  python pipeline/run.py --resume promote pipeline/drafts/20260706-192742")
        sys.exit(1)

    mode = mode_args[0] if mode_args else None

    return {
        "mode": mode,
        "mode_args": mode_args,
        "resume_step": resume_step,
        "run_dir": run_dir,
        "skip_steps": skip_steps,
        "pause_after": pause_after,
        "dry_run": dry_run,
    }


def main():
    config = parse_args()

    mode = config["mode"]
    resume_step = config["resume_step"]
    run_dir = config["run_dir"]
    skip_steps = config["skip_steps"]
    pause_after = config["pause_after"]
    dry_run = config["dry_run"]

    if resume_step:
        if resume_step not in STEPS:
            print(f"Error: unknown step '{resume_step}'. Valid steps: {', '.join(STEPS)}")
            return 1
        if not run_dir:
            run_dir = find_latest_run()
            if not run_dir:
                print("Error: no runs found. Specify a run directory or use --latest.")
                return 1
        print(f"Resuming from step: {resume_step}")
        print(f"Run directory: {run_dir}")

        step_index = STEPS.index(resume_step)
        steps_to_run = STEPS[step_index:]
    elif mode == "rework":
        # rework replaces generate, then continue with evaluate onward
        steps_to_run = ["rework"] + STEPS[1:]  # rework, evaluate, review, promote, ship, post_review
    elif mode == "generate":
        steps_to_run = STEPS
    else:
        print(f"Error: first argument must be 'generate' or 'rework', got '{mode}'")
        return 1

    steps_to_run = [s for s in steps_to_run if s not in skip_steps]

    print(f"Pipeline steps: {' → '.join(steps_to_run)}")
    if skip_steps:
        print(f"Skipping: {', '.join(skip_steps)}")
    if dry_run:
        print("Mode: DRY RUN (all steps)")
    print()

    # Track the run dir before starting so we can detect if a new one was created
    pre_run_latest = find_latest_run()

    for step in steps_to_run:
        if step in ("generate", "rework"):
            # Strip the leading mode word ("generate" or "rework") since run_step
            # prepends the script path. The remaining args go straight through.
            args_for_step = config["mode_args"][1:]
            if dry_run and "--dry-run" not in args_for_step:
                args_for_step = args_for_step + ["--dry-run"]
            success = run_step(step, args_for_step, dry_run=dry_run)
        else:
            success = run_step(step, [], run_dir=run_dir, dry_run=dry_run)

        if not success:
            if step == "evaluate":
                print(f"\n{'='*60}")
                print(f"  EVALUATE FAILED — drafts have errors.")
                print(f"  Fix the issues and resume with:")
                print(f"    python pipeline/run.py --resume evaluate --latest")
                print(f"  Or skip to review (LLM may catch the same issues):")
                print(f"    python pipeline/run.py --resume review --latest")
                print(f"{'='*60}")
            elif step == "review":
                print(f"\n{'='*60}")
                print(f"  REVIEW has remaining must-fix items.")
                print(f"  Check review-report.json, fix manually, then resume:")
                print(f"    python pipeline/run.py --resume promote --latest")
                print(f"{'='*60}")
            else:
                print(f"\n{'='*60}")
                print(f"  STEP '{step}' FAILED.")
                print(f"  Fix the issue and resume with:")
                print(f"    python pipeline/run.py --resume {step} --latest")
                print(f"{'='*60}")
            return 1

        # Pause after this step if requested
        if step in pause_after:
            next_step_idx = steps_to_run.index(step) + 1
            next_step = steps_to_run[next_step_idx] if next_step_idx < len(steps_to_run) else None
            print(f"\n{'='*60}")
            print(f"  PAUSED after '{step}'. Review the output, then resume:")
            if run_dir:
                rd = run_dir.relative_to(REPO_ROOT) if run_dir.is_relative_to(REPO_ROOT) else run_dir
                print(f"  Drafts: {rd}/")
            if next_step:
                print(f"    python pipeline/run.py --resume {next_step} --latest")
            print(f"{'='*60}")
            return 0

        # After generate/rework, pick up the NEW run directory for subsequent steps
        if step in ("generate", "rework") and not run_dir:
            new_latest = find_latest_run()
            if new_latest and new_latest != pre_run_latest:
                run_dir = new_latest
            elif dry_run:
                print(f"\n{'='*60}")
                print(f"  DRY RUN COMPLETE (no drafts created, stopping)")
                print(f"{'='*60}")
                return 0
            else:
                print(f"\nError: generate/rework did not produce a new run directory.")
                return 1

    print(f"\n{'='*60}")
    print(f"  PIPELINE COMPLETE")
    if run_dir:
        print(f"  Run: {run_dir.relative_to(REPO_ROOT) if run_dir.is_relative_to(REPO_ROOT) else run_dir}")
    print(f"{'='*60}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
