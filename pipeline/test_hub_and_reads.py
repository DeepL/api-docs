#!/usr/bin/env python3
"""Tests for the thin-page hub exemption and for reading the page a gap edits.

    python pipeline/test_hub_and_reads.py

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
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self._saved = (detect_gaps.REPO_ROOT, generate.REPO_ROOT)
        detect_gaps.REPO_ROOT = self.root
        generate.REPO_ROOT = self.root
        self.addCleanup(self._restore)

    def _restore(self):
        detect_gaps.REPO_ROOT, generate.REPO_ROOT = self._saved
        self._tmp.cleanup()

    def write(self, rel, text="---\ntitle: T\n---\n\nSome body copy.\n"):
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


class HasChildPagesTest(unittest.TestCase):
    def test_a_page_with_children_is_a_hub(self):
        pages = ["docs/notices", "docs/notices/july-2024"]
        self.assertTrue(detect_gaps.has_child_pages(pages, "docs/notices"))

    def test_a_leaf_is_not(self):
        self.assertFalse(detect_gaps.has_child_pages(["docs/a", "docs/b"], "docs/a"))

    def test_a_name_prefix_is_not_a_child(self):
        """'docs/x-ray' must not count as a child of 'docs/x'."""
        self.assertFalse(detect_gaps.has_child_pages(["docs/x", "docs/x-ray"], "docs/x"))


class ThinPageDetectionTest(TempDocsTree):
    def test_hub_is_not_flagged_but_a_real_thin_page_is(self):
        short = "---\ntitle: T\ndescription: d\n---\n\nToo short.\n"
        for page in ("docs/hub", "docs/hub/child", "docs/lonely"):
            self.write(f"{page}.mdx", short)
        docs_json = {"navigation": {"tabs": [
            {"tab": "Home", "pages": ["docs/hub", "docs/hub/child", "docs/lonely"]},
        ]}}

        thin = [g["description"] for g in detect_gaps.detect_gaps(docs_json, [], {})
                if g["type"] == "thin_page"]
        self.assertEqual(sorted(thin), [
            "docs/hub/child has under 100 words",  # a child can still be thin
            "docs/lonely has under 100 words",
        ])


class LoadExistingPageTest(TempDocsTree):
    def test_reads_the_page(self):
        self.write("docs/a.mdx", "---\ntitle: T\n---\n\nReal content.\n")
        page = generate.load_existing_page({"type": "thin_page", "path": "docs/a.mdx"})
        self.assertIn("Real content.", page)

    def test_a_missing_file_raises_instead_of_returning_nothing(self):
        """An empty read used to become "write this page from scratch"."""
        with self.assertRaises(FileNotFoundError):
            generate.load_existing_page({"type": "thin_page", "path": "docs/ghost.mdx"})

    def test_a_directory_raises_file_not_found_not_is_a_directory(self):
        self.write("docs/a/child.mdx")
        with self.assertRaises(FileNotFoundError):
            generate.load_existing_page({"type": "thin_page", "path": "docs/a"})

    def test_an_empty_page_raises(self):
        self.write("docs/blank.mdx", "   \n")
        with self.assertRaises(ValueError):
            generate.load_existing_page({"type": "thin_page", "path": "docs/blank.mdx"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
