#!/usr/bin/env python3
"""
Agentic docs generation pipeline.

Takes the gap report from detect_gaps.py and uses Claude to generate
missing documentation pages.

Usage:
    python pipeline/generate.py                          # generate for all gaps
    python pipeline/generate.py --section voice           # generate for one family
    python pipeline/generate.py --type missing_orientation # generate one gap type
    python pipeline/generate.py --dry-run                 # show what would be generated
    python pipeline/generate.py --force                   # regenerate even if files exist
    python pipeline/generate.py --section admin --force   # regenerate one section
    python pipeline/generate.py --ignore-open-prs         # draft gaps even if a PR is open for them

Gaps that an open PR already covers are skipped before any model call — a gap is
only closed when its PR merges, so every run would otherwise redraft and reship
the same pages. See pipeline/open_prs.py.
"""

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

from util import build_authoring_system_prompt, looks_like_mdx, format_retry_prompt
from open_prs import EXIT_NOTHING_TO_DO, fetch_open_prs, split_claimed_gaps
from detect_gaps import page_file

REPO_ROOT = Path(__file__).resolve().parent.parent
OPENAPI_PATH = REPO_ROOT / "api-reference" / "openapi.yaml"
STANDARDS_PATH = REPO_ROOT / "standards" / "ia.yaml"
DOCS_DIR = REPO_ROOT / "docs"

MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 8192

# Gap types that aren't "write a new page" tasks — generate skips these. They need a
# human decision (placement), a nav edit, or a removal, handled elsewhere.
NON_GENERATIVE = {
    "narrative_home_unplaced", "missing_hub_entry", "apiref_narrative_page",
    "ungrouped_tag", "missing_api_reference_group", "reference_only_no_guide",
}
OVERVIEW_TYPES = {"missing_overview", "missing_product_tab", "undocumented_product", "missing_orientation"}


def slugify(text):
    s = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return s or "how-to"


def title_from_content(content):
    m = re.search(r'^title:\s*["\']?(.+?)["\']?\s*$', content or "", re.MULTILINE)
    return m.group(1).strip() if m else ""


def load_file(path):
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


def load_existing_page(gap):
    """Content of the page a gap edits, resolved from its nav entry.

    Raises instead of returning nothing. A gap's `path` is a docs.json nav entry
    with no extension, so opening it directly either fails or (when a directory
    shares the page's name) hands back a directory. Both used to surface as an
    empty page, which turned "expand this page" into "write one from scratch"
    and silently discarded the real content.
    """
    page_path = gap.get("path", "")
    resolved = page_file(page_path)
    if not resolved:
        raise FileNotFoundError(f"no .mdx or .md file backs the nav entry '{page_path}'")
    content = load_file(resolved)
    if not content.strip():
        raise ValueError(f"{resolved.relative_to(REPO_ROOT)} is empty, refusing to rewrite it from nothing")
    return content


def load_openapi_for_tags(tags):
    """Extract the portion of the OpenAPI spec whose endpoints carry any of `tags`."""
    with open(OPENAPI_PATH) as f:
        spec = yaml.safe_load(f)

    want = set(tags)
    relevant_paths = {}
    for path, methods in (spec.get("paths") or {}).items():
        for method, details in methods.items():
            if method in ("get", "post", "put", "patch", "delete"):
                if set(details.get("tags", [])) & want:
                    relevant_paths.setdefault(path, {})[method] = details

    return yaml.dump({"paths": relevant_paths}, default_flow_style=False)


def family_all_tags(cfg):
    return [t for grp in cfg.get("groups", []) for t in grp.get("tags", [])]


def group_tags(cfg, group_name):
    for grp in cfg.get("groups", []):
        if grp.get("name") == group_name:
            return grp.get("tags", [])
    return family_all_tags(cfg)


