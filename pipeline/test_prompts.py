#!/usr/bin/env python3
"""Tests for prompt assembly and reply-shape checking.

    python pipeline/test_prompts.py

The .claude/agents/*.md files are agent definitions written for a harness with
tools. The pipeline reuses their prose in plain API calls where no tools exist,
and when their tool instructions leak through, the model returns a transcript of
itself "researching" instead of a page. These cover both halves of the guard:
stripping the `tools:` frontmatter, and recognizing a reply that isn't a file.
"""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from util import (  # noqa: E402
    NO_TOOLS,
    build_authoring_system_prompt,
    build_review_system_prompt,
    format_retry_prompt,
    load_agent,
    looks_like_mdx,
)


class LoadAgentTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.dir = Path(self._tmp.name)

    def write(self, text):
        path = self.dir / "agent.md"
        path.write_text(text, encoding="utf-8")
        return path

    def test_drops_the_frontmatter_including_the_tools_line(self):
        path = self.write(
            "---\nname: docs-writer\ntools: Read, Write, Grep, Glob, Agent\n---\n\n"
            "# Your Role\n\nYou write docs.\n"
        )
        body = load_agent(path)
        self.assertTrue(body.startswith("# Your Role"))
        self.assertNotIn("tools:", body)
        self.assertIn("You write docs.", body)

    def test_a_file_without_frontmatter_is_unchanged(self):
        path = self.write("# Just Prose\n\nNo frontmatter here.\n")
        self.assertEqual(load_agent(path), "# Just Prose\n\nNo frontmatter here.\n")

    def test_body_horizontal_rules_survive(self):
        """Only the leading block is frontmatter; --- later is content."""
        path = self.write("---\nname: a\n---\n\n# T\n\nOne\n\n---\n\nTwo\n")
        body = load_agent(path)
        self.assertIn("\n---\n", body)
        self.assertIn("Two", body)

    def test_missing_file_is_empty(self):
        self.assertEqual(load_agent(self.dir / "nope.md"), "")


class SystemPromptTest(unittest.TestCase):
    """Built from the repo's real agent files."""

    def test_authoring_prompt_carries_the_override_and_no_tools_frontmatter(self):
        prompt = build_authoring_system_prompt("You are a documentation writer.")
        self.assertIn(NO_TOOLS, prompt)
        self.assertNotIn("tools: Read, Write", prompt)
        self.assertIn("Output ONLY the .mdx file content", prompt)

    def test_the_override_comes_after_the_guidelines_it_overrides(self):
        prompt = build_authoring_system_prompt("role")
        self.assertGreater(prompt.index(NO_TOOLS), prompt.index("Docs Writer Guidelines"))

    def test_review_prompt_too(self):
        prompt = build_review_system_prompt()
        self.assertIn(NO_TOOLS, prompt)
        self.assertNotIn("tools: Read, Grep", prompt)


class LooksLikeMdxTest(unittest.TestCase):
    def test_a_page_passes(self):
        self.assertTrue(looks_like_mdx('---\ntitle: "T"\n---\n\nBody.\n'))

    def test_leading_blank_lines_are_tolerated(self):
        self.assertTrue(looks_like_mdx('\n\n---\ntitle: T\n---\n\nBody.\n'))

    def test_the_faked_tool_transcript_fails(self):
        """The actual failure this guard exists for."""
        reply = (
            "I'll research the GitHub repo and peer pages before writing.\n\n"
            '<tool_call>\n{"name": "Glob", "arguments": {"pattern": "docs/**/*.mdx"}}\n'
            "</tool_call>\n<tool_response>\n---\ntitle: A peer page\n---\n</tool_response>\n"
        )
        self.assertFalse(looks_like_mdx(reply))

    def test_commentary_then_a_page_fails(self):
        self.assertFalse(looks_like_mdx("Here is the page:\n\n---\ntitle: T\n---\n\nBody.\n"))

    def test_unclosed_frontmatter_fails(self):
        self.assertFalse(looks_like_mdx("---\ntitle: T\n\nBody with no closing fence.\n"))

    def test_empty_and_none(self):
        self.assertFalse(looks_like_mdx(""))
        self.assertFalse(looks_like_mdx(None))


class RetryPromptTest(unittest.TestCase):
    def test_names_the_problem_and_forbids_a_preamble(self):
        prompt = format_retry_prompt("it did not start with YAML frontmatter (---)")
        self.assertIn("did not start with YAML frontmatter", prompt)
        self.assertIn("No preamble", prompt)


if __name__ == "__main__":
    unittest.main(verbosity=2)
