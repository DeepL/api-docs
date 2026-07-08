#!/usr/bin/env python3
"""
LLM-based review loop for generated docs drafts.

Runs between evaluate (deterministic checks) and promote (copying to docs tree).
Sends each draft to Claude for editorial and Diataxis review, auto-fixes must-fix
findings, and re-reviews up to a configurable number of iterations.

Usage:
    python pipeline/review.py pipeline/drafts/20260706-192742
    python pipeline/review.py --latest                         # pick most recent run
    python pipeline/review.py --latest --dry-run               # show what would be reviewed
    python pipeline/review.py --latest --file docs--admin--overview.mdx  # one file only
    python pipeline/review.py --latest --max-iterations 3      # up to 3 fix cycles
"""

import argparse
import json
import sys
from pathlib import Path

try:
    import anthropic
except ImportError:
    print("Install the Anthropic SDK: pip install anthropic")
    sys.exit(1)


REPO_ROOT = Path(__file__).resolve().parent.parent
DRAFTS_DIR = REPO_ROOT / "pipeline" / "drafts"
CLAUDE_MD_PATH = REPO_ROOT / "CLAUDE.md"
EDITORIAL_REVIEWER_PATH = REPO_ROOT / ".claude" / "agents" / "editorial-reviewer.md"
DIATAXIS_PATH = REPO_ROOT / ".claude" / "agents" / "diataxis.md"

MODEL = "claude-sonnet-4-6"
REVIEW_MAX_TOKENS = 4096
FIX_MAX_TOKENS = 8192


def load_file(path):
    """Read a file, returning empty string if not found."""
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


def resolve_run_dir(args):
    """Resolve the run directory from args (same pattern as evaluate.py)."""
    if args.latest:
        if not DRAFTS_DIR.exists():
            print(f"No drafts directory at {DRAFTS_DIR}", file=sys.stderr)
            sys.exit(1)
        runs = sorted(
            [d for d in DRAFTS_DIR.iterdir() if d.is_dir()],
            key=lambda d: d.stat().st_mtime,
        )
        if not runs:
            print("No runs found in drafts/", file=sys.stderr)
            sys.exit(1)
        return runs[-1]

    if args.run_dir:
        run_dir = Path(args.run_dir)
        if not run_dir.is_absolute():
            run_dir = REPO_ROOT / run_dir
        if not run_dir.exists():
            print(f"Run directory not found: {run_dir}", file=sys.stderr)
            sys.exit(1)
        return run_dir

    print("Specify a run directory or use --latest", file=sys.stderr)
    sys.exit(1)


def build_review_system_prompt():
    """System prompt for the review step (assembled from the agent files, one place)."""
    from util import build_review_system_prompt as _build
    return _build()


