#!/usr/bin/env python3
"""
Deterministic quality checker for generated docs drafts.

Runs structural, frontmatter, DRY, and code checks on .mdx drafts before
they get promoted to the docs tree. No AI — pure pattern matching.

Usage:
    python pipeline/evaluate.py pipeline/drafts/20260706-192742
    python pipeline/evaluate.py --latest                # pick most recent run
    python pipeline/evaluate.py --latest --verbose       # detailed findings per file
    python pipeline/evaluate.py --latest --output json   # machine-readable output
"""

import argparse
import json
import re
import sys
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parent.parent
DRAFTS_DIR = REPO_ROOT / "pipeline" / "drafts"

# Severity levels
ERROR = "error"
WARNING = "warning"

# Frontmatter description patterns that are too generic
GENERIC_DESCRIPTION_PATTERNS = [
    re.compile(r"^Learn what .+ does\.?$", re.IGNORECASE),
    re.compile(r"^Overview of .+\.?$", re.IGNORECASE),
    re.compile(r"^Information about .+\.?$", re.IGNORECASE),
    re.compile(r"^Introduction to .+\.?$", re.IGNORECASE),
    re.compile(r"^This (page|article|doc|guide) .+\.?$", re.IGNORECASE),
]

# Navigation heading patterns to flag (DRY anti-pattern)
NAV_HEADING_PATTERNS = [
    re.compile(r"^#+\s+(In this section)\s*$", re.IGNORECASE),
    re.compile(r"^#+\s+(Guides in this section)\s*$", re.IGNORECASE),
    re.compile(r"^#+\s+(Related pages)\s*$", re.IGNORECASE),
    re.compile(r"^#+\s+(Related API reference)\s*$", re.IGNORECASE),
    re.compile(r"^#+\s+(Related reference)\s*$", re.IGNORECASE),
]

# HTTP method + path pattern for endpoint tables
ENDPOINT_TABLE_PATTERN = re.compile(
    r"\|\s*`?(GET|POST|PUT|PATCH|DELETE)\s+/v\d+/", re.IGNORECASE
)

# Callout components
CALLOUT_PATTERN = re.compile(r"<(Note|Tip|Warning)[\s>]", re.IGNORECASE)


def extract_frontmatter(content):
    """Parse YAML frontmatter from file content. Returns (dict, end_index)."""
    if not content.startswith("---"):
        return {}, 0
    end = content.find("---", 3)
    if end == -1:
        return {}, 0
    try:
        fm = yaml.safe_load(content[3:end]) or {}
    except yaml.YAMLError:
        fm = {}
    return fm, end + 3


def original_path_from_filename(filename):
    """Convert draft filename back to its original docs path.

    Example: docs--admin--overview.mdx -> docs/admin/overview
    """
    return filename.replace(".mdx", "").replace("--", "/")


def is_overview_page(original_path):
    """Check if the page is an overview page (by path convention)."""
    parts = original_path.lower().split("/")
    return any(p in ("overview", "intro", "introduction", "index") for p in parts)


