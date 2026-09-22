#!/usr/bin/env python3
"""Tests for the open-PR duplicate check.

    python pipeline/test_open_prs.py

No gh calls and no network: every test hands in the PR data `fetch_open_prs` would
have returned, and `run_cmd` is stubbed so a stray subprocess fails the test rather
than reaching GitHub.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import open_prs  # noqa: E402
from open_prs import (  # noqa: E402
    find_duplicate_pr,
    format_gap_marker,
    gap_key,
    gap_keys_from_report,
    index_open_prs,
    parse_gap_marker,
    split_claimed_gaps,
    _covers_in_diff,
)


# PR number -> the diff `gh pr diff` should return. Empty means "no covers here".
DIFFS = {}


class _FakeResult:
    def __init__(self, returncode, stdout):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = ""


def _fake_run_cmd(cmd, check=True, **kwargs):
    """Stand in for gh. Anything but a `pr diff` lookup is a bug in the code."""
    assert cmd[:3] == ["gh", "pr", "diff"], f"unexpected subprocess call: {cmd}"
    return _FakeResult(0, DIFFS.get(int(cmd[3]), ""))


def setUpModule():
    open_prs.run_cmd = _fake_run_cmd


def tearDownModule():
    DIFFS.clear()


def pr(number, branch="docs/pipeline-x", body="", files=()):
    return {
        "number": number,
        "headRefName": branch,
        "body": body,
        "files": [{"path": f} for f in files],
    }


class GapKeyTest(unittest.TestCase):
    def test_same_gap_two_runs_has_one_key(self):
        """The wording of `description` changes between runs; identity must not."""
        a = {"type": "missing_group_coverage", "family": "Voice", "group": "Voice Jobs",
             "severity": "high", "description": "No guide covers the Voice Jobs endpoints"}
        b = dict(a, description="reworded", severity="medium")
        self.assertEqual(gap_key(a), gap_key(b))

    def test_different_groups_differ(self):
        base = {"type": "missing_group_coverage", "family": "Voice"}
        self.assertNotEqual(
            gap_key(dict(base, group="Voice Jobs")),
            gap_key(dict(base, group="Translate Audio Files")),
        )

    def test_page_scoped_gaps_differ_by_page(self):
        base = {"type": "thin_page"}
        self.assertNotEqual(
            gap_key(dict(base, path="docs/a.mdx")),
            gap_key(dict(base, path="docs/b.mdx")),
        )

    def test_missing_pieces_do_not_collide_with_empty(self):
        self.assertEqual(gap_key({}), "-:-:-:-")


class MarkerTest(unittest.TestCase):
    def test_roundtrip_through_a_pr_body(self):
        keys = {"missing_group_coverage:voice:voice-jobs:-", "thin_page:-:-:docs/a.mdx"}
        body = "## Summary\nGenerated pages.\n\n---\n" + format_gap_marker(keys)
        self.assertEqual(parse_gap_marker(body), keys)

    def test_missing_or_malformed_marker_is_empty(self):
        for body in (None, "", "no marker", "<!-- docs-pipeline-gaps: not json -->"):
            self.assertEqual(parse_gap_marker(body), set())

    def test_keys_come_from_the_run_report(self):
        report = {"generated": [
            {"path": "docs/a.mdx", "gap": {"type": "thin_page", "path": "docs/a.mdx"}},
            {"path": "docs/b.mdx"},  # no gap recorded
        ]}
        self.assertEqual(gap_keys_from_report(report), {"thin_page:-:-:docs/a.mdx"})


class SplitClaimedGapsTest(unittest.TestCase):
    def setUp(self):
        self.gap = {"type": "missing_group_coverage", "family": "Voice", "group": "Voice Jobs"}

    def test_marker_claims_a_gap_whose_filename_is_unpredictable(self):
        open_pr = pr(447, body=format_gap_marker({gap_key(self.gap)}),
                     files=["docs/voice/some-slug-we-never-predicted.mdx"])
        todo, claimed = split_claimed_gaps([self.gap], [open_pr])
        self.assertEqual(todo, [])
        self.assertEqual(claimed[0][1]["number"], 447)

    def test_path_claims_a_gap_with_a_predictable_target(self):
        gap = {"type": "thin_page", "path": "docs/a.mdx"}
        todo, claimed = split_claimed_gaps([gap], [pr(1, files=["docs/a.mdx"])])
        self.assertEqual((todo, len(claimed)), ([], 1))

    def test_unclaimed_gap_survives(self):
        todo, claimed = split_claimed_gaps([self.gap], [pr(1, files=["docs/other.mdx"])])
        self.assertEqual((todo, claimed), ([self.gap], []))

    def test_no_open_prs_claims_nothing(self):
        todo, claimed = split_claimed_gaps([self.gap], [])
        self.assertEqual((todo, claimed), ([self.gap], []))


class FindDuplicatePrTest(unittest.TestCase):
    def test_all_keys_claimed_is_a_duplicate(self):
        keys = {"missing_group_coverage:voice:voice-jobs:-"}
        open_pr = pr(447, body=format_gap_marker(keys))
        # Different filename this run, same gap: the whole point of gap keys.
        is_dup, matches = find_duplicate_pr(keys, ["docs/voice/different-slug.mdx"], [open_pr])
        self.assertTrue(is_dup)
        self.assertTrue(matches)

    def test_all_paths_claimed_is_a_duplicate(self):
        is_dup, _ = find_duplicate_pr(set(), ["docs/a.mdx"], [pr(1, files=["docs/a.mdx"])])
        self.assertTrue(is_dup)

    def test_partial_overlap_still_ships(self):
        """A run carrying work no open PR has must not be dropped."""
        keys = {"a:-:-:-", "b:-:-:-"}
        open_pr = pr(1, body=format_gap_marker({"a:-:-:-"}), files=["docs/a.mdx"])
        is_dup, matches = find_duplicate_pr(keys, ["docs/a.mdx", "docs/b.mdx"], [open_pr])
        self.assertFalse(is_dup)
        self.assertEqual(len(matches), 2)  # reported, not blocked

    def test_nothing_to_compare_is_not_a_duplicate(self):
        is_dup, _ = find_duplicate_pr(set(), [], [pr(1, files=["docs/a.mdx"])])
        self.assertFalse(is_dup)

    def test_own_branch_is_not_its_own_duplicate(self):
        keys = {"a:-:-:-"}
        mine = pr(9, branch="docs/pipeline-mine", body=format_gap_marker(keys),
                  files=["docs/a.mdx"])
        is_dup, _ = find_duplicate_pr(keys, ["docs/a.mdx"], [mine],
                                      exclude_branch="docs/pipeline-mine")
        self.assertFalse(is_dup)

    def test_first_pr_wins_when_two_claim_the_same_thing(self):
        body = format_gap_marker({"a:-:-:-"})
        by_key, _ = index_open_prs([pr(446, body=body), pr(447, body=body)])
        self.assertEqual(by_key["a:-:-:-"]["number"], 446)


class CoversClaimTest(unittest.TestCase):
    """The fallback for PRs with no marker: read `covers:` out of the diff."""

    def setUp(self):
        DIFFS.clear()
        self.gap = {"type": "missing_group_coverage", "family": "Voice", "group": "Voice Jobs"}

    def test_covers_in_an_open_diff_claims_the_group_gap(self):
        DIFFS[447] = "+++ b/docs/voice/slug.mdx\n+covers: [Voice Jobs]\n"
        open_pr = pr(447, files=["docs/voice/a-slug-we-never-predicted.mdx"])
        todo, claimed = split_claimed_gaps([self.gap], [open_pr])
        self.assertEqual(todo, [])
        self.assertIn("covering 'Voice Jobs'", claimed[0][2])

    def test_a_different_group_does_not_claim_it(self):
        DIFFS[447] = "+covers: [Languages]\n"
        todo, claimed = split_claimed_gaps([self.gap], [pr(447, files=["docs/x.mdx"])])
        self.assertEqual((todo, claimed), ([self.gap], []))

    def test_group_name_case_and_spacing_still_match(self):
        DIFFS[447] = "+covers:  voice jobs \n"
        todo, _ = split_claimed_gaps([self.gap], [pr(447, files=["docs/x.mdx"])])
        self.assertEqual(todo, [])

    def test_prs_touching_no_mdx_are_not_diffed(self):
        """The cheap filter: a spec-only PR can't declare `covers`."""
        todo, claimed = split_claimed_gaps(
            [self.gap], [pr(447, files=["api-reference/openapi.yaml", "docs.json"])]
        )
        self.assertEqual((todo, claimed), ([self.gap], []))