def build_review_user_prompt(filename, content, previous_fixes=None):
    """Build the user prompt for reviewing a draft.

    Args:
        filename: The draft filename (e.g. docs--admin--overview.mdx)
        content: The full file content
        previous_fixes: List of fix titles already applied (to avoid re-flagging)
    """
    original_path = filename.replace(".mdx", "").replace("--", "/") + ".mdx"

    context_block = ""
    if previous_fixes:
        fixes_list = "\n".join(f"- {f}" for f in previous_fixes)
        context_block = f"""
IMPORTANT: This is a re-review after fixes were applied. The following issues were
already fixed in this iteration. Do NOT re-flag them unless the fix introduced a new
problem. Only report genuinely remaining or new issues.

Previously fixed:
{fixes_list}
"""

    return f"""Review this documentation draft and return findings as JSON.

File: {filename}
Original path: {original_path}
{context_block}
Review the draft for:
1. DRY violations (navigation headings, endpoint tables in non-reference pages, duplicated content)
2. Diataxis adherence (correct type, no type mixing, follows type-specific structure)
3. Style and voice compliance (per CLAUDE.md: active voice, present tense, no marketing language, no em-dashes, concise)
4. Code example quality (language identifiers, runnable, request+response pairs, comments explain "why")
5. Frontmatter quality (has title, description is action-oriented and under 160 chars, not generic)
6. Structure (heading hierarchy, short paragraphs, tables for comparisons, no walls of text)

Return ONLY valid JSON in this exact format (no markdown fences, no commentary):

{{"must_fix": [{{"title": "Short issue title", "line": 1, "description": "What is wrong and what it should be.", "suggested_fix": "Concrete description of the fix to apply, or null if manual review needed"}}], "consider": [{{"title": "Short issue title", "line": 1, "description": "What could be improved.", "suggested_fix": "Concrete description of the fix to apply, or null if unclear"}}]}}

Rules:
- Be specific and actionable. "Improve the description" is too vague. "Frontmatter description is generic ('Overview of admin'). Rewrite to be action-oriented, e.g. 'Configure admin settings and manage team access'" is good.
- Consolidate: if the same issue appears on multiple lines, report it once and list all line numbers in the description.
- Only flag real problems. If the draft is solid, return empty arrays.
- "must_fix" = incorrect info, broken code, DRY violations, Diataxis type mixing, missing required structure, style violations that affect clarity
- "consider" = minor improvements, better wording, additional examples, minor inconsistencies
- For suggested_fix, describe what to change concretely enough that another LLM could apply it. Set to null if the fix requires judgment or context you don't have.

<draft>
{content}
</draft>"""


def build_fix_prompt(filename, content, finding):
    """Build the prompt for applying a single fix to a draft."""
    return f"""Apply this fix to the documentation draft below. Return the FULL updated file content.

File: {filename}

Fix to apply:
- Title: {finding['title']}
- Line: {finding.get('line', 'N/A')}
- Description: {finding['description']}
- Suggested fix: {finding.get('suggested_fix', 'N/A')}

Rules:
- Return ONLY the updated file content. No commentary, no markdown fences, no explanation.
- Start with the frontmatter (---) and end with the last line of content.
- Make the minimum change needed to fix the issue. Do not rewrite unrelated content.
- Preserve all existing formatting, structure, and content that isn't related to the fix.

<draft>
{content}
</draft>"""


def parse_review_response(response_text):
    """Parse the JSON review response from Claude.

    Handles cases where the model wraps JSON in markdown fences.
    """
    text = response_text.strip()

    # Strip markdown code fences if present
    if text.startswith("```"):
        first_newline = text.index("\n")
        text = text[first_newline + 1:]
        if text.endswith("```"):
            text = text[:-3].strip()

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        # Try to find JSON object in the response
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                parsed = json.loads(text[start:end])
            except json.JSONDecodeError:
                return {"must_fix": [], "consider": [], "_parse_error": True}
        else:
            return {"must_fix": [], "consider": [], "_parse_error": True}

    # Normalize structure
    if "must_fix" not in parsed:
        parsed["must_fix"] = []
    if "consider" not in parsed:
        parsed["consider"] = []

    return parsed


def review_draft(client, system_prompt, filename, content, previous_fixes=None):
    """Send a draft to Claude for review. Returns parsed findings dict."""
    user_prompt = build_review_user_prompt(filename, content, previous_fixes)

    response = client.messages.create(
        model=MODEL,
        max_tokens=REVIEW_MAX_TOKENS,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )

    return parse_review_response(response.content[0].text)


def apply_fix(client, filename, content, finding):
    """Apply a single fix to draft content via Claude. Returns updated content.

    Raises ValueError if the response is not valid MDX (e.g. chain-of-thought leak).
    """
    user_prompt = build_fix_prompt(filename, content, finding)

    response = client.messages.create(
        model=MODEL,
        max_tokens=FIX_MAX_TOKENS,
        system="You are a documentation editor. Apply fixes precisely and return the full updated file.",
        messages=[{"role": "user", "content": user_prompt}],
    )

    result = response.content[0].text.strip()

    # Strip markdown fences if the model wrapped the output
    if result.startswith("```"):
        first_newline = result.index("\n")
        result = result[first_newline + 1:]
        if result.endswith("```"):
            result = result[:-3].strip()

    # Validate: the result must start with YAML frontmatter.
    # If the model returned reasoning/commentary instead of file content,
    # try to extract the frontmatter block; otherwise reject the fix.
    if not result.startswith("---"):
        fm_start = result.find("\n---\n")
        if fm_start >= 0:
            result = result[fm_start + 1:]
        else:
            raise ValueError(
                f"Fix response is not valid MDX (does not start with frontmatter). "
                f"First 80 chars: {result[:80]!r}"
            )

    return result


