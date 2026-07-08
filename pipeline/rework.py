#!/usr/bin/env python3
"""
Rework existing docs pages (Phase 2 IA cleanup).

Unlike generate.py (which fills gaps with new pages), this script transforms
existing content: consolidate, merge, split, expand, retire, or rework pages.
Outputs go to pipeline/drafts/<timestamp>/ so the standard evaluate → review →
promote → ship flow works unchanged.

Usage:
    python pipeline/rework.py consolidate \
        --source docs/getting-started/intro.mdx docs/getting-started/about.mdx \
        --target docs/getting-started/intro.mdx \
        --instruction "Rework Introduction as orientation page, absorb About content"

    python pipeline/rework.py merge \
        --source docs/translate/xml-html/xml.mdx docs/translate/xml-html/structured-content.mdx \
        --target docs/translate/xml-html/handle-xml-content.mdx \
        --instruction "Merge into one Handle XML content how-to"

    python pipeline/rework.py split \
        --source docs/translate/xml-html/tag-handling-v2.mdx \
        --target docs/translate/xml-html/how-tag-handling-works.mdx \
                 docs/translate/xml-html/migrate-tag-handling.mdx \
        --instruction "Keep explanation, extract migration how-to"

    python pipeline/rework.py expand \
        --source docs/translate/text/detect-languages.mdx \
        --instruction "Currently 3 sentences. Expand into proper how-to."

    python pipeline/rework.py retire \
        --source docs/getting-started/authentication.mdx \
        --target docs/getting-started/your-first-api-request.mdx docs/admin/overview.mdx \
        --instruction "Fold how-to into first API request, fold reference into Admin overview"

    python pipeline/rework.py rework \
        --source docs/admin/managing-api-keys.mdx \
        --instruction "Strip reference content, keep how-to walkthrough"

    Common flags:
        --dry-run    Preview what would happen
        --label      Short label for the run directory (e.g. "consolidate-onboarding")
"""

import argparse
import json
import os
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
CLAUDE_MD_PATH = REPO_ROOT / "CLAUDE.md"
DOCS_WRITER_PATH = REPO_ROOT / ".claude" / "agents" / "docs-writer.md"
DIATAXIS_PATH = REPO_ROOT / ".claude" / "agents" / "diataxis.md"
OPENAPI_PATH = REPO_ROOT / "api-reference" / "openapi.yaml"
STANDARDS_PATH = REPO_ROOT / "standards" / "ia.yaml"

MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 16384

TASK_TYPES = ["consolidate", "merge", "split", "expand", "retire", "rework"]


def load_file(path):
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


def canonical_to_draft_name(canonical_path):
    """Convert a canonical path to a draft filename.

    'docs/admin/overview.mdx' -> 'docs--admin--overview.mdx'
    """
    return str(canonical_path).replace("/", "--")


def build_system_prompt():
    claude_md = load_file(CLAUDE_MD_PATH)
    docs_writer = load_file(DOCS_WRITER_PATH)
    diataxis = load_file(DIATAXIS_PATH)
    standards = load_file(STANDARDS_PATH)

    return f"""You are a documentation editor for DeepL's developer documentation.

You rework existing .mdx files for a Mintlify-powered docs site. The docs-writer guidelines
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
- Start with frontmatter (---). Every page MUST have `title` and `description` fields. If the source is missing a description, write one (under 160 chars, specific, not generic).
- Follow the Diataxis type appropriate for the target page.
- Never invent API parameters or behavior not present in the source content or OpenAPI spec.

## Content Preservation

When consolidating, merging, or retiring pages, be SELECTIVE but not destructive:

- Carry over content that is UNIQUE and useful: limits, warnings, behavioral quirks,
  non-obvious constraints, worked examples that teach something. These are the things
  a developer can't find elsewhere.
- Do NOT carry over content that duplicates the OpenAPI spec (parameter lists, response
  schemas, endpoint paths), generic boilerplate ("learn more about X"), or content that
  already exists on another page in the docs.
- Do NOT summarize a detailed page into a one-line stub. If a source has 10 useful
  paragraphs, the target should have those 10 paragraphs (edited for fit), not a sentence
  that says "see the API reference."
- If the target is an openapi: stub page (auto-rendered from the OpenAPI spec), add
  supplementary prose BELOW the frontmatter — context, examples, warnings, and guidance
  that the spec alone cannot convey.
- After writing, mentally check: did you drop any content that a developer would miss?
  If yes, add it back. Did you keep content that's already in the spec or elsewhere?
  If yes, cut it.
"""


