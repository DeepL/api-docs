#!/usr/bin/env python3
"""
Detect documentation gaps by cross-referencing three surfaces:

  1. The API Reference   (endpoints, from the OpenAPI spec)
  2. The product tabs     (tutorials / how-tos / overviews, from docs.json)
  3. The Home hub         (cross-cutting content + links to each product)

Structure comes from docs.json (Mintlify's live source of truth for what page
sits in which tab). The one thing docs.json can't tell us — which OpenAPI tags
belong to which product family — comes from standards/ia.yaml. The RULES for what
"complete" means are prose in .claude/agents/docs-ia.md; this script implements the
mechanical, deterministic subset of those rules. Judgment calls (is THIS specific
new endpoint missing a how-to, is a page really the wrong Diataxis type) are left
to the LLM audit — see audit_gaps.py (follow-up).

Deterministic — no AI, no API calls.

Usage:
    python pipeline/detect_gaps.py                     # full audit
    python pipeline/detect_gaps.py --section voice     # one family
    python pipeline/detect_gaps.py --output json       # machine-readable
    python pipeline/detect_gaps.py --force             # report even when files exist
"""

import argparse
import json
import sys
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parent.parent
STANDARDS_PATH = REPO_ROOT / "standards" / "ia.yaml"
OPENAPI_PATH = REPO_ROOT / "api-reference" / "openapi.yaml"
DOCS_JSON_PATH = REPO_ROOT / "docs.json"

# Tab-name matching. Structure is in flux (the doc tab is being split from a single
# "Documentation" tab into per-product tabs), so accept the known aliases.
HOME_TAB_NAMES = {"Home", "Documentation"}
API_REFERENCE_TAB_NAMES = {"API Reference", "API reference"}


# --------------------------------------------------------------------------- #
# Loading                                                                      #
# --------------------------------------------------------------------------- #

def load_yaml(path):
    with open(path) as f:
        return yaml.safe_load(f)


def load_docs_json():
    with open(DOCS_JSON_PATH) as f:
        return json.load(f)


# --------------------------------------------------------------------------- #
# docs.json — the live structure of the site                                   #
# --------------------------------------------------------------------------- #

def _nav_root(docs_json):
    return docs_json.get("navigation", docs_json)


def list_tab_names(docs_json):
    return [t.get("tab", "") for t in _nav_root(docs_json).get("tabs", [])]


def collect_pages_under(docs_json, name):
    """All page paths under the tab OR group whose title == `name`."""
    pages = []

    def rec(node, active):
        if isinstance(node, dict):
            here = node.get("tab") == name or node.get("group") == name
            active = active or here
            for key in ("tabs", "groups", "pages"):
                for child in node.get(key, []):
                    rec(child, active)
        elif isinstance(node, list):
            for child in node:
                rec(child, active)
        elif isinstance(node, str) and active:
            pages.append(node)

    rec(_nav_root(docs_json), False)
    return pages


def group_names_under(docs_json, name):
    """Group titles nested under a tab/group (used to match API Reference groups)."""
    groups = []

    def rec(node, active):
        if isinstance(node, dict):
            here = node.get("tab") == name or node.get("group") == name
            if active and "group" in node:
                groups.append(node["group"])
            active = active or here
            for key in ("tabs", "groups", "pages"):
                for child in node.get(key, []):
                    rec(child, active)
        elif isinstance(node, list):
            for child in node:
                rec(child, active)

    rec(_nav_root(docs_json), False)
    return groups


def first_present(names, present):
    for n in names:
        if n in present:
            return n
    return None


# --------------------------------------------------------------------------- #
# OpenAPI — endpoints and their families                                       #
# --------------------------------------------------------------------------- #

def extract_endpoints(spec):
    endpoints = []
    for path, methods in (spec.get("paths") or {}).items():
        for method, details in (methods or {}).items():
            if method in ("get", "post", "put", "patch", "delete") and isinstance(details, dict):
                endpoints.append({
                    "method": method.upper(),
                    "path": path,
                    "tags": details.get("tags", []),
                    "summary": details.get("summary", ""),
                })
    return endpoints


def endpoints_for_tags(endpoints, tags):
    tags = set(tags)
    return [e for e in endpoints if set(e["tags"]) & tags]


def family_tags(cfg):
    """Union of all endpoint tags across a family's groups."""
    return [t for grp in cfg.get("groups", []) for t in grp.get("tags", [])]


def ungrouped_tags(endpoints, families):
    mapped = {t for cfg in families.values() for t in family_tags(cfg)}
    seen = {t for e in endpoints for t in e["tags"]}
    return seen - mapped


# --------------------------------------------------------------------------- #
# Pages — frontmatter + coarse Diataxis classification                         #
# --------------------------------------------------------------------------- #

