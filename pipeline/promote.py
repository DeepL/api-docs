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
    """Find a group by name, searching nested subgroups too. Returns the group dict or None."""
    for g in groups:
        if g.get("group", "").lower() == group_name.lower():
            return g
        for item in g.get("pages", []):
            if isinstance(item, dict) and item.get("group", "").lower() == group_name.lower():
                return item
    return None


def find_group_by_sibling_path(groups, nav_path):
    """Find the most specific group containing a page with the longest common path prefix."""
    best_group = None
    best_prefix_len = 0
    parts = nav_path.split("/")

    def _search(group):
        nonlocal best_group, best_prefix_len
        for item in group.get("pages", []):
            if isinstance(item, str):
                item_parts = item.split("/")
                common = sum(1 for a, b in zip(parts, item_parts) if a == b)
                if common > best_prefix_len:
                    best_prefix_len = common
                    best_group = group
            elif isinstance(item, dict):
                _search(item)

    for g in groups:
        _search(g)
    return best_group


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

    # Check if page already exists in ANY tab before adding
    for tab in tabs:
        for g in tab.get("groups", []):
            if page_in_nav(g.get("pages", []), nav_path):
                return None

    # Only add new pages to the Documentation tab (first tab)
    doc_tab = tabs[0]
    groups = doc_tab.get("groups", [])

    # Find the matching group by family name (searches nested subgroups too)
    group = find_group(groups, family_name)

    # Fallback: find a group whose pages share the longest path prefix
    if not group:
        group = find_group_by_sibling_path(groups, nav_path)

    if group:
        insert_page_in_group(group, nav_path, gap_type)
        return f"Added '{nav_path}' to existing group '{group['group']}'"
    else:
        new_group = {"group": family_name, "pages": [nav_path]}
        insert_idx = find_going_to_production_index(groups)
        groups.insert(insert_idx, new_group)
        return f"Created new group '{family_name}' with page '{nav_path}'"


def remove_from_nav(docs_json, nav_path):
    """Remove a page path from all tabs/groups in docs.json. Returns True if found and removed."""

    def _remove_recursive(pages):
        found = False
        i = 0
        while i < len(pages):
            item = pages[i]
            if isinstance(item, str) and item == nav_path:
                pages.pop(i)
                found = True
                continue
            if isinstance(item, dict) and "pages" in item:
                if _remove_recursive(item["pages"]):
                    found = True
            i += 1
        return found

    tabs = docs_json.get("navigation", {}).get("tabs", [])
    removed = False
    for tab in tabs:
        for group in tab.get("groups", []):
            if _remove_recursive(group.get("pages", [])):
                removed = True
    return removed


def add_redirect(docs_json, source_path, dest_path):
    """Add a redirect entry to docs.json. Returns description of change or None."""
    source = "/" + page_path_for_nav(source_path)
    destination = "/" + page_path_for_nav(dest_path)

    redirects = docs_json.setdefault("redirects", [])
    for r in redirects:
        if r["source"] == source:
            return None

    redirects.append({"source": source, "destination": destination})
    return f"redirect: {source} → {destination}"


def retire_pages(run_dir, docs_json, dry_run=False):
    """Delete retired pages, remove from navigation, and add redirects. Returns list of retired paths."""
    retire_path = run_dir / "retire.json"
    if not retire_path.exists():
        return []

    with open(retire_path) as f:
        retire_list = json.load(f)

    report = load_report(run_dir)
    targets = report.get("targets", []) if report else []

    retired = []
    nav_removals = []
    redirect_changes = []

    for rel_path in retire_list:
        full_path = REPO_ROOT / rel_path
        nav_path = page_path_for_nav(rel_path)

        if dry_run:
            exists = full_path.exists()
            print(f"  {'DELETE' if exists else 'SKIP (not found)'}: {rel_path}")
        else:
            if full_path.exists():
                full_path.unlink()
                print(f"  Retired: {rel_path}")
                retired.append(rel_path)

        if remove_from_nav(docs_json, nav_path):
            nav_removals.append(nav_path)
            if dry_run:
                print(f"    nav: removed '{nav_path}'")

        redirect_dest = next((t for t in targets if t != rel_path), None)
        if redirect_dest:
            change = add_redirect(docs_json, rel_path, redirect_dest)
            if change:
                redirect_changes.append(change)
                if dry_run:
                    print(f"    {change}")

    if nav_removals:
        print(f"\n{'Would remove' if dry_run else 'Removed'} {len(nav_removals)} page(s) from docs.json navigation.")
    if redirect_changes:
        print(f"{'Would add' if dry_run else 'Added'} {len(redirect_changes)} redirect(s).")

    return retired


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

        # Update docs.json navigation (skip api-reference/ — those are auto-discovered from openapi frontmatter)
        if family and not canonical_rel.startswith("api-reference/"):
            change = update_docs_json(docs_json, nav_path, family, gap_type)
            if change:
                nav_changes.append(change)
                if args.dry_run:
                    print(f"    nav: {change}")

    # Retire pages (delete files + remove from nav)
    retired = retire_pages(run_dir, docs_json, dry_run=args.dry_run)

    # Write updated docs.json
    if (nav_changes or retired) and not args.dry_run:
        with open(DOCS_JSON_PATH, "w") as f:
            json.dump(docs_json, f, indent=2)
            f.write("\n")
        print(f"\nUpdated docs.json:")
        for change in nav_changes:
            print(f"  {change}")
    elif (nav_changes or retired) and args.dry_run:
        print(f"\nWould update docs.json with {len(nav_changes)} addition(s) and {len(retired)} removal(s)")
    else:
        print("\nNo docs.json changes needed (all pages already in navigation).")

    print(f"\n{'Would promote' if args.dry_run else 'Promoted'} {len(promoted)} file(s).")

    # Run broken-links check after promotion
    if not args.dry_run and promoted:
        run_broken_links_check()

    return 0


if __name__ == "__main__":
    sys.exit(main())