def build_rework_prompt(task_type, source_contents, targets, instruction, openapi_context=None, retire_paths=None):
    """Build the user prompt for a rework task.

    Args:
        task_type: One of TASK_TYPES
        source_contents: dict of {path: content} for source files
        targets: list of target output paths
        instruction: User's explicit instruction
        openapi_context: Optional OpenAPI spec excerpt for context
        retire_paths: list of page paths being deleted (avoid linking to these)
    """
    source_block = "\n\n".join(
        f"### Source: {path}\n```mdx\n{content}\n```"
        for path, content in source_contents.items()
    )

    target_block = "\n".join(f"- {t}" for t in targets)

    openapi_block = ""
    if openapi_context:
        openapi_block = f"\n\n## OpenAPI spec (for reference)\n\n```yaml\n{openapi_context}\n```"

    type_guidance = {
        "consolidate": (
            "Consolidate multiple source pages into the target page. "
            "Carry over content that is UNIQUE and useful (limits, warnings, worked examples, "
            "behavioral quirks). Cut content that duplicates the OpenAPI spec or exists "
            "elsewhere. The result should be a focused, high-quality page — not a dump of "
            "everything from every source, but also not a stub that lost all the detail."
        ),
        "merge": (
            "Merge the source pages into a single new page. "
            "Combine the best of both, cut duplication, and produce one coherent page."
        ),
        "split": (
            "Split the source page into multiple target pages. "
            "Each target should serve exactly one Diataxis type. "
            "Don't duplicate content across targets — cross-link instead."
        ),
        "expand": (
            "Expand this thin page into a complete, useful page. "
            "Determine the appropriate Diataxis type from the existing content and title, "
            "then write it properly for that type."
        ),
        "retire": (
            "This page is being retired. Fold its unique, useful content into the target page(s). "
            "Each target absorbs the content relevant to it. Cut anything duplicated by the "
            "OpenAPI spec or other docs pages. The source page will be deleted after promotion."
        ),
        "rework": (
            "Rework this page to improve its quality, focus, and Diataxis compliance. "
            "Follow the instruction for what specifically to change."
        ),
    }

    if len(targets) > 1:
        output_instruction = (
            f"Output each target file separated by a line containing only:\n"
            f"--- SPLIT: <target_path> ---\n\n"
            f"Target files to produce:\n{target_block}\n\n"
            f"For each target, output the FULL file content (not just changes).\n"
            f"Start with:\n--- SPLIT: {targets[0]} ---\n"
            f"Then the full .mdx content for that file.\n"
            f"Then:\n--- SPLIT: {targets[1]} ---\n"
            f"Then the full .mdx content for that file.\n"
            f"And so on for each target."
        )
    else:
        output_instruction = (
            f"Output ONLY the .mdx file content for: {targets[0]}\n"
            f"Start with frontmatter (---)."
        )

    retire_block = ""
    if retire_paths:
        retire_list = "\n".join(f"- {p}" for p in retire_paths)
        retire_block = f"""

## Pages being deleted

These pages will be removed after this task. Do NOT link to them in your output.
If the source content links to any of these, replace with a link to the appropriate
target page or remove the link.

{retire_list}"""

    return f"""{type_guidance[task_type]}

## Instruction

{instruction}

## Source Content

{source_block}
{openapi_block}
{retire_block}

## Output

{output_instruction}"""