def page_frontmatter(page_path):
    """Return (frontmatter_dict, raw_content). (None, None) if the file is missing."""
    for ext in (".mdx", ".md"):
        fp = REPO_ROOT / (page_path + ext)
        if fp.exists():
            try:
                content = fp.read_text(encoding="utf-8")
            except Exception:
                return {}, ""
            if content.startswith("---"):
                end = content.find("---", 3)
                if end != -1:
                    try:
                        return (yaml.safe_load(content[3:end]) or {}), content
                    except yaml.YAMLError:
                        return {}, content
            return {}, content
    return None, None  # page listed in nav but file missing


def slug(page_path):
    return page_path.rsplit("/", 1)[-1].lower()


# Coarse role detection. Precise Diataxis typing is the LLM audit's job; here we
# only need "does this tab have AN overview / A tutorial / A how-to at all".
def is_overview(page_path, fm):
    s = slug(page_path)
    t = (fm or {}).get("type", "")
    st = str((fm or {}).get("sidebarTitle", "")).lower()
    return (
        t in ("overview", "explanation")
        or s in ("overview", "intro", "introduction", "index")
        or st == "overview"
    )


def is_tutorial(page_path, fm):
    s = slug(page_path)
    if (fm or {}).get("type") == "tutorial":
        return True
    return any(k in s for k in ("tutorial", "quickstart", "beginners-guide", "beginner", "get-started", "first"))


def is_howto(page_path, fm):
    s = slug(page_path)
    if (fm or {}).get("type") in ("how-to", "howto"):
        return True
    padded = f"-{s}-"
    return any(s.startswith(v) or f"-{v}-" in padded for v in
               ("how-to", "use", "handle", "set-up", "setup", "configure", "migrate", "solve", "control", "manage", "enable"))


def is_openapi_page(fm):
    return bool(fm) and ("openapi" in fm)


# --------------------------------------------------------------------------- #
# Gap detection                                                                #
# --------------------------------------------------------------------------- #

def gap(gap_type, severity, family, path=None, desc="", group=None):
    g = {"type": gap_type, "severity": severity, "description": desc}
    if family:
        g["family"] = family
    if group:
        g["group"] = group
    if path:
        g["path"] = path
    return g


def covered_group_names(docs_json, apiref_tab):
    """Endpoint-group names declared covered by any guide (`covers` frontmatter)."""
    covered = set()
    for p in all_doc_pages(docs_json, apiref_tab):
        fm, _ = page_frontmatter(p)
        if not fm:
            continue
        cov = fm.get("covers")
        if isinstance(cov, str):
            covered.add(cov)
        elif isinstance(cov, list):
            covered.update(cov)
    return covered


def detect_gaps(docs_json, endpoints, families, section=None, force=False):
    gaps = []
    tab_names = set(list_tab_names(docs_json))
    home_tab = first_present(HOME_TAB_NAMES, tab_names)
    apiref_tab = first_present(API_REFERENCE_TAB_NAMES, tab_names)

    home_pages = collect_pages_under(docs_json, home_tab) if home_tab else []
    apiref_pages = collect_pages_under(docs_json, apiref_tab) if apiref_tab else []
    apiref_groups = set(group_names_under(docs_json, apiref_tab)) if apiref_tab else set()

    covered = covered_group_names(docs_json, apiref_tab)

    # --- Per-family, cross-surface checks --------------------------------- #
    for family, cfg in families.items():
        if section and family.lower() != section.lower():
            continue

        groups = cfg.get("groups", [])
        eps = endpoints_for_tags(endpoints, family_tags(cfg))
        home = cfg.get("narrative_home", "unplaced")

        # API Reference: each group with endpoints needs a matching group in the ref tab.
        for grp in groups:
            gname = grp.get("name", "")
            if apiref_tab and gname not in apiref_groups and endpoints_for_tags(endpoints, grp.get("tags", [])):
                gaps.append(gap("missing_api_reference_group", "high", family, group=gname,
                                desc=f"'{gname}' has endpoints but no matching group in the API Reference tab"))

        if home == "reference_only":
            if eps:
                gaps.append(gap("reference_only_no_guide", "low", family,
                                desc=f"{family} is reference-only; consider adding a guide (expected once it leaves alpha)"))
            continue

        if home in ("unplaced", None):
            if eps:
                gaps.append(gap("narrative_home_unplaced", "high", family,
                                desc=f"{family} has {len(eps)} endpoints but no decided narrative home — a human must choose own / a parent tab / reference_only"))
            continue

        # Per-group guide coverage: each endpoint group needs at least one guide
        # (tutorial OR how-to) declaring it via `covers`. Sections have many guides;
        # this is the real bar, not "has one tutorial". Applies wherever the family's
        # guides live (own tab or nested), since `covers` is location-independent.
        for grp in groups:
            gname = grp.get("name", "")
            if gname not in covered and endpoints_for_tags(endpoints, grp.get("tags", [])):
                gaps.append(gap("missing_group_coverage", "high", family, group=gname,
                                desc=f"No guide (tutorial or how-to) covers the '{gname}' endpoints"))

        if home != "own":
            continue  # nested under another tab: overview/hub are the parent's concern

        # own tab: overview page + a Home hub link.
        tab_pages = collect_pages_under(docs_json, family)
        if eps and not tab_pages:
            gaps.append(gap("missing_product_tab", "high", family,
                            desc=f"{family} has {len(eps)} endpoints but no '{family}' product tab"))
            continue

        present = [(p, page_frontmatter(p)[0]) for p in tab_pages]
        if force or not any(is_overview(p, fm) for p, fm in present):
            gaps.append(gap("missing_overview", "high", family,
                            desc=f"{family} tab has no overview/landing page"))

        if home_tab and not any(family.lower() in p.lower() for p in home_pages):
            gaps.append(gap("missing_hub_entry", "medium", family,
                            desc=f"Home hub has no page/link surfacing the {family} product"))

    # --- API Reference must be reference-only ----------------------------- #
    if apiref_tab and not section:
        for p in apiref_pages:
            fm, _ = page_frontmatter(p)
            if fm is None:
                continue  # file missing; separate concern
            if not is_openapi_page(fm):
                gaps.append(gap("apiref_narrative_page", "medium", None, path=p,
                                desc=f"{p} sits in the API Reference tab but is not an endpoint page (narrative belongs in a product tab or Home)"))

    # --- Ungrouped OpenAPI tags ------------------------------------------- #
    if not section:
        for tag in sorted(ungrouped_tags(endpoints, families)):
            gaps.append(gap("ungrouped_tag", "high", None,
                            desc=f"OpenAPI tag '{tag}' is not mapped to a family in standards/ia.yaml — a human must place it"))

    # --- Doc-quality checks on non-reference pages ------------------------ #
    if not section:
        for p in all_doc_pages(docs_json, apiref_tab):
            fm, content = page_frontmatter(p)
            if fm is None:
                continue
            if not fm.get("description"):
                gaps.append(gap("missing_description", "low", None, path=p,
                                desc=f"{p} has no frontmatter description"))
            if len(strip_frontmatter(content).split()) < 100:
                gaps.append(gap("thin_page", "medium", None, path=p,
                                desc=f"{p} has under 100 words"))

    return gaps


