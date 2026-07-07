#!/usr/bin/env python3
"""
Post review findings from review-report.json as GitHub PR review comments
with suggestion blocks.

Reads the review report produced by review.py, generates concrete replacement
text for each finding using Claude, and posts them as a single PR review via
the GitHub API. Findings with suggested_fix get ```suggestion``` blocks that
the reviewer can accept with one click ("Apply suggestion").

Usage:
    python pipeline/post_review.py --latest --pr 42
    python pipeline/post_review.py --latest --pr 42 --dry-run
    python pipeline/post_review.py --latest                    # auto-detect PR from branch
    python pipeline/post_review.py --run pipeline/drafts/20260706-192742 --pr 42
    python pipeline/post_review.py --latest --include-must-fix # also post remaining must_fix items
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
DRAFTS_DIR = REPO_ROOT / "pipeline" / "drafts"

MODEL = "claude-sonnet-4-6"
SUGGESTION_MAX_TOKENS = 1024
# Lines of context before/after the target line to send to Claude
CONTEXT_LINES = 5


# ---------------------------------------------------------------------------
# Helpers: run directory, subprocess, repo detection
# ---------------------------------------------------------------------------

def find_latest_run():
    """Return the most recent run directory under pipeline/drafts/."""
    if not DRAFTS_DIR.exists():
        return None
    runs = sorted(
        [d for d in DRAFTS_DIR.iterdir() if d.is_dir()],
        key=lambda d: d.stat().st_mtime,
    )
    return runs[-1] if runs else None


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


def detect_repo():
    """Detect the GitHub owner/repo from the git remote.

    Returns (owner, repo) or exits on failure.
    """
    result = run(["git", "remote", "get-url", "origin"], check=False)
    if result.returncode != 0:
        print("Error: could not detect git remote origin", file=sys.stderr)
        sys.exit(1)

    url = result.stdout.strip()
    # Handle SSH: git@github.com:owner/repo.git
    # Handle HTTPS: https://github.com/owner/repo.git
    if ":" in url and url.startswith("git@"):
        path = url.split(":")[-1]
    elif "github.com" in url:
        path = url.split("github.com/")[-1]
    else:
        # Try a generic parse
        path = url.rsplit("/", 2)[-2] + "/" + url.rsplit("/", 1)[-1]

    path = path.removesuffix(".git")
    parts = path.split("/")
    if len(parts) < 2:
        print(f"Error: could not parse owner/repo from remote URL: {url}", file=sys.stderr)
        sys.exit(1)
    return parts[-2], parts[-1]


def detect_pr_number():
    """Auto-detect the PR number for the current branch via gh CLI.

    Returns the PR number as an int, or None if not found.
    """
    result = run(["gh", "pr", "view", "--json", "number"], check=False)
    if result.returncode != 0:
        return None
    try:
        data = json.loads(result.stdout)
        return data.get("number")
    except (json.JSONDecodeError, KeyError):
        return None


def draft_to_canonical(filename):
    """Convert a draft filename to its canonical relative path.

    'docs--admin--overview.mdx' -> 'docs/admin/overview.mdx'
    """
    return filename.replace("--", "/")


# ---------------------------------------------------------------------------
# File reading and line extraction
# ---------------------------------------------------------------------------

def read_file_lines(canonical_rel):
    """Read the promoted file (or fall back to draft) and return lines as a list.

    Returns (list_of_lines, source_path) or (None, None) if not found.
    """
    promoted_path = REPO_ROOT / canonical_rel
    if promoted_path.exists():
        lines = promoted_path.read_text(encoding="utf-8").splitlines()
        return lines, promoted_path

    # Fall back: search drafts for the file
    draft_name = canonical_rel.replace("/", "--")
    for run_dir in sorted(DRAFTS_DIR.iterdir(), key=lambda d: d.stat().st_mtime, reverse=True):
        draft_path = run_dir / draft_name
        if draft_path.exists():
            lines = draft_path.read_text(encoding="utf-8").splitlines()
            return lines, draft_path

    return None, None


def extract_context(lines, target_line, context=CONTEXT_LINES):
    """Extract the target line and surrounding context.

    Args:
        lines: list of file lines (0-indexed internally, 1-indexed in findings)
        target_line: 1-based line number from the finding
        context: number of lines before/after to include

    Returns (context_text, target_text, start_1based, end_1based) or Nones if
    the line is out of range.
    """
    if not lines or target_line < 1 or target_line > len(lines):
        return None, None, None, None

    idx = target_line - 1  # 0-based
    start = max(0, idx - context)
    end = min(len(lines), idx + context + 1)

    context_lines = []
    for i in range(start, end):
        prefix = ">>>" if i == idx else "   "
        context_lines.append(f"{prefix} {i + 1:4d} | {lines[i]}")

    context_text = "\n".join(context_lines)
    target_text = lines[idx]
    return context_text, target_text, start + 1, end


# ---------------------------------------------------------------------------
# Claude: generate suggestion replacement text
# ---------------------------------------------------------------------------

def generate_suggestion_text(client, finding, context_text, target_text, lines, target_line):
    """Ask Claude to produce the replacement text for a suggestion block.

    Returns the replacement string (may be multi-line), or None if Claude
    cannot produce a clean replacement.
    """
    prompt = f"""You are editing a documentation file. A reviewer flagged this issue:

