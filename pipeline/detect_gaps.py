#!/usr/bin/env python3
"""
Detect documentation gaps by comparing existing docs against IA standards.

Deterministic script — no AI. Reads the OpenAPI spec, scans existing docs,
compares against standards/ia.yaml, and outputs a structured gap report.

Usage:
    python pipeline/detect_gaps.py                    # full audit
    python pipeline/detect_gaps.py --section translate # audit one section
    python pipeline/detect_gaps.py --output json       # machine-readable output
"""

import argparse
import json
import sys
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parent.parent
STANDARDS_PATH = REPO_ROOT / "standards" / "ia.yaml"
OPENAPI_PATH = REPO_ROOT / "api-reference" / "openapi.yaml"
DOCS_DIR = REPO_ROOT / "docs"
API_REF_DIR = REPO_ROOT / "api-reference"


def load_standards():
    with open(STANDARDS_PATH) as f:
        return yaml.safe_load(f)


def load_openapi():
    with open(OPENAPI_PATH) as f:
        return yaml.safe_load(f)


def derive_product_families(spec, standards):
    """
    Auto-derive product families from OpenAPI tags, applying overrides
    from ia.yaml. Returns {family_name: {tags: [...], endpoints: [...]}}.
    """
    overrides = standards.get("product_family_overrides", {})

    tag_to_family = {}
    for family_name, config in overrides.items():
        for tag in config.get("tags", []):
            tag_to_family[tag] = family_name

    endpoints = extract_endpoints(spec)

    families = {}
    ungrouped_tags = set()

    for ep in endpoints:
        for tag in ep.get("tags", []):
            family = tag_to_family.get(tag)
            if not family:
                ungrouped_tags.add(tag)
                family = tag
            families.setdefault(family, {"tags": set(), "endpoints": []})
            families[family]["tags"].add(tag)
            families[family]["endpoints"].append(ep)

    for name in families:
        families[name]["tags"] = sorted(families[name]["tags"])

    return families, ungrouped_tags


def extract_endpoints(spec):
    endpoints = []
    for path, methods in (spec.get("paths") or {}).items():
        for method, details in methods.items():
            if method in ("get", "post", "put", "patch", "delete"):
                endpoints.append({
                    "method": method.upper(),
                    "path": path,
                    "summary": details.get("summary", ""),
                    "tags": details.get("tags", []),
                    "operation_id": details.get("operationId", ""),
                })
    return endpoints


def find_existing_docs():
    docs = {}
    for dirpath in [DOCS_DIR, API_REF_DIR]:
        if not dirpath.exists():
            continue
        for mdx in dirpath.rglob("*.mdx"):
            rel = mdx.relative_to(REPO_ROOT)
            frontmatter = extract_frontmatter(mdx)
            docs[str(rel.with_suffix(""))] = {
                "path": str(rel),
                "frontmatter": frontmatter,
                "has_code_examples": has_code_examples(mdx),
                "word_count": count_words(mdx),
            }
    return docs


def extract_frontmatter(path):
    try:
        content = path.read_text(encoding="utf-8")
    except Exception:
        return {}
    if not content.startswith("---"):
        return {}
    end = content.find("---", 3)
    if end == -1:
        return {}
    try:
        return yaml.safe_load(content[3:end]) or {}
    except yaml.YAMLError:
        return {}


def has_code_examples(path):
    try:
        content = path.read_text(encoding="utf-8")
    except Exception:
        return False
    return "```" in content


def count_words(path):
    try:
        content = path.read_text(encoding="utf-8")
    except Exception:
        return 0
    if content.startswith("---"):
        end = content.find("---", 3)
        if end != -1:
            content = content[end + 3:]
    return len(content.split())




FAMILY_TO_DOCS_DIRS = {
    "Translate": [
        "docs/learning-how-tos/examples-and-guides/translation",
        "docs/learning-how-tos/examples-and-guides/how-to-use-context",
        "docs/learning-how-tos/examples-and-guides/placeholder",
        "docs/learning-how-tos/examples-and-guides/translating-between",
        "docs/learning-how-tos/examples-and-guides/customizations-for-variants",
        "docs/xml-and-html-handling",
        "docs/best-practices/document-translations",
        "docs/best-practices/language-detection",
        "docs/translate",
    ],
    "Customize": [
        "docs/learning-how-tos/examples-and-guides/glossaries",
        "docs/best-practices/custom-instructions",
        "docs/learning-how-tos/examples-and-guides/how-to-use-translation-memories",
        "docs/customize",
    ],
    "Voice": ["docs/voice"],
    "Write": ["docs/write"],
    "Admin": [
        "docs/getting-started/managing-api-keys",
        "docs/retrieving-usage-data",
        "docs/admin",
    ],
    "Languages": [
        "docs/getting-started/supported-languages",
        "docs/resources/language-release-process",
        "docs/languages",
    ],
}