def parse_split_output(content, targets):
    """Parse a split/retire output into separate file contents.

    Looks for --- SPLIT: <path> --- markers.
    Returns dict of {path: content}.
    """
    results = {}
    marker_prefix = "--- SPLIT: "
    marker_suffix = " ---"

    parts = content.split(marker_prefix)

    for part in parts[1:]:  # skip anything before first marker
        if marker_suffix not in part:
            continue
        path_end = part.index(marker_suffix)
        path = part[:path_end].strip()
        file_content = part[path_end + len(marker_suffix):].strip()
        results[path] = file_content

    if not results and len(targets) == 1:
        results[targets[0]] = content

    return results


def load_openapi_for_paths(source_paths):
    """Try to extract relevant OpenAPI context based on the docs paths."""
    if not OPENAPI_PATH.exists():
        return None

    with open(OPENAPI_PATH) as f:
        spec = yaml.safe_load(f)

    sections = set()
    for p in source_paths:
        parts = Path(p).parts
        if len(parts) >= 2 and parts[0] == "docs":
            sections.add(parts[1].lower())

    with open(STANDARDS_PATH) as f:
        standards = yaml.safe_load(f)
    overrides = standards.get("product_family_overrides", {})

    relevant_tags = set()
    for family, config in overrides.items():
        if family.lower() in sections:
            relevant_tags.update(config.get("tags", []))

    if not relevant_tags:
        return None

    relevant_paths = {}
    for path, methods in (spec.get("paths") or {}).items():
        for method, details in methods.items():
            if method in ("get", "post", "put", "patch", "delete"):
                endpoint_tags = set(details.get("tags", []))
                if endpoint_tags & relevant_tags:
                    relevant_paths.setdefault(path, {})[method] = details

    if not relevant_paths:
        return None

    return yaml.dump({"paths": relevant_paths}, default_flow_style=False)


