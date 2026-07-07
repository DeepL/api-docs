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


REPO_ROOT = Path(__file__).resolve().parent.parent
OPENAPI_PATH = REPO_ROOT / "api-reference" / "openapi.yaml"
CLAUDE_MD_PATH = REPO_ROOT / "CLAUDE.md"
DIATAXIS_PATH = REPO_ROOT / ".claude" / "agents" / "diataxis.md"
DOCS_WRITER_PATH = REPO_ROOT / ".claude" / "agents" / "docs-writer.md"
STANDARDS_PATH = REPO_ROOT / "standards" / "ia.yaml"
DOCS_DIR = REPO_ROOT / "docs"

MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 8192


def load_file(path):
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


def load_openapi_for_family(family_name, overrides):
    """Extract the relevant portion of the OpenAPI spec for a product family."""
    with open(OPENAPI_PATH) as f:
        spec = yaml.safe_load(f)

    family_config = overrides.get(family_name, {})
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
    """Find existing docs content for a product family (for context)."""
    from detect_gaps import FAMILY_TO_DOCS_DIRS, find_existing_docs

    existing = find_existing_docs()
    prefixes = FAMILY_TO_DOCS_DIRS.get(family_name, [f"docs/{family_name.lower()}"])
    context_docs = {}
    for doc_key, doc in existing.items():
        for prefix in prefixes:
            if doc_key.startswith(prefix) or doc["path"].startswith(prefix):
                full_path = REPO_ROOT / doc["path"]
                if full_path.exists():
                    context_docs[doc["path"]] = load_file(full_path)
                break
    return context_docs


def build_system_prompt():
    """Build the system prompt from CLAUDE.md, docs-writer agent, and Diataxis guidelines."""
    claude_md = load_file(CLAUDE_MD_PATH)
    diataxis = load_file(DIATAXIS_PATH)
    docs_writer = load_file(DOCS_WRITER_PATH)
    standards = load_file(STANDARDS_PATH)

    return f"""You are a documentation writer for DeepL's developer documentation.

You write .mdx files for a Mintlify-powered docs site. The docs-writer guidelines
below are your primary instructions. The style guide (CLAUDE.md) provides general
writing principles. When they conflict, the docs-writer guidelines win.

## Style Guide (CLAUDE.md)

{claude_md}

## Docs Writer Guidelines

{docs_writer}

## Diataxis Framework

{diataxis}

## IA Standards

{standards}

## Output Format

- Output ONLY the .mdx file content. No commentary, no explanation, no markdown fences.
- Start with frontmatter (---).
- Follow the Diataxis type specified in the request exactly.
- Never invent API parameters or behavior. Only document what's in the OpenAPI spec provided.
"""


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

    if gap_type == "undocumented_product":
        return f"""Write an overview page (Diataxis: explanation/orientation) for the {family_name} product section.

This product has NO documentation pages yet. This will be the landing page for the section.

Target path: docs/{family_name.lower()}/overview.mdx

Follow the docs-writer guidelines exactly — they cover structure, DRY rules, and what to include/exclude.

{openapi_section}
{existing_docs_summary}"""

    elif gap_type == "missing_orientation":
        return f"""Write an overview page (Diataxis: explanation/orientation) for the {family_name} section.

This section has existing docs but no overview page. This will be the landing page for the section.

Target path: docs/{family_name.lower()}/overview.mdx

Follow the docs-writer guidelines exactly — they cover structure, DRY rules, and what to include/exclude.

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


def determine_output_path(gap, family_name):
    """Determine where to write the generated content."""
    gap_type = gap["type"]

    if gap_type in ("undocumented_product", "missing_orientation"):
        return DOCS_DIR / family_name.lower() / "overview.mdx"

    elif gap_type == "missing_tutorial":
        return DOCS_DIR / family_name.lower() / "tutorial.mdx"

    elif gap_type in ("thin_page", "missing_code_examples"):
        return REPO_ROOT / gap["path"]

    elif gap_type == "missing_description":
        return None  # handled differently

    return None


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
    overrides = standards.get("product_family_overrides", {})

    if args.dry_run:
        print(f"Would generate content for {len(gaps)} gaps:\n")
        for g in gaps:
            family = g.get("family", "unknown")
            out_path = determine_output_path(g, family)
            print(f"  [{g['severity'].upper()}] {g['type']}: {g['description']}")
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
        print(f"[{i+1}/{len(gaps)}] Generating: {gap['type']} for {family}...")

        try:
            openapi_context = load_openapi_for_family(family, overrides)
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
                out_path = determine_output_path(gap, family)
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