def find_existing_docs_for_family(family_name):
    """Load existing docs content for a family (for context/cross-linking).

    Membership comes from docs.json (the live structure), not a hardcoded
    directory map: gather the pages under the family's product tab and its API
    Reference group.
    """
    from detect_gaps import load_docs_json, collect_pages_under, load_yaml, STANDARDS_PATH as SP

    cfg = load_yaml(SP).get("families", {}).get(family_name, {})
    docs_json = load_docs_json()

    # Gather context from the family's tab (own tab is named after the family),
    # its parent tab if it nests, and its API Reference group(s).
    names = [family_name]
    home = cfg.get("narrative_home")
    if home and home not in ("own", "reference_only", "unplaced"):
        names.append(home)  # parent tab it nests under
    names += [grp.get("name") for grp in cfg.get("groups", []) if grp.get("name")]

    page_paths = []
    for name in names:
        if name:
            page_paths.extend(collect_pages_under(docs_json, name))

    context_docs = {}
    for pp in dict.fromkeys(page_paths):  # dedupe, preserve order
        full_path = page_file(pp)
        if full_path:
            context_docs[str(full_path.relative_to(REPO_ROOT))] = load_file(full_path)
    return context_docs


def make_client():
    """Build the API client, importing the SDK only when a call is imminent.

    Kept lazy so --dry-run, gap detection and the tests all work without the
    SDK installed — none of them talk to the model.
    """
    try:
        import anthropic
    except ImportError:
        print("Install the Anthropic SDK: pip install anthropic")
        sys.exit(1)
    return anthropic.Anthropic()


def build_system_prompt():
    # All writing rules live in the agent files, assembled in one place.
    return build_authoring_system_prompt(
        "You are a documentation writer for DeepL's developer documentation."
    )


def build_generation_prompt(gap, family_name, openapi_context, existing_docs_context):
    """Build the user prompt for a specific gap."""
    gap_type = gap["type"]
    existing_docs_summary = ""
    if existing_docs_context:
        existing_docs_summary = "\n\n## Existing docs in this section (for context and cross-linking)\n\n"
        for path, content in existing_docs_context.items():
            truncated = content[:2000] + "..." if len(content) > 2000 else content
            existing_docs_summary += f"### {path}\n```\n{truncated}\n```\n\n"

    openapi_section = f"""## OpenAPI spec for {family_name}

```yaml
{openapi_context}
```"""

    if gap_type in OVERVIEW_TYPES:
        return f"""Write an overview page (Diataxis: explanation/orientation) for the {family_name} product section.

This is the landing page for the section: what the product does, who it's for, and links to everything in it.

Target path: docs/{family_name.lower()}/overview.mdx

Follow the docs-writer guidelines exactly — they cover structure, DRY rules, and what to include/exclude.

{openapi_section}
{existing_docs_summary}"""

    elif gap_type == "missing_group_coverage":
        group = gap.get("group", family_name)
        return f"""Write a guide for the "{group}" capability of the {family_name} product.

The endpoints below (the {group} group) have no guide yet. Write the single most valuable guide for a developer's first real need with them — a tutorial or a how-to, whichever fits best. Give it a goal-oriented title grounded in these endpoints; don't invent capabilities.

IMPORTANT: include `covers: [{group}]` in the frontmatter so the pipeline records that this guide covers the {group} group.

Follow the docs-writer guidelines exactly.

{openapi_section}
{existing_docs_summary}"""

    elif gap_type == "missing_howto":
        return f"""Write a how-to guide (Diataxis: how-to) for the {family_name} product.

The section exposes the endpoints below but has no how-to guide. Choose the SINGLE most valuable how-to — a specific, real task a developer needs to accomplish with these endpoints (not an overview, not a tutorial). Give it a goal-oriented title ("Handle ...", "Use ...", "Configure ..."). Ground it in the actual endpoints; don't invent capabilities.

Follow the docs-writer guidelines exactly.

{openapi_section}
{existing_docs_summary}"""

    elif gap_type == "missing_tutorial":
        return f"""Write a tutorial (Diataxis: tutorial) for the {family_name} section.

This section has no tutorial. Pick the most common/important use case based on the endpoints available. The tutorial should be completable in 5-10 minutes.

Target path: docs/{family_name.lower()}/tutorial.mdx (choose a more specific filename based on the content)

Follow the docs-writer guidelines exactly.

{openapi_section}
{existing_docs_summary}"""

    elif gap_type == "thin_page":
        page_path = gap.get("path", "")
        page_content = load_existing_page(gap)
        return f"""Expand this thin page. It currently has only {gap.get('word_count', 0)} words.

Current content of {page_path}:
```
{page_content}
```

Rewrite it as a complete, useful page. Determine the appropriate Diataxis type from the content and title, then write it properly for that type.

Follow the docs-writer guidelines exactly.

{openapi_section}
{existing_docs_summary}"""

    elif gap_type == "missing_code_examples":
        page_path = gap.get("path", "")
        page_content = load_existing_page(gap)
        return f"""Add code examples to this page. It's a guide but has no runnable code.

Current content of {page_path}:
```
{page_content}
```

Add code examples where appropriate. Don't change the page structure or prose significantly, just add the missing code.

Follow the docs-writer guidelines exactly.

{openapi_section}
{existing_docs_summary}"""

    elif gap_type == "missing_description":
        page_path = gap.get("path", "")
        page_content = load_existing_page(gap)[:500]
        return f"""Generate a frontmatter description for this page.

Current content of {page_path} (first 500 chars):
```
{page_content}
```

Output ONLY the description string (no quotes, no frontmatter, just the text).
Follow the docs-writer description guidelines: uniquely descriptive, action-oriented, max 160 characters."""

    else:
        return f"""Handle this documentation gap:

{json.dumps(gap, indent=2)}

Product family: {family_name}

Follow the docs-writer guidelines exactly.

{openapi_section}
{existing_docs_summary}"""


