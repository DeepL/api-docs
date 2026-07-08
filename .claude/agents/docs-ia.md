---
name: docs-ia
description: The information architecture of the DeepL developer docs — how the site is organized and what each part must contain. Read this before generating, reworking, moving, or auditing any page. Used by humans and by the docs pipeline.
---

# Developer Docs Information Architecture

This is the human-readable source of truth for how the DeepL developer docs are
structured. It is prose on purpose: both people and the pipeline read it. Its only
machine-readable companion is `standards/ia.yaml`, which holds what can't be inferred
from prose — the map from OpenAPI tags to product families, and where each family's
narrative docs live.

Mintlify's `docs.json` is the live structure of the site (which page sits in which
tab and group). When you need to know what currently exists, read `docs.json`. When
you need to know what *should* exist and how it should read, read this file.

## Two taxonomies, kept separate

The single most important thing to understand: **API grouping and narrative placement
are different decisions.**

- **API Reference groups** are mechanical. Every endpoint carries an OpenAPI tag, and
  those tags group the reference. This is comprehensive and spec-driven — every
  endpoint lands in exactly one group, automatically.
- **Narrative home** is editorial. Where a feature's tutorials, how-tos, and
  explanations live is a deliberate call. It does *not* have to mirror the API
  grouping. A feature can be its own API Reference group while its narrative lives
  under a related product's tab.

Example: Quality Estimation may be its own API Reference group but have its guides
filed under Translate, because a developer thinks of it as part of translating. The
API grouping and the narrative home diverge, and that's fine.

So: **an API Reference group existing without its own narrative section is not
automatically a gap.** Whether a feature gets its own tab, nests under another, or
(rarely) stays reference-only is recorded per family in `standards/ia.yaml`.

### Narrative home values

Each family in `ia.yaml` declares a `narrative_home`:

- **`own`** — the family has its own top-level product tab. Current own-tab families:
  **Translate, Voice, Admin.** (This list is editorial and will change.)
- **`<Tab>`** — the family's narrative nests under another tab (e.g. Customize under
  Translate; Languages under Home). No separate tab, no separate overview required.
- **`reference_only`** — no narrative docs, intentionally. **Rare.** Reserved for
  early alpha features, and even then a guide is usually still wanted. This is an
  explicit, logged decision, not a default and not an escape hatch — the pipeline
  still nudges ("consider a guide," required once it leaves alpha).
- **`unplaced`** — placement not yet decided. Surfaces as a gap for a human to
  resolve. The pipeline never invents a placement.

The default expectation is that a feature has narrative docs *somewhere*. Missing
narrative is a gap unless a human has explicitly chosen `reference_only`.

## The shape of the site

The docs are organized into **tabs**. Three kinds:

### 1. Home (a hub tab)

One tab for everything that spans products: onboarding, languages, going to
production, cookbooks, developer tools, API updates. It is the front door.

The Home tab must:
- Orient a new developer (what DeepL's APIs are, how to make a first call).
- Link out to every family whose `narrative_home` is `own`. If an own-tab product
  exists but Home doesn't surface it, that's a gap.
- Hold only cross-cutting content, plus the narrative for families filed `under: Home`.

### 2. Product tabs (own-tab families)

A product tab is the narrative home for a product we want developers to adopt and
that warrants its own space. A product tab has:

- **An overview / landing page** — orientation: what the product does, links to
  everything in the tab. (Structural page, exempt from one-Diataxis-type.)
- **At least one tutorial** — a guided, start-to-finish first success.
- **How-to guides** for its major capabilities.

Families filed `under` a product tab (e.g. Customize under Translate) live as a group
inside that tab and don't need their own overview or tutorial — their coverage is the
parent tab's concern.

### 3. API Reference (one unified tab)

A single tab for endpoint reference, generated from the OpenAPI spec, grouped by API
tag. Rules:

- **One page per endpoint.** Reference mirrors the machinery.
- **No standalone overview or narrative pages.** The API Reference tab is reference
  only. Conceptual material, orientation, and "how it works" narrative live in a
  product tab or Home, never here. A narrative/overview page under the API Reference
  tab should be folded into the first endpoint page of its group or moved to the
  narrative home, then retired. Hard rule.
- Groups use Mintlify `tag` labels (BETA, DEPRECATED, ALPHA) for lifecycle state.

## Product families

A product family is a group of related OpenAPI endpoints that a developer thinks of as
one product. `standards/ia.yaml` maps tags to families and records each family's
`narrative_home` and API Reference group. Keep it current: when a new OpenAPI tag
appears that isn't mapped, the pipeline flags it for a human to place.

## Diataxis

Every content page serves exactly one Diataxis type (tutorial, how-to, reference,
explanation). Overview/landing pages are structural and exempt. The rules for each
type — structure, voice, title conventions, the cookbook test — live in
`.claude/agents/diataxis.md`. Don't restate them; read that file.

## What "complete" means (how gaps are judged)

Per family, based on its `narrative_home`:

- **`own`**: needs an overview, at least one tutorial, and how-to coverage of its
  capabilities in its tab, plus a link from Home. Anything missing is a gap.
- **`<Tab>`**: coverage is checked inside the parent tab, not as a standalone section.
- **`reference_only`**: no hard requirements, but the pipeline emits a low-severity
  "consider a guide" nudge (and expects one once the feature leaves alpha).
- **`unplaced`**: a gap — a human must choose the narrative home.

Separately, the API Reference tab is checked for narrative pages that don't belong
there.

## Principles for ongoing content

1. One Diataxis type per content page (overviews exempt).
2. Narrative placement is deliberate, recorded in `ia.yaml`, and decoupled from API
   grouping.
3. Narrative is the default; `reference_only` is rare and explicit.
4. No catch-all tabs or groups. "Best Practices" and "Resources" are not valid
   groupings — content belongs under a product or a named cross-cutting section.
5. Reference is reference. Narrative never lives in the API Reference tab.
