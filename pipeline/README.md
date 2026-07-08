# Docs Pipeline

End-to-end pipeline for detecting documentation gaps, generating drafts, reviewing them, and shipping as PRs.

## Control panel — where to change the output

Everything a human controls about what the pipeline produces lives in one of these
files. The pipeline scripts contain orchestration only (which file, which path, which
step) — no prose rules, no prompts. If you don't like the output, this table is the
one place to look.

| To change… | Edit | Notes |
| --- | --- | --- |
| **How pages read** (voice, structure, DRY, descriptions, content preservation) | `.claude/agents/docs-writer.md` | Also usable by hand — it's the docs-writer agent. |
| **What each Diataxis type is** (tutorial / how-to / reference / explanation) | `.claude/agents/diataxis.md` | Shared by generate, rework, review, and the batch planner. |
| **Site structure & placement rules** (tabs, per-tab requirements, no-narrative-in-reference, hub rules) | `.claude/agents/docs-ia.md` | Human-readable IA source of truth. |
| **Review criteria** | `.claude/agents/editorial-reviewer.md` | The review-step rubric. |
| **General writing style** | `CLAUDE.md` (repo root) | docs-writer wins on conflict. |
| **Which OpenAPI tags map to which product family / tab / API-ref group** | `standards/ia.yaml` | The only structured data. Tiny by design — rules go in `docs-ia.md`, not here. |
| **Live site structure** (which page is in which tab) | `docs.json` | Mintlify's own file; the pipeline reads it, never duplicates it. |

All model prompts are assembled from the files above in one place: the
`build_*_system_prompt` / `load_planning_context` helpers in `pipeline/util.py`. That
is plumbing — change behavior in the files above, not in `util.py`.

## Setup

```bash
pip install anthropic pyyaml
export ANTHROPIC_API_KEY=...
```

## Pipeline Steps

The pipeline runs as a sequence of independent scripts. Each step reads the output of the previous one. You can run any step standalone, or use `run.py` to chain them all.

```
Phase 3 (new pages):   detect_gaps.py → generate.py → evaluate.py → review.py → promote.py → ship.py → post_review.py
Phase 2 (IA cleanup):  rework.py ─────────────────────→ evaluate.py → review.py → promote.py → ship.py → post_review.py
```

### 1. Detect Gaps

Cross-references three surfaces — the API Reference (OpenAPI endpoints), the product tabs, and the Home hub — using `docs.json` for live structure and `standards/ia.yaml` for the tag→family map. Deterministic, no API key needed.

```bash
python pipeline/detect_gaps.py                         # full audit
python pipeline/detect_gaps.py --section admin          # one product family
python pipeline/detect_gaps.py --output json            # machine-readable
python pipeline/detect_gaps.py --force                  # report requirement gaps even when satisfied
```

**What it checks (per family, across surfaces):** missing product tab, missing overview / tutorial / how-to, missing hub link, narrative pages sitting in the API Reference tab, ungrouped OpenAPI tags, plus thin pages (< 100 words) and missing frontmatter descriptions.

**What it doesn't check:** fine-grained judgment (is *this specific* endpoint missing a how-to, is a page the wrong Diataxis type) — that's the LLM audit (`audit_gaps.py`, follow-up); style/Diataxis prose compliance (the review step); code sample correctness (validation step).

### 2. Generate Drafts