Title: {finding['title']}
Description: {finding['description']}
Suggested fix: {finding.get('suggested_fix', 'N/A')}

Here is the file context around line {target_line} (marked with >>>):

{context_text}

The current text on line {target_line} is:
{target_text}

Return ONLY the replacement text for line {target_line}. Rules:
- Return the replacement line(s) exactly as they should appear in the file.
- No explanation, no markdown fences, no line numbers.
- Make the minimum edit that addresses the finding.
- If the fix requires replacing multiple consecutive lines, return all replacement lines.
- If you cannot produce a clean replacement (e.g. the fix is too complex or ambiguous), return exactly: SKIP"""

    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=SUGGESTION_MAX_TOKENS,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text.strip()
        if text == "SKIP":
            return None
        # Strip markdown fences if the model wrapped the output
        if text.startswith("```"):
            first_newline = text.index("\n")
            text = text[first_newline + 1:]
            if text.endswith("```"):
                text = text[:-3].strip()
        return text
    except Exception as e:
        print(f"    Warning: Claude call failed for '{finding['title']}': {e}")
        return None


# ---------------------------------------------------------------------------
# Build review comments
# ---------------------------------------------------------------------------

def build_comment(finding, canonical_path, lines, client):
    """Build a single PR review comment dict for a finding.

    Returns a dict suitable for the GitHub PR review API, or None if the
    finding cannot be posted (e.g. no line number and no content).
    """
    line = finding.get("line", 0)
    title = finding["title"]
    description = finding["description"]
    suggested_fix = finding.get("suggested_fix")

    # File-level comment if no usable line number
    if not line or line < 1:
        body = f"**{title}**\n\n{description}"
        if suggested_fix:
            body += f"\n\n**Suggested fix:** {suggested_fix}"
        # GitHub API: file-level comments use subject_type=file and no line
        return {
            "path": canonical_path,
            "body": body,
            "subject_type": "file",
            "_title": title,
            "_has_suggestion": False,
        }

    # Try to generate a suggestion block
    suggestion_text = None
    if suggested_fix and lines:
        context_text, target_text, _, _ = extract_context(lines, line)
        if context_text and target_text:
            suggestion_text = generate_suggestion_text(
                client, finding, context_text, target_text, lines, line
            )

    # Build body
    body = f"**{title}**\n\n{description}"

    if suggestion_text is not None:
        body += f"\n\n```suggestion\n{suggestion_text}\n```"
        has_suggestion = True
    elif suggested_fix:
        body += f"\n\n**Suggested fix:** {suggested_fix}"
        has_suggestion = False
    else:
        has_suggestion = False

    comment = {
        "path": canonical_path,
        "line": line,
        "body": body,
        "_title": title,
        "_has_suggestion": has_suggestion,
    }

    # Clamp line to file length to avoid API errors
    if lines and line > len(lines):
        comment["line"] = len(lines)

    return comment


def collect_findings(report, include_must_fix=False):
    """Extract postable findings from the review report.

    Yields (draft_filename, finding_dict) tuples.
    By default only yields "consider" items. With include_must_fix, also yields
    remaining must_fix items (those that were not auto-fixed).
    """
    results = report.get("results", {})
    for draft_filename, file_result in results.items():
        # Get the last iteration's findings (most current)
        findings_list = file_result.get("findings", [])
        if not findings_list:
            continue
        last_iteration = findings_list[-1]

        # Consider items always
        for finding in last_iteration.get("consider", []):
            yield draft_filename, finding

        # Must-fix items only if requested
        if include_must_fix:
            # Only include must_fix items that were NOT successfully auto-fixed
            fixed_titles = {
                h["title"]
                for h in file_result.get("fix_history", [])
                if h.get("status") == "applied"
            }
            for finding in last_iteration.get("must_fix", []):
                if finding["title"] not in fixed_titles:
                    yield draft_filename, finding


# ---------------------------------------------------------------------------
# Post review via gh api
# ---------------------------------------------------------------------------

def post_review(owner, repo, pr_number, comments):
    """Post a PR review with all comments in a single API call.

    Uses `gh api` to create the review.
    """
    # Strip internal keys (prefixed with _) before sending
    api_comments = []
    for c in comments:
        api_comment = {k: v for k, v in c.items() if not k.startswith("_")}
        api_comments.append(api_comment)

    payload = {
        "event": "COMMENT",
        "body": f"Pipeline review: {len(comments)} finding(s) from review-report.json.",
        "comments": api_comments,
    }

    payload_json = json.dumps(payload)

    result = run(
        [
            "gh", "api",
            f"repos/{owner}/{repo}/pulls/{pr_number}/reviews",
            "--method", "POST",
            "--input", "-",
        ],
        check=False,
        input=payload_json,
    )

    if result.returncode != 0:
        stderr = result.stderr.strip() if result.stderr else ""
        stdout = result.stdout.strip() if result.stdout else ""
        print(f"Error posting review: {stderr or stdout}", file=sys.stderr)
        return False

    try:
        response = json.loads(result.stdout)
        review_id = response.get("id", "unknown")
        html_url = response.get("html_url", "")
        print(f"Review posted (id: {review_id})")
        if html_url:
            print(f"  {html_url}")
    except (json.JSONDecodeError, KeyError):
        print("Review posted (could not parse response)")

    return True


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Post review findings as GitHub PR review comments with suggestion blocks"
    )
    run_group = parser.add_mutually_exclusive_group(required=True)
    run_group.add_argument(
        "--run",
        help="Path to the run directory containing review-report.json",
    )
    run_group.add_argument(
        "--latest", action="store_true",
        help="Auto-pick the most recent run in pipeline/drafts/",
    )
    parser.add_argument(
        "--pr", type=int,
        help="PR number (auto-detected from current branch if omitted)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Show what would be posted without calling the API",
    )
    parser.add_argument(
        "--include-must-fix", action="store_true",
        help="Also post remaining must_fix items (default: consider only)",
    )
    args = parser.parse_args()

    # --- Resolve run directory ---
    if args.latest:
        run_dir = find_latest_run()
        if not run_dir:
            print("Error: no runs found in pipeline/drafts/", file=sys.stderr)
            return 1
        print(f"Using latest run: {run_dir.relative_to(REPO_ROOT)}")
    else:
        run_dir = Path(args.run)
        if not run_dir.is_absolute():
            run_dir = REPO_ROOT / run_dir
        if not run_dir.exists():
            print(f"Error: run directory not found: {run_dir}", file=sys.stderr)
            return 1

    # --- Load review report ---
    report_path = run_dir / "review-report.json"
    if not report_path.exists():
        print(f"Error: review-report.json not found in {run_dir}", file=sys.stderr)
        print("Run review.py first.", file=sys.stderr)
        return 1

    with open(report_path) as f:
        report = json.load(f)

    # --- Collect findings ---
    findings = list(collect_findings(report, include_must_fix=args.include_must_fix))
    if not findings:
        print("No findings to post.")
        return 0

    categories = "consider" + (" + must_fix" if args.include_must_fix else "")
    print(f"Found {len(findings)} finding(s) ({categories})")

    # --- Detect repo and PR ---
    if not args.dry_run:
        owner, repo = detect_repo()
        print(f"Repo: {owner}/{repo}")
    else:
        owner, repo = "OWNER", "REPO"

    pr_number = args.pr
    if not pr_number:
        pr_number = detect_pr_number()
        if not pr_number:
            print("Error: could not auto-detect PR number. Use --pr to specify.", file=sys.stderr)
            return 1
        print(f"Auto-detected PR: #{pr_number}")
    else:
        print(f"PR: #{pr_number}")

    # --- Build comments ---
    client = anthropic.Anthropic()
    comments = []
    file_lines_cache = {}  # canonical_path -> (lines, source_path)

    for draft_filename, finding in findings:
        canonical_path = draft_to_canonical(draft_filename)

        # Cache file reads
        if canonical_path not in file_lines_cache:
            lines, source = read_file_lines(canonical_path)
            file_lines_cache[canonical_path] = (lines, source)
        else:
            lines, source = file_lines_cache[canonical_path]

        print(f"  {canonical_path}:{finding.get('line', '?')} — {finding['title']}", end="")

        if args.dry_run and finding.get("suggested_fix"):
            # In dry-run, still call Claude to show what the suggestion would be
            comment = build_comment(finding, canonical_path, lines, client)
        elif args.dry_run:
            # No suggested_fix, no Claude call needed
            comment = build_comment(finding, canonical_path, lines, None)
        else:
            comment = build_comment(finding, canonical_path, lines, client)

        if comment:
            suffix = " [suggestion]" if comment.get("_has_suggestion") else ""
            print(suffix)
            comments.append(comment)
        else:
            print(" [skipped]")

    if not comments:
        print("No comments to post (all findings were skipped).")
        return 0

    suggestion_count = sum(1 for c in comments if c.get("_has_suggestion"))
    plain_count = len(comments) - suggestion_count

    print(f"\n{len(comments)} comment(s): {suggestion_count} with suggestions, {plain_count} plain")

    # --- Dry run output ---
    if args.dry_run:
        print("\n--- DRY RUN ---\n")
        for c in comments:
            path = c["path"]
            line = c.get("line", "file-level")
            title = c["_title"]
            has_suggestion = c.get("_has_suggestion", False)
            print(f"  {path}:{line} — {title}")
            if has_suggestion:
                # Extract suggestion text from body
                body = c["body"]
                start = body.find("```suggestion\n")
                end = body.find("\n```", start + 14)
                if start >= 0 and end >= 0:
                    suggestion = body[start + 14:end]
                    print(f"    Suggestion: {suggestion[:120]}{'...' if len(suggestion) > 120 else ''}")
            print()
        print("--- END DRY RUN ---")
        return 0

    # --- Post review ---
    print(f"\nPosting review to {owner}/{repo}#{pr_number}...")
    success = post_review(owner, repo, pr_number, comments)

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