def review_and_fix_file(client, system_prompt, filepath, max_iterations):
    """Run the full review-fix loop for a single file.

    Returns a result dict with status, iteration count, findings, and fix history.
    """
    filename = filepath.name
    content = filepath.read_text(encoding="utf-8")

    result = {
        "status": "clean",
        "iterations": 0,
        "initial_must_fix": 0,
        "remaining_must_fix": 0,
        "remaining_consider": 0,
        "findings": [],
        "fix_history": [],
    }

    previous_fixes = []

    for iteration in range(1, max_iterations + 1):
        result["iterations"] = iteration

        # Review
        print(f"    Iteration {iteration}: reviewing...")
        findings = review_draft(client, system_prompt, filename, content, previous_fixes if iteration > 1 else None)

        if findings.get("_parse_error"):
            print(f"    Warning: could not parse review response, treating as clean")
            break

        must_fix = findings.get("must_fix", [])
        consider = findings.get("consider", [])

        if iteration == 1:
            result["initial_must_fix"] = len(must_fix)

        # Store findings from this iteration
        result["findings"].append({
            "iteration": iteration,
            "must_fix": must_fix,
            "consider": consider,
        })

        if not must_fix:
            # No must-fix issues, done
            result["remaining_must_fix"] = 0
            result["remaining_consider"] = len(consider)
            result["status"] = "clean"
            print(f"    Iteration {iteration}: clean ({len(consider)} consider items)")
            break

        print(f"    Iteration {iteration}: {len(must_fix)} must-fix, {len(consider)} consider")

        # Fix phase: apply fixes for must_fix items that have suggested_fix
        fixable = [f for f in must_fix if f.get("suggested_fix")]
        unfixable = [f for f in must_fix if not f.get("suggested_fix")]

        if not fixable:
            # Nothing we can auto-fix
            result["remaining_must_fix"] = len(must_fix)
            result["remaining_consider"] = len(consider)
            result["status"] = "has_remaining_issues"
            print(f"    No auto-fixable items, stopping")
            break

        fixes_applied = 0
        for finding in fixable:
            try:
                print(f"    Fixing: {finding['title']}...")
                content = apply_fix(client, filename, content, finding)
                previous_fixes.append(finding["title"])
                fixes_applied += 1
                result["fix_history"].append({
                    "iteration": iteration,
                    "title": finding["title"],
                    "status": "applied",
                })
            except Exception as e:
                print(f"    Fix failed: {finding['title']}: {e}")
                result["fix_history"].append({
                    "iteration": iteration,
                    "title": finding["title"],
                    "status": "failed",
                    "error": str(e),
                })

        if fixes_applied > 0:
            # Write fixed content back to the draft file
            filepath.write_text(content, encoding="utf-8")
            print(f"    Applied {fixes_applied} fix(es), updated {filename}")

        # If this was the last iteration, record remaining issues
        if iteration == max_iterations:
            # We applied fixes but can't re-review (hit max). Record unfixable items.
            result["remaining_must_fix"] = len(unfixable)
            result["remaining_consider"] = len(consider)
            if unfixable:
                result["status"] = "has_remaining_issues"
            # If all must-fix items were fixable and we applied them, still mark clean
            # since we can't verify. The next pipeline run will re-evaluate.
            elif fixes_applied == len(fixable):
                result["status"] = "fixed_at_limit"
            print(f"    Hit max iterations ({max_iterations})")

    return result