def find_docs_for_family(family_name, existing_docs):
    prefixes = FAMILY_TO_DOCS_DIRS.get(family_name, [f"docs/{family_name.lower()}"])
    matches = []
    for doc_key, doc in existing_docs.items():
        for prefix in prefixes:
            if doc_key.startswith(prefix) or doc["path"].startswith(prefix):
                matches.append(doc)
                break
    return matches


def detect_gaps(families, standards, existing_docs, section_filter=None):
    gaps = []

    for family_name, family in families.items():
        if section_filter and family_name.lower() != section_filter.lower():
            continue

        family_docs = find_docs_for_family(family_name, existing_docs)
        endpoint_count = len(family.get("endpoints", []))

        # Check: does this product family have ANY docs-tab pages?
        if not family_docs:
            gaps.append({
                "type": "undocumented_product",
                "severity": "high",
                "family": family_name,
                "endpoint_count": endpoint_count,
                "description": f"{family_name} has {endpoint_count} endpoints but no documentation pages",
            })
        else:
            # Check: has orientation page?
            has_orientation = any(
                "overview" in d["path"].lower() or "intro" in d["path"].lower()
                for d in family_docs
            )
            if not has_orientation:
                gaps.append({
                    "type": "missing_orientation",
                    "severity": "high",
                    "family": family_name,
                    "description": f"{family_name} section has no orientation/overview page",
                })

            # Check: has at least one tutorial?
            has_tutorial = any(
                d.get("frontmatter", {}).get("type") == "tutorial"
                or "beginner" in d["path"].lower()
                or "quickstart" in d["path"].lower()
                or "first" in d["path"].lower()
                for d in family_docs
            )
            if not has_tutorial:
                gaps.append({
                    "type": "missing_tutorial",
                    "severity": "high",
                    "family": family_name,
                    "description": f"{family_name} section has no tutorial",
                })

        # Code samples are tracked in the samples repo, not here.

    # Check docs-tab pages for quality issues (independent of product families)
    for doc_key, doc in existing_docs.items():
        if doc_key.startswith("api-reference/"):
            continue

        if not doc["has_code_examples"]:
            path = doc["path"]
            if "cookbook" in path or "how-to" in path or "guide" in path:
                gaps.append({
                    "type": "missing_code_examples",
                    "severity": "medium",
                    "path": path,
                    "description": f"{path} appears to be a guide but has no code examples",
                })

        if doc["word_count"] < 100:
            gaps.append({
                "type": "thin_page",
                "severity": "medium",
                "path": doc["path"],
                "word_count": doc["word_count"],
                "description": f"{doc['path']} has only {doc['word_count']} words",
            })

        fm = doc.get("frontmatter", {})
        if not fm.get("description"):
            gaps.append({
                "type": "missing_description",
                "severity": "low",
                "path": doc["path"],
                "description": f"{doc['path']} has no frontmatter description",
            })

    return gaps


def get_gap_group(gap):
    """Get the grouping key for a gap (product family or page path's section)."""
    if "family" in gap:
        return gap["family"]
    path = gap.get("path", "")
    parts = path.split("/")
    if len(parts) >= 2:
        return parts[1].replace("-", " ").title()
    return "Other"


def format_report(gaps, ungrouped_tags, output_format="text"):
    if output_format == "json":
        return json.dumps({
            "gaps": gaps,
            "total": len(gaps),
            "ungrouped_tags": sorted(ungrouped_tags),
        }, indent=2)

    lines = []
    lines.append("Documentation Gap Report")
    lines.append("=" * 50)

    if ungrouped_tags:
        lines.append("")
        lines.append("[WARNING] Ungrouped OpenAPI tags (need product family assignment):")
        for tag in sorted(ungrouped_tags):
            lines.append(f"  - {tag}")

    lines.append("")
    lines.append(f"Total gaps: {len(gaps)}")

    by_severity = {"high": [], "medium": [], "low": []}
    for g in gaps:
        by_severity.get(g.get("severity", "low"), by_severity["low"]).append(g)

    for severity in ["high", "medium", "low"]:
        items = by_severity[severity]
        if not items:
            continue

        lines.append("")
        lines.append(f"[{severity.upper()}] ({len(items)} issues)")
        lines.append("=" * 50)

        grouped = {}
        for g in items:
            key = get_gap_group(g)
            grouped.setdefault(key, []).append(g)

        for group_name in sorted(grouped):
            group_items = grouped[group_name]
            lines.append("")
            lines.append(f"  [{group_name}]")
            for g in group_items:
                lines.append(f"    {g['type']}: {g['description']}")

    lines.append("")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Detect documentation gaps")
    parser.add_argument("--section", help="Audit only this product family")
    parser.add_argument("--output", choices=["text", "json"], default="text")
    args = parser.parse_args()

    standards = load_standards()
    spec = load_openapi()
    existing_docs = find_existing_docs()
    families, ungrouped_tags = derive_product_families(spec, standards)
    gaps = detect_gaps(families, standards, existing_docs, args.section)

    print(format_report(gaps, ungrouped_tags, args.output))
    return 1 if gaps else 0


if __name__ == "__main__":
    sys.exit(main())