def _complete(client, system_prompt, messages):
    response = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=system_prompt,
        messages=messages,
    )
    return response.content[0].text


def generate_content(client, system_prompt, user_prompt, expect_file=True):
    """Call Claude to generate content.

    A reply that isn't a page gets one corrective turn rather than failing the
    run. The docs-writer guidelines are written for a harness with tools, so the
    model occasionally obliges by narrating research it cannot do and returns a
    transcript instead of a file.
    """
    messages = [{"role": "user", "content": user_prompt}]
    text = _complete(client, system_prompt, messages)

    if not expect_file or looks_like_mdx(text) or not text.strip():
        return text

    print("  Reply was not a page (commentary or a faked tool transcript), asking again")
    messages += [
        # Echo a slice back rather than the whole thing: the bad reply can run to
        # hundreds of lines and only needs to be identifiable.
        {"role": "assistant", "content": text[:500].strip()},
        {"role": "user", "content": format_retry_prompt(
            "it did not start with YAML frontmatter (---)")},
    ]
    return _complete(client, system_prompt, messages)


def determine_output_path(gap, family_name, content=None):
    """Determine where to write the generated content."""
    gap_type = gap["type"]

    if gap_type in OVERVIEW_TYPES:
        return DOCS_DIR / family_name.lower() / "overview.mdx"

    elif gap_type == "missing_tutorial":
        return DOCS_DIR / family_name.lower() / "tutorial.mdx"

    elif gap_type in ("missing_howto", "missing_group_coverage"):
        # The model picks the topic; derive the filename from its title.
        slug = slugify(title_from_content(content))
        return DOCS_DIR / family_name.lower() / f"{slug}.mdx"

    elif gap_type in ("thin_page", "missing_code_examples", "missing_description"):
        # Resolve the nav entry to the real file. Without the extension the draft
        # is written as `docs--a--b` and promote.py, which only collects *.mdx,
        # drops it without a word — the page looks generated but never ships.
        return page_file(gap.get("path", ""))

    return None  # non-generative types skipped