Calls Claude to draft missing pages. Writes to `pipeline/drafts/<timestamp>/`, not to the docs tree. Writing rules come from `.claude/agents/docs-writer.md` (the script's prompts describe WHAT to generate, the agent file defines HOW to write).

```bash
python pipeline/generate.py --dry-run                   # preview what would be generated
python pipeline/generate.py --section admin              # generate for one family
python pipeline/generate.py --type missing_orientation   # generate one gap type
python pipeline/generate.py --force                      # regenerate even if files exist
python pipeline/generate.py --section admin --force      # regenerate one section
```

Each run creates a timestamped folder under `pipeline/drafts/` with the generated `.mdx` files and a `report.json` with metadata.

### 2b. Rework Existing Pages (Phase 2 alternative to Generate)

Transforms existing content instead of generating from scratch. Used for IA Phase 2 cleanup: consolidate, merge, split, expand, retire, or rework pages. Outputs to the same `pipeline/drafts/` structure so the rest of the pipeline works unchanged.

```bash
python pipeline/rework.py consolidate --source A.mdx B.mdx --target A.mdx --instruction "..."
python pipeline/rework.py merge --source A.mdx B.mdx --target C.mdx --instruction "..."
python pipeline/rework.py split --source A.mdx --target B.mdx C.mdx --instruction "..."
python pipeline/rework.py expand --source A.mdx --instruction "..."
python pipeline/rework.py retire --source A.mdx --target B.mdx C.mdx --instruction "..."
python pipeline/rework.py rework --source A.mdx --instruction "..."
```

Add `--label` to tag the run directory (e.g. `--label consolidate-onboarding`). Add `--dry-run` to preview.

For `retire` and `merge`, a `retire.json` file is written listing source pages that should be deleted after promotion (promote.py does not auto-delete).

### 3. Evaluate (Quality Gate)

Deterministic quality checks on drafts. No API key needed. Catches rule violations before the more expensive LLM review.

```bash
python pipeline/evaluate.py --latest                    # check most recent run
python pipeline/evaluate.py --latest --verbose          # detailed findings with line numbers
python pipeline/evaluate.py --latest --output json      # machine-readable
python pipeline/evaluate.py pipeline/drafts/20260706-192742  # specific run
```

**Checks:** frontmatter (title, description quality, length), DRY violations (nav sections, endpoint tables outside api-reference), structure (headings, word count, callout limits), code (fenced blocks, language identifiers).

Exit code 0 if no errors (warnings OK), 1 if errors found.

### 4. Review (LLM Review Loop)

Sends each draft to Claude for editorial and Diataxis review. Auto-fixes "must fix" findings, then re-reviews. Capped at 2 iterations by default.

```bash
python pipeline/review.py --latest                      # review most recent run
python pipeline/review.py --latest --dry-run            # show what would be reviewed
python pipeline/review.py --latest --max-iterations 1   # single pass, no re-review
python pipeline/review.py --latest --file docs--admin--overview.mdx  # one file
```

Writes a `review-report.json` to the run directory with findings, fix counts, and per-file status. Overwrites draft files in place with fixes applied.

Exit code 0 if all files clean or only "consider" items remain, 1 if "must fix" items remain after max iterations.

### 5. Promote

Copies approved drafts from a run into the canonical docs tree and updates `docs.json` navigation.

```bash
python pipeline/promote.py --latest --dry-run           # preview changes
python pipeline/promote.py --latest                     # promote all drafts in latest run
python pipeline/promote.py --latest --file docs--admin--overview.mdx  # one file
python pipeline/promote.py pipeline/drafts/20260706-192742           # specific run
```

Overview pages are inserted first in their nav group, tutorials second. New groups are created before "Going to Production." Runs `mint broken-links` after promotion if available.

### 6. Ship

Creates a git branch and opens a PR for human review.

```bash
python pipeline/ship.py --latest --dry-run              # preview branch, commit, PR body
python pipeline/ship.py --latest                        # create branch, commit, prompt before push
python pipeline/ship.py --latest --yes                  # skip push confirmation
python pipeline/ship.py --latest --branch docs/my-branch  # custom branch name
```

Requires `gh` CLI authenticated. Stages only `docs/**/*.mdx` and `docs.json`. Never force-pushes.

### 7. Post Review (PR Suggestions)

Posts "consider" findings from the review report as GitHub PR review comments with `suggestion` blocks. The reviewer can click "Apply suggestion" to accept changes directly in the PR.

```bash
python pipeline/post_review.py --latest --pr 42 --dry-run   # preview what would be posted
python pipeline/post_review.py --latest --pr 42              # post to PR #42
python pipeline/post_review.py --latest                      # auto-detect PR from current branch
python pipeline/post_review.py --latest --include-must-fix   # also post remaining must_fix items
```

For each finding with a `suggested_fix`, calls Claude to generate exact replacement text and formats it as a GitHub suggestion block. Findings without a concrete fix are posted as plain review comments. All comments are submitted as a single PR review.

Requires `gh` CLI authenticated and an open PR.

## E2E Runner (`run.py`)

Run the entire pipeline with one command. Chains all steps, stops on failure, prints resume instructions.

### New pages (Phase 3: fill gaps)

```bash
# Full pipeline: detect gaps → generate → evaluate → review → promote → ship → post_review
python pipeline/run.py generate --section admin --force

# Dry run the whole pipeline
python pipeline/run.py generate --section admin --dry-run
```

### Rework existing pages (Phase 2: IA cleanup)

```bash
# Consolidate multiple pages into one
python pipeline/run.py rework consolidate \
  --source docs/getting-started/intro.mdx docs/getting-started/about.mdx \
  --target docs/getting-started/intro.mdx \
  --instruction "Rework Introduction as orientation page, absorb About content"

# Merge two pages
python pipeline/run.py rework merge \
  --source docs/translate/xml-html/xml.mdx docs/translate/xml-html/structured-content.mdx \
  --target docs/translate/xml-html/handle-xml-content.mdx \
  --instruction "Merge into one Handle XML content how-to"

# Split a page
python pipeline/run.py rework split \
  --source docs/translate/xml-html/tag-handling-v2.mdx \
  --target docs/translate/xml-html/how-tag-handling-works.mdx docs/translate/xml-html/migrate-tag-handling.mdx \
  --instruction "Keep explanation, extract migration how-to"

# Expand a thin page
python pipeline/run.py rework expand \
  --source docs/translate/text/detect-languages.mdx \
  --instruction "Currently 3 sentences. Expand into proper how-to."

# Retire a page (fold content into other pages)
python pipeline/run.py rework retire \
  --source docs/getting-started/authentication.mdx \
  --target docs/getting-started/your-first-api-request.mdx docs/admin/overview.mdx \
  --instruction "Fold how-to into first API request, fold reference into Admin overview"

# Rework in place
python pipeline/run.py rework rework \
  --source docs/admin/managing-api-keys.mdx \
  --instruction "Strip reference content, keep how-to walkthrough"
```

### Resume after failure

If any step fails, the runner prints a resume command:

```bash
# Resume from review step on the latest run
python pipeline/run.py --resume review --latest

# Resume from promote on a specific run
python pipeline/run.py --resume promote pipeline/drafts/20260706-192742

# Skip a step
python pipeline/run.py generate --section admin --skip post_review
```

## Batch Runner (`batch.py`)

Run all IA Phase 2 tasks through the pipeline in sequence. Each task is a freeform description (pulled from the IA Proposal). A planning step uses Claude to resolve each description into concrete file paths, then runs the full pipeline per task.

```bash
# Preview plans — see what files each task would read/write
python pipeline/batch.py --plan

# Dry-run — plan + dry-run each pipeline step
python pipeline/batch.py --dry-run

# Run all tasks, 1 PR per task
python pipeline/batch.py

# Run specific tasks by index
python pipeline/batch.py --only 1,3,5

# Accumulate all tasks on one branch → push → PR → post review suggestions
python pipeline/batch.py --branch docs/ia-phase2-reworks

# Subset on one branch
python pipeline/batch.py --branch docs/ia-phase2-reworks --only 8,9,10,11,12

# Stop after committing (review locally before pushing)
python pipeline/batch.py --branch docs/ia-phase2-reworks --no-push
```

With `--branch`, each task runs through rework → evaluate → review → promote, then commits the promoted changes. After all tasks, the runner pushes the branch, creates a PR, and posts "consider" suggestions as inline PR comments via `post_review.py`. Use `--no-push` to stop after committing for local review.

Without `--branch`, each task gets its own branch and PR.

If a task fails, the runner cleans up uncommitted changes and continues with the next task.

Task descriptions are defined in the `TASKS` list at the top of `batch.py`. Edit that list to add, remove, or reorder tasks.

## Running Steps Individually

Each script is standalone. You can run any step without the E2E runner.

### Comparing Runs

Draft folders are timestamped and preserved. To compare runs after changing prompts/rules:

```bash
python pipeline/generate.py --section admin --force
python pipeline/evaluate.py pipeline/drafts/run-01
python pipeline/evaluate.py --latest
diff pipeline/drafts/run-01/docs--admin--overview.mdx pipeline/drafts/<latest>/docs--admin--overview.mdx
```

### Testing Individual Steps

```bash
python pipeline/evaluate.py pipeline/drafts/run-01 --verbose
python pipeline/promote.py pipeline/drafts/run-01 --file docs--voice--overview.mdx --dry-run
python pipeline/ship.py --latest --dry-run
```

## Architecture

### Content Rules

All rules and prompts live in the files listed under [Control panel](#control-panel--where-to-change-the-output) — the `.claude/agents/*.md` files plus `CLAUDE.md`. Every step assembles its prompt from those files via `pipeline/util.py`, so there is exactly one copy of each rule, shared by the pipeline and by manual authoring with Claude.

The pipeline scripts contain NO writing rules, Diataxis definitions, or structure rules in their prompts. They describe WHAT to do (gap type, product family, target path) and delegate HOW to the agent files. When they conflict, docs-writer wins over CLAUDE.md.

### Draft Storage

All generated content goes to `pipeline/drafts/<timestamp>/` first. Files are named with `--` replacing path separators (`docs--admin--overview.mdx` → `docs/admin/overview.mdx`). Nothing touches the docs tree until `promote.py` runs.

### IA Standards

Structure is defined in two places, by design:
- **Rules** (what "fully documented" means, tab requirements, no-narrative-in-reference) are prose in [`.claude/agents/docs-ia.md`](../.claude/agents/docs-ia.md).
- **Data** (which OpenAPI tags belong to which family, and each family's product tab + API-ref group) is the tiny map in [`standards/ia.yaml`](../standards/ia.yaml).

The live site structure (which page sits in which tab) is read from `docs.json` at runtime, never duplicated. When an OpenAPI tag isn't mapped in `ia.yaml`, detect_gaps flags it for a human to place.

## Dependencies

- Python 3.8+
- `anthropic` (for generate.py, rework.py, review.py, post_review.py)
- `pyyaml` (for all scripts)
- `gh` CLI (for ship.py, post_review.py)
- `mint` / `npx` (optional, for broken-links check in promote.py)
