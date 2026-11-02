#!/usr/bin/env python3
"""Tests for resolving a docs.json page ID to its file.

    python pipeline/test_page_file.py

Stdlib only: each test builds a throwaway docs tree in a temp directory.
"""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from util import page_file  # noqa: E402


class PageFileTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)

    def touch(self, rel):
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("---\ntitle: t\n---\n", encoding="utf-8")

    def test_resolves_an_mdx_page(self):
        self.touch("docs/a.mdx")
        self.assertEqual(page_file("docs/a", self.root), "docs/a.mdx")

    def test_falls_back_to_md(self):
        self.touch("docs/a.md")
        self.assertEqual(page_file("docs/a", self.root), "docs/a.md")

    def test_prefers_mdx_over_md(self):
        self.touch("docs/a.mdx")
        self.touch("docs/a.md")
        self.assertEqual(page_file("docs/a", self.root), "docs/a.mdx")

    def test_a_page_and_a_folder_with_the_same_name_resolve_to_the_page(self):
        # docs/resources/breaking-changes-change-notices.mdx sits next to a folder of
        # the same name; the folder must never be mistaken for the page.
        self.touch("docs/a.mdx")
        self.touch("docs/a/child.mdx")
        self.assertEqual(page_file("docs/a", self.root), "docs/a.mdx")

    def test_a_folder_without_a_page_resolves_to_nothing(self):
        self.touch("docs/a/child.mdx")
        self.assertIsNone(page_file("docs/a", self.root))

    def test_a_missing_page_resolves_to_nothing(self):
        self.assertIsNone(page_file("docs/missing", self.root))


if __name__ == "__main__":
    unittest.main()