def main():
    parser = argparse.ArgumentParser(
        description="Rework existing docs pages (Phase 2 IA cleanup)"
    )
    parser.add_argument(
        "task_type",
        choices=TASK_TYPES,
        help="Type of rework task",
    )
    parser.add_argument(
        "--source",
        nargs="+",
        required=True,
        help="Source page path(s) relative to repo root",
    )
    parser.add_argument(
        "--target",
        nargs="+",
        help="Target output path(s) relative to repo root. Defaults to source path for expand/rework.",
    )
    parser.add_argument(
        "--instruction",
        required=True,
        help="What to do with the content",
    )
    parser.add_argument(
        "--retire",
        nargs="*",
        default=[],
        help="Page paths being retired/deleted (so output avoids linking to them)",
    )
    parser.add_argument(
        "--label",
        help="Short label for the run directory (e.g. 'consolidate-onboarding')",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would happen without calling the API",
    )
    args = parser.parse_args()

    # Validate source files exist
    source_contents = {}
    for src in args.source:
        src_path = REPO_ROOT / src
        if not src_path.exists():
            print(f"Error: source file not found: {src}")
            return 1
        source_contents[src] = load_file(src_path)

    # Resolve targets
    targets = args.target
    if not targets:
        if args.task_type in ("expand", "rework"):
            targets = list(args.source)
        elif args.task_type == "merge":
            print("Error: --target required for merge (where should the merged page go?)")
            return 1
        elif args.task_type == "split":
            print("Error: --target required for split (what files should be produced?)")
            return 1
        elif args.task_type == "consolidate":
            targets = [args.source[0]]
        elif args.task_type == "retire":
            print("Error: --target required for retire (where should content be folded into?)")
            return 1

    # For retire/consolidate targets that are existing files, load them too
    if args.task_type in ("retire", "consolidate"):
        for t in targets:
            t_path = REPO_ROOT / t
            if t_path.exists() and t not in source_contents:
                source_contents[t] = load_file(t_path)

    # For split targets that are also existing files, load them as context
    if args.task_type == "split":
        for t in targets:
            t_path = REPO_ROOT / t
            if t_path.exists() and t not in source_contents:
                source_contents[t] = load_file(t_path)

    # Build run directory
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    label = args.label or args.task_type
    run_id = f"{timestamp}-{label}"
    run_dir = REPO_ROOT / "pipeline" / "drafts" / run_id

    print(f"Task: {args.task_type}")
    print(f"Sources: {', '.join(args.source)}")
    print(f"Targets: {', '.join(targets)}")
    print(f"Run: pipeline/drafts/{run_id}/")
    print(f"Instruction: {args.instruction}")
    print()

    if args.dry_run:
        print("--- DRY RUN ---")
        print(f"Would read {len(source_contents)} source file(s)")
        print(f"Would generate {len(targets)} output file(s):")
        for t in targets:
            draft_name = canonical_to_draft_name(t)
            print(f"  {draft_name} -> {t}")
        print("--- END DRY RUN ---")
        return 0

    # Load OpenAPI context if relevant
    openapi_context = load_openapi_for_paths(args.source + targets)

    # Build prompts
    system_prompt = build_system_prompt()
    user_prompt = build_rework_prompt(
        args.task_type, source_contents, targets, args.instruction, openapi_context,
        retire_paths=args.retire,
    )

    # Call Claude
    print("Calling Claude...")
    client = anthropic.Anthropic()
    with client.messages.stream(
        model=MODEL,
        max_tokens=MAX_TOKENS * len(targets),
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    ) as stream:
        raw_output = stream.get_final_text()

    # Parse output
    if len(targets) > 1:
        file_outputs = parse_split_output(raw_output, targets)
    else:
        file_outputs = {targets[0]: raw_output}

    # Write drafts
    run_dir.mkdir(parents=True, exist_ok=True)

    generated = []
    for target_path, content in file_outputs.items():
        draft_name = canonical_to_draft_name(target_path)
        draft_path = run_dir / draft_name
        draft_path.write_text(content, encoding="utf-8")
        print(f"  Wrote: {draft_name}")
        generated.append({
            "source": args.source,
            "target": target_path,
            "draft": str(draft_path.relative_to(REPO_ROOT)),
            "action": args.task_type,
            "path": target_path,
            "gap": {
                "type": args.task_type,
                "family": Path(target_path).parts[1] if len(Path(target_path).parts) > 1 else "",
                "description": args.instruction,
            },
        })

    missing = [t for t in targets if t not in file_outputs]
    if missing:
        print(f"\n  Warning: no output produced for: {', '.join(missing)}")

    # Write report
    report = {
        "generated": generated,
        "errors": [],
        "run_id": run_id,
        "model": MODEL,
        "task_type": args.task_type,
        "instruction": args.instruction,
        "sources": args.source,
        "targets": targets,
    }
    report_path = run_dir / "report.json"
    report_path.write_text(json.dumps(report, indent=2))
    print(f"\nReport: {report_path.relative_to(REPO_ROOT)}")

    # Retired source pages need special handling at promote time
    if args.task_type in ("retire", "merge"):
        retired = [s for s in args.source if s not in targets]
        if retired:
            retire_path = run_dir / "retire.json"
            retire_path.write_text(json.dumps(retired, indent=2))
            print(f"\nPages to retire (delete after promotion): {', '.join(retired)}")
            print(f"  Saved to: {retire_path.relative_to(REPO_ROOT)}")
            print(f"  Note: promote.py does not auto-delete. Remove these manually after verifying.")

    print(f"\nDone. Next steps:")
    print(f"  python pipeline/evaluate.py --latest --verbose")
    print(f"  python pipeline/review.py --latest")
    print(f"  python pipeline/promote.py --latest --dry-run")

    return 0


if __name__ == "__main__":
    sys.exit(main())
