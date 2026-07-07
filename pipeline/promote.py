#!/usr/bin/env python3
"""
Promote approved drafts from a pipeline run into the canonical docs tree.

Copies .mdx drafts to their canonical paths (derived from the `--`-delimited
filenames) and updates docs.json navigation so new pages appear in the right
groups.

Usage:
    python pipeline/promote.py pipeline/drafts/20260706-192742
    python pipeline/promote.py --latest
    python pipeline/promote.py --latest --dry-run
    python pipeline/promote.py --latest --file docs--admin--overview.mdx
"""

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
DOCS_JSON_PATH = REPO_ROOT / "docs.json"
DRAFTS_DIR = REPO_ROOT / "pipeline" / "drafts"


def find_latest_run():
    """Return the most recent run directory under pipeline/drafts/."""
    if not DRAFTS_DIR.exists():
        return None
    runs = sorted(
        [d for d in DRAFTS_DIR.iterdir() if d.is_dir()],
        key=lambda d: d.stat().st_mtime,
    )
    return runs[-1] if runs else None


def draft_to_canonical(filename):
    """Convert a draft filename to its canonical relative path.

    'docs--admin--overview.mdx' -> 'docs/admin/overview.mdx'
    """
    return filename.replace("--", "/")


def page_path_for_nav(canonical_path):
    """Strip the .mdx extension for docs.json page references.

    'docs/admin/overview.mdx' -> 'docs/admin/overview'
    """
    return str(Path(canonical_path).with_suffix(""))


def load_report(run_dir):
    """Load report.json from the run directory, if it exists."""
    report_path = run_dir / "report.json"
    if report_path.exists():
        with open(report_path) as f:
            return json.load(f)
    return None


def build_family_map(report):
    """Build a mapping from canonical page path (no ext) to family name using the report."""
    family_map = {}
    if not report:
        return family_map
    for entry in report.get("generated", []):
        page_path = entry.get("path", "")
        family = entry.get("gap", {}).get("family", "")
        if page_path and family:
            family_map[page_path_for_nav(page_path)] = family
    return family_map


def get_draft_type(report, canonical_path):
    """Determine the gap type for a draft from the report."""
    if not report:
        return "unknown"
    nav_path = page_path_for_nav(canonical_path)
    for entry in report.get("generated", []):
        entry_nav = page_path_for_nav(entry.get("path", ""))
        if entry_nav == nav_path:
            return entry.get("gap", {}).get("type", "unknown")
    return "unknown"


def page_in_nav(pages, nav_path):
    """Check recursively whether nav_path already exists in a pages array."""
    for item in pages:
        if isinstance(item, str) and item == nav_path:
            return True
        if isinstance(item, dict) and "pages" in item:
            if page_in_nav(item["pages"], nav_path):
                return True
    return False


def find_group(groups, group_name):
    """Find a group by name in the groups list. Returns (index, group) or (None, None)."""
    for i, g in enumerate(groups):
        if g.get("group", "").lower() == group_name.lower():
            return i, g
    return None, None


def find_going_to_production_index(groups):
    """Find the index of the 'Going to Production' group."""
    for i, g in enumerate(groups):
        if g.get("group") == "Going to Production":
            return i
    return len(groups)


def insert_page_in_group(group, nav_path, gap_type):
    """Insert a page path into a group's pages array at the appropriate position."""
    pages = group["pages"]

    if gap_type in ("undocumented_product", "missing_orientation"):
        # Overview pages go first
        pages.insert(0, nav_path)
    elif gap_type == "missing_tutorial":
        # Tutorials go after overview (position 1), or first if no overview
        insert_at = 0
        for i, item in enumerate(pages):
            if isinstance(item, str) and "overview" in item.lower():
                insert_at = i + 1
                break
        pages.insert(insert_at, nav_path)
    else:
        # Everything else appends
        pages.append(nav_path)


def update_docs_json(docs_json, nav_path, family_name, gap_type):
    """Add nav_path to the docs.json navigation under the correct group.

    Returns a description of the change made, or None if no change was needed.
    """
    tabs = docs_json.get("navigation", {}).get("tabs", [])
    if not tabs:
        return None

    # Only modify the Documentation tab (first tab)
    doc_tab = tabs[0]
    groups = doc_tab.get("groups", [])

    # Check if page already exists anywhere in the Documentation tab
    for g in groups:
        if page_in_nav(g.get("pages", []), nav_path):
            return None

    # Find the matching group by family name
    _, group = find_group(groups, family_name)

    if group:
        insert_page_in_group(group, nav_path, gap_type)
        return f"Added '{nav_path}' to existing group '{group['group']}'"
    else:
        # Create a new group
        new_group = {"group": family_name, "pages": [nav_path]}
        insert_idx = find_going_to_production_index(groups)
        groups.insert(insert_idx, new_group)
        return f"Created new group '{family_name}' with page '{nav_path}'"