def _predicted_path(gap):
    """The repo-relative path a gap would write to, or None if unpredictable.

    Used only for open-PR matching. For missing_howto / missing_group_coverage the
    filename comes from the title the model invents, so there's nothing to predict
    and those gaps are matched on their gap key instead.
    """
    out_path = determine_output_path(gap, gap.get("family", "unknown"))
    if not out_path:
        return None
    try:
        return str(out_path.relative_to(REPO_ROOT))
    except ValueError:
        return None


def _pr_review_hint(claimed):
    """One line pointing at the PRs worth reviewing, for the skip summary."""
    numbers = sorted({pr.get("number") for _, pr, _ in claimed if pr.get("number")})
    listed = ", ".join(f"#{n}" for n in numbers)
    return f"Review or close {listed} to let the pipeline redraft these."


def apply_description(gap, description):
    """Insert a frontmatter description into an existing page."""
    page_path = page_file(gap.get("path", ""))
    if not page_path:
        return False
    content = page_path.read_text(encoding="utf-8")

    if not content.startswith("---"):
        return False

    end = content.find("---", 3)
    if end == -1:
        return False

    frontmatter = content[3:end]
    if "description:" in frontmatter:
        return False

    new_frontmatter = frontmatter.rstrip() + f'\ndescription: "{description.strip()}"\n'
    new_content = "---" + new_frontmatter + "---" + content[end + 3:]
    page_path.write_text(new_content, encoding="utf-8")
    return True


def run_gap_detection(section_filter=None, force=False):
    """Run detect_gaps.py and return parsed JSON."""
    cmd = [sys.executable, str(REPO_ROOT / "pipeline" / "detect_gaps.py"), "--output", "json"]
    if section_filter:
        cmd.extend(["--section", section_filter])
    if force:
        cmd.append("--force")
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=REPO_ROOT)
    return json.loads(result.stdout)


