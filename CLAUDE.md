# DeepL Developer Documentation

Source for [developers.deepl.com](https://developers.deepl.com/), built on [Mintlify](https://mintlify.com/). Content lives in `.mdx` files under `docs/` (guides) and `api-reference/` (API reference).

## Writing Style

### Voice and Tone

Write like a knowledgeable colleague, not a textbook. Clear, direct, and friendly. Use second person ("you") to address the reader. "We" is fine both for DeepL as a company ("We recommend...") and as inclusive "you and I" in tutorials ("Let's configure..."). Active voice, present tense ("returns" not "will return," per the Google Developer Documentation Style Guide). Be concise: every sentence earns its place. Cut filler and throat-clearing.

Avoid jargon unless the audience already knows it. Define technical terms on first use. Don't be overly formal ("hereafter", "aforementioned") or overly casual ("gonna", "super easy").

### Developer Documentation Tone

No marketing language or sales copy. Flag "best-in-class", "game-changing", "major step forward." Replace with technical descriptors. Developers reading these docs have already chosen DeepL or been directed here; describe what the API does and how to use it, don't pitch business outcomes.

Frame version comparisons neutrally. Focus on what the new version provides, not what the old version "lacked." Never say a previous version was "bad" or "broken."

Action-oriented descriptions: frontmatter `description` fields should tell developers what they'll learn. "Learn how to X" over "Information about X." Descriptions must be uniquely descriptive of the specific page content — never generic enough to apply to multiple pages.

When noting limitations or incompatibilities, mention if they're temporary. "Currently only compatible with X. Support for Y will be added in a future update." Avoid indefinite phrases like "for the time being" without specifics.

Write from the external developer's perspective, never from DeepL's internal perspective. The reader doesn't care about internal team names, decisions, or how a feature was built. Watch for: "We will..." / "We plan to..." (rewrite as what the developer can expect), internal team references, Jira tickets, explaining DeepL's decision-making instead of the outcome.

### Structure and Formatting

Front-load key information. Lead with what the reader needs to do, not background.

Short paragraphs (3-4 lines max). Use headings, bullets, and tables to break up walls of text, but don't add subsections just for organization if 2-3 paragraphs or bullets suffice.

Use tables for structured comparisons (feature matrices, parameter lists, method trade-offs).

Use Mintlify components (`<Tabs>`, `<Steps>`, `<Tip>`, `<Warning>`, `<Note>`) where they improve clarity. Don't overuse them. Consolidate related examples into tabs rather than separate sections, placing the most common use case first.

### Content Principles

Write for an external developer who has never used DeepL before, wants to integrate a translation/writing API into their product, will skim your page in 30 seconds, and needs to know what to do, not how DeepL works internally.

Task-oriented over feature-oriented. Frame docs around what the user wants to accomplish. Every piece of information should answer "so what should I do?" If it doesn't, add guidance.

Show what a feature is before announcing what changed. Never assume the reader knows what something is. When describing updates or configuration, include one sentence explaining what the feature does and why a developer would use it.

Warn about the mistakes developers will actually make. Think about what goes wrong in practice. Add warnings for common pitfalls, not theoretical ones.

Progressive disclosure: introduce simple concepts before complex ones. Concrete before abstract: show examples before deep technical details. Connect technical features to practical use cases.

Show, don't just tell. Pair explanations with concrete examples.

Link generously. Cross-reference related pages rather than duplicating content.

When presenting multiple approaches, include a comparison table and "when to use this" guidance for each.

In migration guides and technical sections, prefer concise technical bullets over explanatory prose.

### Lists and Bullets

Avoid excessive use of bulleted lists. When you do use them:
- Bullet points end without periods (unless multi-sentence). Capitalize standalone items; lowercase is fine when bullets complete a stem sentence
- All items in a list follow the same grammatical structure (parallel construction)
- Use `-` or `*` for unordered lists (either is fine, but be consistent within a page), numbers for sequential steps

### Cross-references and Links

Use relative links for internal docs. Link text should be descriptive: "See [Managing API Keys](/docs/getting-started/managing-api-keys)" not "See [here](/docs/getting-started/managing-api-keys)."

### Formatting

No em-dashes. Use commas, periods, or parentheses. No curly/smart quotes; use straight quotes. Consistent list markers within a page (`-` or `*`, either is fine).

## Code Examples

### Structure

Each code example should include:
1. A brief introduction (one sentence explaining what the example demonstrates)
2. A complete, runnable code block (or clearly marked pseudo-code)
3. Key points explained after the code
4. Variations with pros/cons, if applicable

When showing API requests, include both the request and a sample response. Use the same example text/scenario across methods within a single doc for easy comparison. Use curl as the default, with SDK examples in tabs where available. Include the `Authorization: DeepL-Auth-Key` header in every curl example. Use realistic but simple data (not "hello world" unless it's a quickstart).

### Formatting

Always include the language identifier in fenced code blocks. Use 4 spaces for Python indentation (not tabs). Prefer breaking lines at 80-88 characters for readability.

Show import statements when first introducing a concept. Use descriptive variable names (`style_rule_list` not `srl`). Include type hints in function signatures when helpful for understanding. Show error handling in production-like examples, omit in minimal examples.

### Example Types

Distinguish between three types of code examples:
- **Minimal examples**: simplest possible demonstration of a concept
- **Production-like examples**: include error handling, logging, edge cases
- **Anti-patterns**: clearly marked with what NOT to do, always paired with the correct alternative

### Comments

Comment "why" not "what." The code shows what; comments explain why. Avoid redundant comments (`queue.close()  # Close the queue`).

**Teaching examples** get detailed explanatory comments. Use phase labels to organize multi-step processes. Inline comments clarify non-obvious parameters.

**Production-like examples** stay minimal. Let descriptive variable/function names speak for themselves. No redundant comments.

**Complex logic** always gets comments, especially async patterns, error handling with specific recovery strategies, edge cases, and performance-critical sections.

**Anti-patterns** use ❌/✅ markers consistently, include a brief explanation of why it's wrong, and always show the correct alternative.

Prefer explanatory text before/after code blocks over inline comments. Keep commenting density consistent within examples in the same section.

No TODO, FIXME, or placeholder comments in documentation.

### Inline Method Examples

When a doc presents multiple methods/approaches, each method section should include a short, focused code example:
- Place immediately after the "When to use this:" bullets
- Label properly ("Example cURL request", "Example response")
- Always show both request and response
- Keep short and focused on the method's key differentiator

When NOT to include inline examples: if the guide has a comprehensive example section later, or if the method requires setup steps that can't be shown inline. In these cases, add a note directing users to the detailed example section.

## Tables

Text columns: left-align. Status/symbol columns (✅/❌): center-align. Numeric columns: right-align.

Use bold text for all table headers. Use sentence case for headers. Use code formatting for code terms in cells. Use line breaks (`<br>`) sparingly, only when necessary for readability. Keep cell content concise: tables should be scannable.

Similar table types (feature matrices, comparison tables) should use the same structure throughout the docs.

## Info Boxes and Warnings

Use `<Tip>` for supplementary context. Use `<Warning>` for things that will cause bugs or unexpected behavior if ignored. Keep them to 1-2 sentences. If it's longer, it should be regular content. No more than 2 callout boxes per page.

## Changelog Entries

New entries go at the top of the month section, not the bottom. Format: `## Month Day - Feature Name` followed by bullet points. First bullet always explains what the feature is (not just that it shipped). Include links to relevant docs/API reference pages.

## Documentation Types (Diataxis)

This repo follows the [Diataxis framework](https://diataxis.fr/). When creating or reviewing docs, identify which type you're writing:

1. **Tutorials** (`learning-how-tos/`): Learning-oriented. Walk the reader through a complete task step by step.
2. **How-to guides** (`best-practices/`, some `docs/`): Goal-oriented. Show how to solve a specific problem.
3. **Reference** (`api-reference/`): Information-oriented. Accurate, complete, no opinions.
4. **Explanation** (various): Understanding-oriented. Clarify concepts, trade-offs, and architecture.

Don't mix types. A tutorial shouldn't become a reference doc mid-page. The `diataxis` agent (`.claude/agents/diataxis.md`) has the full framework knowledge and handles both writing guidance and review.

## AI Workflow

### Writing Documentation

When creating new documentation, start by identifying the Diataxis type (see above). Then either:

- Ask Claude naturally ("Create a how-to guide for configuring glossaries") and the `diataxis-documentation` plugin will activate automatically, guiding content toward the correct type.
- Or invoke the `diataxis` agent directly for more hands-on framework guidance:

      Use the diataxis agent to help me write [description]

Templates for each documentation type are available in `.claude/agents/diataxis-templates/`. The diataxis agent reads these automatically in writing mode.

To install the diataxis plugin (DeepL internal only):

    /plugin marketplace add https://git.deepl.dev/deepl/devex/ai-tooling/claude-code-marketplace.git
    /plugin install diataxis-documentation@deepl-claude-code-marketplace

### Reviewing Documentation

Use the `docs-review` orchestrator agent to review any doc:

    Use the docs-review agent on [filename]

This runs editorial and Diataxis reviews in parallel, deduplicates findings, and writes a single review to `reviews/`. You don't need to invoke the sub-agents separately.

**Review priority ordering**: Structural and Diataxis issues (type mixing, missing tutorial structure, wrong doc type) are always the highest-priority findings. Lead the summary and must-fix list with these. Formatting and style issues (tab order, list markers, capitalization) are important but secondary.

## File Conventions

- All content files use `.mdx` extension
- Frontmatter is required: at minimum `title`
- Images go in `_assets/images/`
- Navigation structure is defined in `docs.json` — update it when adding or moving pages
- Snippet files in `snippets/` can be reused across pages with Mintlify's snippet syntax

## Local Development

    npm i -g mint
    mint dev

After making changes, run `mint broken-links` and `mint broken-links --check-anchors` to verify links.