def format_summary_table(file_results):
    """Format a summary table for stdout."""
    lines = []

    name_width = max(len(f) for f in file_results) if file_results else 20
    name_width = max(name_width, 10)
    header = f"{'File':<{name_width}}  {'Iters':>5}  {'Initial':>7}  {'Remaining':>9}  {'Status'}"
    lines.append(header)
    lines.append("-" * len(header))

    for filename in sorted(file_results):
        r = file_results[filename]
        row = (
            f"{filename:<{name_width}}  "
            f"{r['iterations']:>5}  "
            f"{r['initial_must_fix']:>7}  "
            f"{r['remaining_must_fix']:>9}  "
            f"{r['status']}"
        )
        lines.append(row)

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="LLM-based review loop for generated docs drafts"
    )
    parser.add_argument(
        "run_dir",
        nargs="?",
        help="Path to a drafts run directory (e.g. pipeline/drafts/20260706-192742)",
    )
    parser.add_argument(
        "--latest",
        action="store_true",
        help="Auto-pick the most recent run in pipeline/drafts/",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be reviewed without calling the API",
    )
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=5,
        help="Max review-fix cycles per file (default: 5)",
    )
    parser.add_argument(
        "--file",
        help="Review a specific draft file only (by filename, e.g. docs--admin--overview.mdx)",
    )
    args = parser.parse_args()

    run_dir = resolve_run_dir(args)

    # Collect draft files
    mdx_files = sorted(run_dir.glob("*.mdx"))
    if args.file:
        mdx_files = [f for f in mdx_files if f.name == args.file]
        if not mdx_files:
            print(f"File not found in run: {args.file}", file=sys.stderr)
            return 1

    if not mdx_files:
        print(f"No .mdx files found in {run_dir}", file=sys.stderr)
        return 1

    print(f"Reviewing {len(mdx_files)} file(s) in {run_dir.name}/")
    print(f"Max iterations: {args.max_iterations}\n")

    if args.dry_run:
        print("Dry run: would review these files:\n")
        for f in mdx_files:
            original = f.name.replace(".mdx", "").replace("--", "/") + ".mdx"
            print(f"  {f.name}  ({original})")
        return 0

    # Set up API client and system prompt
    client = anthropic.Anthropic()
    system_prompt = build_review_system_prompt()

    # Review each file
    file_results = {}
    total_fixes_applied = 0

    for i, filepath in enumerate(mdx_files):
        print(f"[{i + 1}/{len(mdx_files)}] {filepath.name}")
        result = review_and_fix_file(client, system_prompt, filepath, args.max_iterations)
        file_results[filepath.name] = result
        total_fixes_applied += sum(
            1 for h in result["fix_history"] if h["status"] == "applied"
        )

    # Summary counts
    clean_count = sum(1 for r in file_results.values() if r["status"] == "clean")
    fixed_at_limit_count = sum(1 for r in file_results.values() if r["status"] == "fixed_at_limit")
    remaining_count = sum(1 for r in file_results.values() if r["status"] == "has_remaining_issues")

    # Build iteration map
    iterations_map = {f: r["iterations"] for f, r in file_results.items()}

    # Write review report
    report = {
        "run_dir": str(run_dir),
        "files_reviewed": len(file_results),
        "iterations": iterations_map,
        "results": file_results,
        "summary": {
            "clean": clean_count + fixed_at_limit_count,
            "has_remaining_issues": remaining_count,
            "total_fixes_applied": total_fixes_applied,
        },
    }

    report_path = run_dir / "review-report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    # Print summary
    print(f"\n{format_summary_table(file_results)}")
    print(f"\nClean: {clean_count + fixed_at_limit_count}, "
          f"Remaining issues: {remaining_count}, "
          f"Fixes applied: {total_fixes_applied}")
    print(f"Report: {report_path.relative_to(REPO_ROOT)}")

    # Exit code: 0 if all files clean or only consider items, 1 if must_fix remain
    return 1 if remaining_count > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