def main():
    parser = argparse.ArgumentParser(description="Generate missing documentation")
    parser.add_argument("--section", help="Generate for one product family only")
    parser.add_argument("--type", help="Generate for one gap type only")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be generated")
    parser.add_argument("--force", action="store_true", help="Regenerate even when files already exist")
    parser.add_argument("--gap-report", help="Path to existing gap report JSON (skips re-running detection)")
    parser.add_argument(
        "--ignore-open-prs", action="store_true",
        help="Draft every gap, even ones an open PR already covers (default: skip those)",
    )
    args = parser.parse_args()

    if args.gap_report:
        with open(args.gap_report) as f:
            report = json.load(f)
    else:
        report = run_gap_detection(args.section, force=args.force)

    gaps = report.get("gaps", [])
    if args.section:
        gaps = [g for g in gaps if g.get("family", "").lower() == args.section.lower()]
    if args.type:
        gaps = [g for g in gaps if g["type"] == args.type]

    if not gaps:
        print("No gaps to generate for.")
        return EXIT_NOTHING_TO_DO

    # Drop gaps that an open PR already covers. Done here, before any model call,
    # so a duplicate run costs nothing instead of a full generate → review cycle
    # that ends in a PR nobody wants.
    if args.ignore_open_prs:
        print("Skipping the open-PR check (--ignore-open-prs).")
    else:
        prs, err = fetch_open_prs()
        if prs is None:
            print(f"Warning: could not check open PRs ({err}).")
            print("  Proceeding without deduplication — this run may duplicate an open PR.")
        else:
            gaps, claimed = split_claimed_gaps(
                gaps, prs,
                path_for_gap=_predicted_path,
            )
            if claimed:
                print(f"Skipping {len(claimed)} gap(s) already covered by an open PR:")
                for gap, pr, reason in claimed:
                    print(f"  - {gap['type']} ({gap.get('family', 'site-wide')}): {reason}")
                print(f"  {_pr_review_hint(claimed)}")

    if not gaps:
        print("\nEvery detected gap is already covered by an open PR. Nothing to do.")
        print("Merge or close those PRs, then re-run the pipeline.")
        return EXIT_NOTHING_TO_DO

    standards = yaml.safe_load(open(STANDARDS_PATH))
    families = standards.get("families", {})

    if args.dry_run:
        print(f"Would process {len(gaps)} gaps:\n")
        for g in gaps:
            family = g.get("family", "unknown")
            print(f"  [{g['severity'].upper()}] {g['type']}: {g['description']}")
            if g["type"] in NON_GENERATIVE:
                print("    -> skip (needs a human decision or a non-generation step)")
            else:
                out_path = determine_output_path(g, family)
                if out_path:
                    print(f"    -> {out_path.relative_to(REPO_ROOT)}")
                elif g.get("path"):
                    print(f"    -> skip (no file backs the nav entry '{g['path']}')")
                else:
                    print(f"    -> filename chosen from the generated title")
            print()
        return 0

    client = make_client()
    system_prompt = build_system_prompt()

    run_id = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    run_dir = REPO_ROOT / "pipeline" / "drafts" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    print(f"Run: {run_dir.relative_to(REPO_ROOT)}")

    generated = []
    errors = []

    for i, gap in enumerate(gaps):
        family = gap.get("family", "unknown")

        if gap["type"] in NON_GENERATIVE:
            print(f"[{i+1}/{len(gaps)}] Skipping {gap['type']} for {family} (needs a human decision or a non-generation step)")
            continue

        print(f"[{i+1}/{len(gaps)}] Generating: {gap['type']} for {family}...")

        try:
            # Scope the spec to the gap's group when it targets one, else the whole family.
            cfg = families.get(family, {})
            tags = group_tags(cfg, gap["group"]) if gap.get("group") else family_all_tags(cfg)
            openapi_context = load_openapi_for_tags(tags)
            existing_docs = find_existing_docs_for_family(family)
            user_prompt = build_generation_prompt(gap, family, openapi_context, existing_docs)

            # Every gap but missing_description wants a whole file back;
            # missing_description wants a bare string, so don't shape-check it.
            content = generate_content(
                client, system_prompt, user_prompt,
                expect_file=gap["type"] != "missing_description",
            )

            if gap["type"] == "missing_description":
                description = content.strip().strip('"').strip("'")
                page_path = gap.get("path", "")
                if apply_description(gap, description):
                    print(f"  Applied description to {page_path}")
                    generated.append({"gap": gap, "action": "description_applied", "path": page_path})
                else:
                    print(f"  Could not apply description to {page_path}")
                    errors.append({"gap": gap, "error": "Could not insert description"})
            else:
                out_path = determine_output_path(gap, family, content)
                if out_path:
                    rel = out_path.relative_to(REPO_ROOT)

                    draft_path = run_dir / str(rel).replace("/", "--")
                    draft_path.write_text(content, encoding="utf-8")

                    print(f"  Wrote {draft_path.relative_to(REPO_ROOT)}")
                    generated.append({"gap": gap, "action": "file_written", "path": str(rel), "draft": str(draft_path.relative_to(REPO_ROOT))})
                else:
                    detail = (
                        f"no file backs the nav entry '{gap['path']}'"
                        if gap.get("path") else "no output path could be determined"
                    )
                    print(f"  Skipping: {detail}")
                    errors.append({"gap": gap, "error": detail})

        except Exception as e:
            print(f"  Error: {e}")
            errors.append({"gap": gap, "error": str(e)})

    print(f"\nDone. Generated: {len(generated)}, Errors: {len(errors)}")

    summary = {"generated": generated, "errors": errors, "run_id": run_id, "model": MODEL}
    summary_path = run_dir / "report.json"
    summary_path.write_text(json.dumps(summary, indent=2))
    print(f"Report: {summary_path.relative_to(REPO_ROOT)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
