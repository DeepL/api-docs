#!/usr/bin/env python3
"""Tests for turning a docs.json nav entry into a file path.

    python pipeline/test_gap_paths.py

A nav entry ("docs/resources/breaking-changes-change-notices") has no extension,
and may share its name with the directory holding its child pages. Treating one as
a file path produced three failures at once: a crash on the directory, an empty
"current content" that turned an expand into a rewrite-from-scratch, and an
extensionless draft that promote.py silently dropped. These pin all three down.

Runs against a temp docs tree, so no repo file is read and none is written.
"""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import detect_gaps  # noqa: E402
import generate  # noqa: E402


class TempDocsTree(unittest.TestCase):
    """Points both modules at a scratch tree laid out like the real repo."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        # DOCS_DIR is bound at import time, so redirect it alongside the roots.
        self._saved = (detect_gaps.REPO_ROOT, generate.REPO_ROOT, generate.DOCS_DIR)
        detect_gaps.REPO_ROOT = self.root
        generate.REPO_ROOT = self.root
        generate.DOCS_DIR = self.root / "docs"
        self.addCleanup(self._restore)

    def _restore(self):
        detect_gaps.REPO_ROOT, generate.REPO_ROOT, generate.DOCS_DIR = self._saved
        self._tmp.cleanup()

    def write(self, rel, text="---\ntitle: T\n---\n\nSome body copy.\n"):
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path


class PageFileTest(TempDocsTree):
    def test_resolves_the_mdx_behind_a_nav_entry(self):
        self.write("docs/a/b.mdx")
        self.assertEqual(detect_gaps.page_file("docs/a/b"), self.root / "docs/a/b.mdx")

    def test_falls_back_to_md(self):
        self.write("docs/a/b.md")
        self.assertEqual(detect_gaps.page_file("docs/a/b"), self.root / "docs/a/b.md")

    def test_a_directory_of_the_same_name_is_not_the_page(self):
        """The [Errno 21] regression: page and child-page folder share a name."""
        (self.root / "docs/resources/notices").mkdir(parents=True)
        self.write("docs/resources/notices/july-2024.mdx")
        self.assertIsNone(detect_gaps.page_file("docs/resources/notices"))

        # With the page's own file present, that file is what resolves.
        self.write("docs/resources/notices.mdx")
        self.assertEqual(
            detect_gaps.page_file("docs/resources/notices"),
            self.root / "docs/resources/notices.mdx",
        )

    def test_nothing_backing_the_entry(self):
        self.assertIsNone(detect_gaps.page_file("docs/a/ghost"))
        self.assertIsNone(detect_gaps.page_file(""))


class HasChildPagesTest(unittest.TestCase):
    def setUp(self):
        self.pages = [
            "docs/resources/notices",
            "docs/resources/notices/july-2024",
            "docs/resources/notices-and-more",
            "docs/a/leaf",
        ]

    def test_a_page_with_children_is_a_parent(self):
        self.assertTrue(detect_gaps.has_child_pages(self.pages, "docs/resources/notices"))

    def test_a_leaf_is_not(self):
        self.assertFalse(detect_gaps.has_child_pages(self.pages, "docs/a/leaf"))

    def test_a_name_prefix_is_not_a_child(self):
        """'notices-and-more' must not count as a child of 'notices'."""
        self.assertFalse(
            detect_gaps.has_child_pages(["docs/x", "docs/x-ray"], "docs/x")
        )


class ThinPageDetectionTest(TempDocsTree):
    """Hub pages are short by design; padding them out is the wrong fix."""

    def _gaps(self):
        docs_json = {"navigation": {"tabs": [
            {"tab": "Home", "pages": ["docs/hub", "docs/hub/child", "docs/lonely"]},
        ]}}
        return detect_gaps.detect_gaps(docs_json, [], {})

    def test_parent_page_is_not_flagged_but_a_real_thin_page_is(self):
        short = '---\ntitle: T\ndescription: d\n---\n\nToo short.\n'
        self.write("docs/hub.mdx", short)
        self.write("docs/hub/child.mdx", short)
        self.write("docs/lonely.mdx", short)

        thin = [g["path"] for g in self._gaps() if g["type"] == "thin_page"]
        self.assertNotIn("docs/hub", thin)
        self.assertIn("docs/lonely", thin)
        self.assertIn("docs/hub/child", thin)  # a child can still be thin


class OutputPathTest(TempDocsTree):
    def test_page_edits_keep_the_extension(self):
        """promote.py only collects *.mdx drafts, so losing it loses the page."""
        self.write("docs/a/b.mdx")
        for gap_type in ("thin_page", "missing_code_examples", "missing_description"):
            out = generate.determine_output_path({"type": gap_type, "path": "docs/a/b"}, "unknown")
            self.assertEqual(out, self.root / "docs/a/b.mdx", gap_type)

    def test_unbacked_entry_yields_no_path(self):
        out = generate.determine_output_path({"type": "thin_page", "path": "docs/a/ghost"}, "unknown")
        self.assertIsNone(out)

    def test_new_pages_are_unaffected(self):
        out = generate.determine_output_path({"type": "missing_tutorial"}, "Voice")
        self.assertEqual(out, self.root / "docs/voice/tutorial.mdx")


class LoadExistingPageTest(TempDocsTree):
    def test_reads_the_resolved_file(self):
        self.write("docs/a/b.mdx", "---\ntitle: T\n---\n\nReal content.\n")
        self.assertIn("Real content.", generate.load_existing_page({"path": "docs/a/b"}))

    def test_unbacked_entry_raises_instead_of_returning_nothing(self):
        """An empty read used to become "write this page from scratch"."""
        with self.assertRaises(FileNotFoundError):
            generate.load_existing_page({"path": "docs/a/ghost"})

    def test_directory_collision_raises_rather_than_crashing_on_the_directory(self):
        (self.root / "docs/a/b").mkdir(parents=True)
        self.write("docs/a/b/child.mdx")
        with self.assertRaises(FileNotFoundError):  # not IsADirectoryError
            generate.load_existing_page({"path": "docs/a/b"})

    def test_empty_page_raises(self):
        self.write("docs/a/blank.mdx", "   \n")
        with self.assertRaises(ValueError):
            generate.load_existing_page({"path": "docs/a/blank"})


class ApplyDescriptionTest(TempDocsTree):
    def test_writes_into_the_resolved_file(self):
        self.write("docs/a/b.mdx", "---\ntitle: T\n---\n\nBody.\n")
        self.assertTrue(generate.apply_description({"path": "docs/a/b"}, "A description."))
        self.assertIn('description: "A description."',
                      (self.root / "docs/a/b.mdx").read_text())

    def test_unbacked_entry_is_a_no_op(self):
        self.assertFalse(generate.apply_description({"path": "docs/a/ghost"}, "x"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
