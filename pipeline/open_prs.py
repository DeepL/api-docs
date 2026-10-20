"""Open-PR awareness: don't re-ship docs that already have a PR waiting.

Every run of the pipeline re-detects gaps from scratch, and a gap stays open until
its PR *merges*. So the next spec change re-detects the same gaps and, without this
module, drafts and ships them again — one open PR per run, all saying the same thing.
This is the memory the pipeline otherwise lacks: it reads the repo's open PRs and
answers "is this gap already in flight?".

Three independent signals, because none alone is enough:

  1. **Gap keys**, from a machine-readable marker `ship.py` writes into the PR body.
     Authoritative: it's the same identity `detect_gaps.py` produced. Required
     because some gap types have no predictable output path — the model picks the
     filename, so two runs of the *same* gap produce two different slugs
     (`query-supported-languages-for-a-resource.mdx` vs
     `...-for-a-deepl-api-resource.mdx`), which path matching alone can't connect.
  2. **File paths**, from each PR's changed files. Catches gaps whose target path
     *is* predictable, and does so for PRs this pipeline didn't open — a human
     writing the same page by hand, or a pipeline PR from before markers existed.
  3. **`covers:` frontmatter**, read from each PR's diff. `missing_group_coverage`
     is detected by asking which endpoint groups no page declares it `covers` —
     so a PR whose diff adds `covers: [<group>]` closes that gap the moment it
     merges. This is signal 1's answer for PRs with no marker: unpredictable
     filename, but the group name is right there in the diff.

All three are best-effort: if `gh` can't be reached we say so and let the caller
proceed rather than block the pipeline on a missing CLI.
"""

import json
import re

from util import run_cmd, check_gh_available


# Exit code shared by generate.py and ship.py: "nothing to do, an open PR already
# covers this". Distinct from 0 (did work) and 1 (failed) so run.py can stop the
# chain cleanly instead of treating it as either success or breakage.
EXIT_NOTHING_TO_DO = 3

MARKER_RE = re.compile(r"<!--\s*docs-pipeline-gaps:\s*(\[.*?\])\s*-->", re.DOTALL)

# Gap types that `covers:` frontmatter actually answers. detect_gaps raises
# missing_group_coverage by asking which groups no page declares it covers, so a
# PR adding that declaration closes exactly this gap — and nothing else. Other
# group-scoped types (a missing API Reference group, say) are about where a page
# sits in the nav, which `covers` says nothing about.
COVERS_GAP_TYPES = {"missing_group_coverage"}

# PR fields we need in one `gh pr list` call — `files` included, so path matching
# costs no extra API round-trips per PR.
PR_JSON_FIELDS = "number,title,url,headRefName,body,files"


# --------------------------------------------------------------------------- #
# Gap identity                                                                 #
# --------------------------------------------------------------------------- #

def gap_key(gap):
    """Stable identity for a gap, independent of when it was detected.

    Built only from what makes a gap *the same gap* — its type and what it's
    about (family / endpoint group / page). Deliberately excludes run IDs,
    timestamps, descriptions and generated filenames, all of which change
    between runs of an unchanged gap.
    """
    gap = gap or {}
    parts = [
        gap.get("type") or "-",
        gap.get("family") or "-",
        gap.get("group") or "-",
        gap.get("path") or "-",
    ]
    return ":".join(
        re.sub(r"\s+", "-", str(p).strip().lower()) or "-" for p in parts
    )


def gap_keys_from_report(report):
    """Gap keys for everything a run's report.json claims to have produced."""
    keys = set()
    for entry in (report or {}).get("generated", []):
        if entry.get("gap"):
            keys.add(gap_key(entry["gap"]))
    return keys


# --------------------------------------------------------------------------- #
# The PR-body marker                                                           #
# --------------------------------------------------------------------------- #

def format_gap_marker(keys):
    """Render gap keys as an HTML comment — invisible in the rendered PR body."""
    return f"<!-- docs-pipeline-gaps: {json.dumps(sorted(keys))} -->"


def parse_gap_marker(body):
    """Read gap keys back out of a PR body. Empty set if there's no marker."""
    keys = set()
    for match in MARKER_RE.finditer(body or ""):
        try:
            parsed = json.loads(match.group(1))
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, list):
            keys.update(str(k) for k in parsed)
    return keys


# --------------------------------------------------------------------------- #
# Reading the open PRs                                                         #
# --------------------------------------------------------------------------- #

def fetch_open_prs(limit=100):
    """Return (prs, error). `prs` is None when the check itself failed.

    None and [] mean different things and callers must treat them differently:
    [] is "nothing in flight, go ahead"; None is "I don't know" and must never
    be read as permission to open a duplicate.
    """
    gh_ok, gh_err = check_gh_available()
    if not gh_ok:
        return None, gh_err

    result = run_cmd(
        ["gh", "pr", "list", "--state", "open", "--limit", str(limit),
         "--json", PR_JSON_FIELDS],
        check=False,
    )
    if result.returncode != 0:
        return None, (result.stderr or "").strip() or "gh pr list failed"

    try:
        prs = json.loads(result.stdout or "[]")
    except json.JSONDecodeError as e:
        return None, f"could not parse gh output: {e}"

    return prs, ""