def all_doc_pages(docs_json, apiref_tab):
    """Every page path in the nav except those under the API Reference tab."""
    ref = set(collect_pages_under(docs_json, apiref_tab)) if apiref_tab else set()
    everything = set()

    def rec(node):
        if isinstance(node, dict):
            for key in ("tabs", "groups", "pages"):
                for child in node.get(key, []):
                    rec(child)
        elif isinstance(node, list):
            for child in node:
                rec(child)
        elif isinstance(node, str):
            everything.add(node)

    rec(_nav_root(docs_json))
    return sorted(everything - ref)


def strip_frontmatter(content):
    if content and content.startswith("---"):
        end = content.find("---", 3)
        if end != -1:
            return content[end + 3:]
    return content or ""


# --------------------------------------------------------------------------- #
# Reporting                                                                    #
# --------------------------------------------------------------------------- #

def group_key(g):
    if "family" in g:
        return g["family"]
    path = g.get("path", "")
    parts = path.split("/")
    return parts[1].replace("-", " ").title() if len(parts) >= 2 else "Site-wide"


def format_report(gaps, output_format="text"):
    if output_format == "json":
        return json.dumps({"gaps": gaps, "total": len(gaps)}, indent=2)

    lines = ["Documentation Gap Report", "=" * 50, "", f"Total gaps: {len(gaps)}"]
    by_sev = {"high": [], "medium": [], "low": []}
    for g in gaps:
        by_sev.setdefault(g.get("severity", "low"), []).append(g)

    for sev in ("high", "medium", "low"):
        items = by_sev.get(sev) or []
        if not items:
            continue
        lines += ["", f"[{sev.upper()}] ({len(items)} issues)", "=" * 50]
        grouped = {}
        for g in items:
            grouped.setdefault(group_key(g), []).append(g)
        for name in sorted(grouped):
            lines += ["", f"  [{name}]"]
            for g in grouped[name]:
                lines.append(f"    {g['type']}: {g['description']}")
    lines.append("")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Detect documentation gaps")
    parser.add_argument("--section", help="Audit only this product family")
    parser.add_argument("--output", choices=["text", "json"], default="text")
    parser.add_argument("--force", action="store_true", help="Report requirement gaps even when satisfied (for regeneration)")
    args = parser.parse_args()

    families = load_yaml(STANDARDS_PATH).get("families", {})
    spec = load_yaml(OPENAPI_PATH)
    docs_json = load_docs_json()
    endpoints = extract_endpoints(spec)

    gaps = detect_gaps(docs_json, endpoints, families, section=args.section, force=args.force)
    print(format_report(gaps, args.output))
    return 1 if gaps else 0


if __name__ == "__main__":
    sys.exit(main())