def check_file(filepath, verbose=False):
    """Run all checks on a single .mdx file. Returns list of findings."""
    findings = []
    content = filepath.read_text(encoding="utf-8")
    lines = content.splitlines()
    filename = filepath.name
    original_path = original_path_from_filename(filename)
    is_api_ref = original_path.startswith("api-reference/")
    is_overview = is_overview_page(original_path)

    # --- Frontmatter checks ---
    fm, body_start = extract_frontmatter(content)
    body = content[body_start:] if body_start > 0 else content

    if not fm:
        findings.append({
            "file": filename,
            "line": 1,
            "check": "frontmatter_present",
            "category": "frontmatter",
            "severity": ERROR,
            "message": "No valid YAML frontmatter found",
        })
    else:
        # Has title
        if not fm.get("title"):
            findings.append({
                "file": filename,
                "line": 1,
                "check": "frontmatter_title",
                "category": "frontmatter",
                "severity": ERROR,
                "message": "Missing 'title' field in frontmatter",
            })

        # Has description (skip for openapi pages — content is spec-rendered)
        desc = fm.get("description", "")
        if not desc and not fm.get("openapi"):
            findings.append({
                "file": filename,
                "line": 1,
                "check": "frontmatter_description",
                "category": "frontmatter",
                "severity": ERROR,
                "message": "Missing 'description' field in frontmatter",
            })
        else:
            desc_str = str(desc)
            # Description length
            if len(desc_str) > 160:
                findings.append({
                    "file": filename,
                    "line": 1,
                    "check": "frontmatter_description_length",
                    "category": "frontmatter",
                    "severity": WARNING,
                    "message": f"Description is {len(desc_str)} chars (max 160)",
                })

            # Generic description
            for pattern in GENERIC_DESCRIPTION_PATTERNS:
                if pattern.match(desc_str):
                    findings.append({
                        "file": filename,
                        "line": 1,
                        "check": "frontmatter_description_generic",
                        "category": "frontmatter",
                        "severity": WARNING,
                        "message": f"Description looks generic: \"{desc_str}\"",
                    })
                    break

    # --- DRY / anti-pattern checks ---
    for i, line in enumerate(lines, start=1):
        # Navigation headings
        for pattern in NAV_HEADING_PATTERNS:
            if pattern.match(line):
                findings.append({
                    "file": filename,
                    "line": i,
                    "check": "dry_nav_heading",
                    "category": "dry",
                    "severity": ERROR,
                    "message": f"Navigation heading found: \"{line.strip()}\"",
                })

        # Endpoint tables in non-reference pages
        if not is_api_ref and ENDPOINT_TABLE_PATTERN.search(line):
            findings.append({
                "file": filename,
                "line": i,
                "check": "dry_endpoint_table",
                "category": "dry",
                "severity": ERROR,
                "message": "Endpoint table with HTTP method+path in non-reference page",
            })

    # --- Structure checks ---
    # Pages with openapi: frontmatter are spec-rendered stubs — body content is
    # auto-generated from the OpenAPI spec, so prose checks don't apply.
    is_openapi_page = bool(fm.get("openapi"))

    if not is_openapi_page:
        has_h2 = any(line.startswith("## ") for line in lines)
        if not has_h2:
            findings.append({
                "file": filename,
                "line": 1,
                "check": "structure_has_h2",
                "category": "structure",
                "severity": ERROR,
                "message": "No ## heading found",
            })

        body_words = len(body.split())
        if body_words < 100:
            findings.append({
                "file": filename,
                "line": 1,
                "check": "structure_word_count",
                "category": "structure",
                "severity": ERROR,
                "message": f"Body has only {body_words} words (minimum 100)",
            })

    # Callout count
    callout_count = len(CALLOUT_PATTERN.findall(content))
    if callout_count > 2:
        findings.append({
            "file": filename,
            "line": 1,
            "check": "structure_callout_count",
            "category": "structure",
            "severity": WARNING,
            "message": f"Page has {callout_count} callout components (max 2)",
        })

    # --- Code checks (non-overview pages only) ---
    if not is_overview and not is_openapi_page:
        # Has at least one code block
        code_block_starts = [
            (i, line) for i, line in enumerate(lines, start=1)
            if line.strip().startswith("```")
        ]

        # Code blocks come in pairs (open/close), so count opening fences
        opening_fences = []
        in_block = False
        for i, line in enumerate(lines, start=1):
            stripped = line.strip()
            if stripped.startswith("```"):
                if not in_block:
                    opening_fences.append((i, stripped))
                    in_block = True
                else:
                    in_block = False

        if not opening_fences:
            findings.append({
                "file": filename,
                "line": 1,
                "check": "code_has_blocks",
                "category": "code",
                "severity": WARNING,
                "message": "No fenced code blocks found (expected for non-overview pages)",
            })
        else:
            # Check language identifiers on opening fences
            for line_num, fence in opening_fences:
                lang = fence.lstrip("`").strip()
                if not lang:
                    findings.append({
                        "file": filename,
                        "line": line_num,
                        "check": "code_lang_identifier",
                        "category": "code",
                        "severity": WARNING,
                        "message": "Code block missing language identifier",
                    })

    return findings


def resolve_run_dir(args):
    """Resolve the run directory from args."""
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


def load_run_report(run_dir):
    """Load report.json from the run directory if present."""
    report_path = run_dir / "report.json"
    if report_path.exists():
        try:
            with open(report_path) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return None
    return None