def pr_label(pr):
    return f"#{pr.get('number', '?')} ({pr.get('headRefName', '?')})"


def covers_claimed_by_open_prs(prs, exclude_branch=None):
    """Return {group_name_lower: pr} for endpoint groups open PRs already cover.

    Reads each PR's diff for added `covers:` frontmatter — the same declaration
    detect_gaps reads off merged pages to decide a group is covered. One `gh pr
    diff` per PR, so this is called only when there's a group gap left to match.
    """
    index = {}
    for pr in prs or []:
        number = pr.get("number")
        if not number or (exclude_branch and pr.get("headRefName") == exclude_branch):
            continue
        # Cheap filter: only PRs that touch docs pages can declare `covers`.
        if not any((f.get("path") or "").endswith(".mdx") for f in pr.get("files") or []):
            continue
        result = run_cmd(["gh", "pr", "diff", str(number)], check=False)
        if result.returncode != 0:
            continue
        for group in _covers_in_diff(result.stdout):
            index.setdefault(group.lower(), pr)
    return index


COVERS_RE = re.compile(r"^\+\s*covers:\s*(.+?)\s*$", re.MULTILINE)


def _covers_in_diff(diff):
    """Group names from added `covers:` frontmatter lines in a unified diff."""
    groups = []
    for raw in COVERS_RE.findall(diff or ""):
        value = raw.strip()
        if value.startswith("[") and value.endswith("]"):
            value = value[1:-1]
        for part in value.split(","):
            name = part.strip().strip("\"'")
            if name:
                groups.append(name)
    return groups


def index_open_prs(prs, exclude_branch=None):
    """Build {gap_key: pr} and {file_path: pr} lookups from open PRs.

    `exclude_branch` skips the PR for the branch we're shipping to, so re-running
    the pipeline onto an existing branch isn't mistaken for a duplicate of itself.
    """
    by_key = {}
    by_path = {}
    for pr in prs or []:
        if exclude_branch and pr.get("headRefName") == exclude_branch:
            continue
        for key in parse_gap_marker(pr.get("body")):
            by_key.setdefault(key, pr)
        for f in pr.get("files") or []:
            path = f.get("path")
            if path:
                by_path.setdefault(path, pr)
    return by_key, by_path


# --------------------------------------------------------------------------- #
# Answering "is this already in flight?"                                       #
# --------------------------------------------------------------------------- #

def split_claimed_gaps(gaps, prs, path_for_gap=None, exclude_branch=None):
    """Split gaps into (todo, claimed).

    `claimed` is a list of (gap, pr, reason) so the caller can print exactly why
    each gap was skipped and which PR to go look at.

    `path_for_gap(gap)` optionally returns the repo-relative path the gap would
    write to; gaps with no predictable path are matched on their key alone.
    """
    by_key, by_path = index_open_prs(prs, exclude_branch=exclude_branch)
    by_covers = None  # built lazily: costs one gh call per PR

    todo, claimed = [], []
    for gap in gaps:
        key = gap_key(gap)
        pr = by_key.get(key)
        if pr:
            claimed.append((gap, pr, f"gap {key} is already in PR {pr_label(pr)}"))
            continue

        path = None
        if path_for_gap:
            try:
                path = path_for_gap(gap)
            except Exception:
                path = None
        # A gap's own `path` (thin_page, missing_description) is the page it edits.
        path = path or gap.get("path")

        pr = by_path.get(path) if path else None
        if pr:
            claimed.append((gap, pr, f"{path} is already changed in PR {pr_label(pr)}"))
            continue

        # Last resort for group gaps: a PR may already add a page declaring it
        # covers this group under a filename we could never have predicted.
        group = gap.get("group")
        if group and gap.get("type") in COVERS_GAP_TYPES:
            if by_covers is None:
                by_covers = covers_claimed_by_open_prs(prs, exclude_branch=exclude_branch)
            pr = by_covers.get(group.lower())
            if pr:
                claimed.append((
                    gap, pr,
                    f"a page covering '{group}' is already in PR {pr_label(pr)}",
                ))
                continue

        todo.append(gap)

    return todo, claimed


def find_duplicate_pr(gap_keys, paths, prs, exclude_branch=None):
    """Decide whether a finished run is a duplicate of something already open.

    Returns (is_duplicate, matches) where `matches` is a list of
    (what, pr, reason) for everything that overlaps an open PR.

    Duplicate only when *every* gap key, or *every* changed page, is already
    claimed. A partial overlap is reported but not blocked: the run carries work
    that no open PR has, and dropping it would silently lose that work.
    """
    by_key, by_path = index_open_prs(prs, exclude_branch=exclude_branch)

    key_matches = [
        (k, by_key[k], f"gap {k} is already in PR {pr_label(by_key[k])}")
        for k in gap_keys if k in by_key
    ]
    path_matches = [
        (p, by_path[p], f"{p} is already changed in PR {pr_label(by_path[p])}")
        for p in paths if p in by_path
    ]

    fully_claimed_keys = bool(gap_keys) and len(key_matches) == len(gap_keys)
    fully_claimed_paths = bool(paths) and len(path_matches) == len(paths)

    return (fully_claimed_keys or fully_claimed_paths), key_matches + path_matches