def run_broken_links_check():
    """Run Mintlify broken-links check if available."""
    try:
        result = subprocess.run(
            ["npx", "mint", "broken-links"],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
            timeout=60,
        )
        if result.returncode == 0:
            print("\nBroken-links check passed.")
        else:
            print(f"\nBroken-links check found issues:\n{result.stdout}")
            if result.stderr:
                print(result.stderr)
    except FileNotFoundError:
        print("\nNote: 'npx' not found, skipping broken-links check.")
    except subprocess.TimeoutExpired:
        print("\nNote: broken-links check timed out, skipping.")
    except Exception as e:
        print(f"\nNote: Could not run broken-links check: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Promote approved drafts into the canonical docs tree"
    )
    parser.add_argument(
        "run_dir",
        nargs="?",
        help="Path to the run directory (e.g. pipeline/drafts/20260706-192742)",
    )
    parser.add_argument(
        "--latest",
        action="store_true",
        help="Auto-pick the most recent run directory",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be promoted without making changes",
    )
    parser.add_argument(
        "--file",
        help="Promote a specific draft file only (e.g. docs--admin--overview.mdx)",
    )
    args = parser.parse_args()

    # Resolve run directory
    if args.latest:
        run_dir = find_latest_run()
        if not run_dir:
            print("Error: No run directories found under pipeline/drafts/")
            return 1
    elif args.run_dir:
        run_dir = Path(args.run_dir)
        if not run_dir.is_absolute():
            run_dir = REPO_ROOT / run_dir
    else:
        parser.error("Provide a run directory path or use --latest")
        return 1

    if not run_dir.exists():
        print(f"Error: Run directory not found: {run_dir}")
        return 1

    print(f"Run directory: {run_dir.relative_to(REPO_ROOT)}")

    # Collect draft files
    draft_files = sorted(
        f for f in run_dir.iterdir()
        if f.suffix == ".mdx" and f.name != "report.json"
    )

    if args.file:
        draft_files = [f for f in draft_files if f.name == args.file]
        if not draft_files:
            print(f"Error: Draft file '{args.file}' not found in {run_dir.name}")
            return 1

    if not draft_files:
        print("No .mdx draft files found in the run directory.")
        return 0

    # Load report for family/type metadata
    report = load_report(run_dir)
    family_map = build_family_map(report)

    # Load docs.json
    with open(DOCS_JSON_PATH) as f:
        docs_json = json.load(f)

    nav_changes = []
    promoted = []

    for draft_file in draft_files:
        canonical_rel = draft_to_canonical(draft_file.name)
        canonical_path = REPO_ROOT / canonical_rel
        nav_path = page_path_for_nav(canonical_rel)
        gap_type = get_draft_type(report, canonical_rel)
        family = family_map.get(nav_path, "")

        if args.dry_run:
            exists = canonical_path.exists()
            print(f"  {'OVERWRITE' if exists else 'NEW'}: {draft_file.name} -> {canonical_rel}")
        else:
            # Create parent directories if needed
            canonical_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(draft_file, canonical_path)
            print(f"  Promoted: {canonical_rel}")

        promoted.append(canonical_rel)

        # Update docs.json navigation
        if family:
            change = update_docs_json(docs_json, nav_path, family, gap_type)
            if change:
                nav_changes.append(change)
                if args.dry_run:
                    print(f"    nav: {change}")

    # Write updated docs.json
    if nav_changes and not args.dry_run:
        with open(DOCS_JSON_PATH, "w") as f:
            json.dump(docs_json, f, indent=2)
            f.write("\n")
        print(f"\nUpdated docs.json:")
        for change in nav_changes:
            print(f"  {change}")
    elif nav_changes and args.dry_run:
        print(f"\nWould update docs.json with {len(nav_changes)} change(s)")
    else:
        print("\nNo docs.json changes needed (all pages already in navigation).")

    print(f"\n{'Would promote' if args.dry_run else 'Promoted'} {len(promoted)} file(s).")

    # Run broken-links check after promotion
    if not args.dry_run and promoted:
        run_broken_links_check()

    return 0


if __name__ == "__main__":
    sys.exit(main())