def format_summary_table(file_results):
    """Format a summary table showing pass/fail per file per check category."""
    categories = ["frontmatter", "dry", "structure", "code"]
    lines = []

    # Header
    name_width = max(len(f) for f in file_results) if file_results else 20
    name_width = max(name_width, 10)
    header = f"{'File':<{name_width}}  {'Front':>7}  {'DRY':>5}  {'Struct':>7}  {'Code':>6}"
    lines.append(header)
    lines.append("-" * len(header))

    error_count = 0
    warning_count = 0

    for filename in sorted(file_results):
        findings = file_results[filename]
        statuses = {}
        for cat in categories:
            cat_findings = [f for f in findings if f["category"] == cat]
            has_errors = any(f["severity"] == ERROR for f in cat_findings)
            has_warnings = any(f["severity"] == WARNING for f in cat_findings)
            if has_errors:
                statuses[cat] = "FAIL"
            elif has_warnings:
                statuses[cat] = "WARN"
            else:
                statuses[cat] = "OK"

        error_count += sum(1 for f in findings if f["severity"] == ERROR)
        warning_count += sum(1 for f in findings if f["severity"] == WARNING)

        row = (
            f"{filename:<{name_width}}  "
            f"{statuses.get('frontmatter', '-'):>7}  "
            f"{statuses.get('dry', '-'):>5}  "
            f"{statuses.get('structure', '-'):>7}  "
            f"{statuses.get('code', '-'):>6}"
        )
        lines.append(row)

    lines.append("")
    lines.append(f"Total: {error_count} error(s), {warning_count} warning(s)")
    return "\n".join(lines)


def format_verbose(file_results):
    """Format detailed findings per file."""
    lines = []
    for filename in sorted(file_results):
        findings = file_results[filename]
        if not findings:
            lines.append(f"{filename}: all checks passed")
            lines.append("")
            continue

        lines.append(f"{filename}:")
        for f in sorted(findings, key=lambda x: (x["line"], x["check"])):
            severity_tag = "ERROR" if f["severity"] == ERROR else "WARN "
            lines.append(
                f"  L{f['line']:>4}  [{severity_tag}] {f['check']}: {f['message']}"
            )
        lines.append("")

    error_count = sum(
        1 for findings in file_results.values()
        for f in findings if f["severity"] == ERROR
    )
    warning_count = sum(
        1 for findings in file_results.values()
        for f in findings if f["severity"] == WARNING
    )
    lines.append(f"Total: {error_count} error(s), {warning_count} warning(s)")
    return "\n".join(lines)


def format_json(file_results, run_dir, run_report):
    """Format machine-readable JSON output."""
    all_findings = []
    for filename, findings in file_results.items():
        all_findings.extend(findings)

    error_count = sum(1 for f in all_findings if f["severity"] == ERROR)
    warning_count = sum(1 for f in all_findings if f["severity"] == WARNING)

    output = {
        "run_dir": str(run_dir),
        "files_checked": len(file_results),
        "total_findings": len(all_findings),
        "errors": error_count,
        "warnings": warning_count,
        "passed": error_count == 0,
        "findings": all_findings,
    }
    if run_report:
        output["run_report"] = run_report

    return json.dumps(output, indent=2)


def main():
    parser = argparse.ArgumentParser(
        description="Quality-check generated docs drafts"
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
        "--verbose",
        action="store_true",
        help="Show detailed findings per file with line numbers",
    )
    parser.add_argument(
        "--output",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )
    args = parser.parse_args()

    run_dir = resolve_run_dir(args)
    run_report = load_run_report(run_dir)

    mdx_files = sorted(run_dir.glob("*.mdx"))
    if not mdx_files:
        print(f"No .mdx files found in {run_dir}", file=sys.stderr)
        return 1

    print(f"Evaluating {len(mdx_files)} file(s) in {run_dir.name}/\n")

    file_results = {}
    for mdx in mdx_files:
        findings = check_file(mdx)
        file_results[mdx.name] = findings

    # Output
    if args.output == "json":
        print(format_json(file_results, run_dir, run_report))
    elif args.verbose:
        print(format_verbose(file_results))
    else:
        print(format_summary_table(file_results))

    # Exit code: 0 if no errors (warnings are OK), 1 if any errors
    has_errors = any(
        f["severity"] == ERROR
        for findings in file_results.values()
        for f in findings
    )
    return 1 if has_errors else 0


if __name__ == "__main__":
    sys.exit(main())