class CoversInDiffTest(unittest.TestCase):
    def test_reads_added_covers_lines_only(self):
        diff = (
            "+++ b/docs/voice/x.mdx\n"
            "+covers: [Translate Audio Files, Languages]\n"
            "-covers: [Removed Group]\n"
            " covers: [Context Line]\n"
            "+covers: Voice Jobs\n"
        )
        self.assertEqual(
            _covers_in_diff(diff),
            ["Translate Audio Files", "Languages", "Voice Jobs"],
        )

    def test_quoted_and_empty_values(self):
        self.assertEqual(_covers_in_diff('+covers: ["Voice Jobs"]\n'), ["Voice Jobs"])
        self.assertEqual(_covers_in_diff("+covers: []\n"), [])
        self.assertEqual(_covers_in_diff(""), [])

    def test_covers_only_claims_the_gap_type_it_answers(self):
        """`covers` says a guide exists, not that the nav group does."""
        gap = {"type": "missing_api_reference_group", "family": "Voice", "group": "Voice Jobs"}
        todo, claimed = split_claimed_gaps([gap], [pr(1, files=["docs/voice/x.mdx"])])
        self.assertEqual((todo, claimed), ([gap], []))  # no gh diff call either


if __name__ == "__main__":
    unittest.main(verbosity=2)
