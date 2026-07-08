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

try:
    import anthropic
except ImportError:
    print("Install the Anthropic SDK: pip install anthropic")
    sys.exit(1)


from util import build_authoring_system_prompt

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


def load_openapi_for_family(family_name, families):
    """Extract the relevant portion of the OpenAPI spec for a product family."""
    with open(OPENAPI_PATH) as f:
        spec = yaml.safe_load(f)

    family_config = families.get(family_name, {})
    family_tags = set(family_config.get("tags", [family_name]))

    relevant_paths = {}
    for path, methods in (spec.get("paths") or {}).items():
        for method, details in methods.items():
            if method in ("get", "post", "put", "patch", "delete"):
                endpoint_tags = set(details.get("tags", []))
                if endpoint_tags & family_tags:
                    relevant_paths.setdefault(path, {})[method] = details

    return yaml.dump({"paths": relevant_paths}, default_flow_style=False)


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
    ref = cfg.get("api_reference_group")
    names += [ref] if isinstance(ref, str) else list(ref or [])

    page_paths = []
    for name in names:
        if name:
            page_paths.extend(collect_pages_under(docs_json, name))

    context_docs = {}
    for pp in dict.fromkeys(page_paths):  # dedupe, preserve order
        for ext in (".mdx", ".md"):
            full_path = REPO_ROOT / (pp + ext)
            if full_path.exists():
                context_docs[pp + ext] = load_file(full_path)
                break
    return context_docs


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
        page_content = load_file(REPO_ROOT / page_path)
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
        page_content = load_file(REPO_ROOT / page_path)
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
        page_content = load_file(REPO_ROOT / page_path)[:500]
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


def generate_content(client, system_prompt, user_prompt):
    """Call Claude to generate content."""
    response = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )
    return response.content[0].text


def determine_output_path(gap, family_name, content=None):
    """Determine where to write the generated content."""
    gap_type = gap["type"]

    if gap_type in OVERVIEW_TYPES:
        return DOCS_DIR / family_name.lower() / "overview.mdx"

    elif gap_type == "missing_tutorial":
        return DOCS_DIR / family_name.lower() / "tutorial.mdx"

    elif gap_type == "missing_howto":
        # The model picks the topic; derive the filename from its title.
        slug = slugify(title_from_content(content))
        return DOCS_DIR / family_name.lower() / f"{slug}.mdx"

    elif gap_type in ("thin_page", "missing_code_examples"):
        return REPO_ROOT / gap["path"]

    return None  # missing_description handled inline; non-generative types skipped


def apply_description(gap, description):
    """Insert a frontmatter description into an existing page."""
    page_path = REPO_ROOT / gap["path"]
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
        return 0

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
            print()
        return 0

    client = anthropic.Anthropic()
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
            openapi_context = load_openapi_for_family(family, families)
            existing_docs = find_existing_docs_for_family(family)
            user_prompt = build_generation_prompt(gap, family, openapi_context, existing_docs)

            content = generate_content(client, system_prompt, user_prompt)

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
                    print(f"  No output path determined, skipping")
                    errors.append({"gap": gap, "error": "No output path"})

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
