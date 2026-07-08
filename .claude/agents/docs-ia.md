---
name: docs-ia
description: The information architecture of the DeepL developer docs — how the site is organized and what each part must contain. Read this before generating, reworking, moving, or auditing any page. Used by humans and by the docs pipeline.
---

# Developer Docs Information Architecture

This is the human-readable source of truth for how the DeepL developer docs are
structured. It is prose on purpose: both people and the pipeline read it. The only
machine-readable companion is `standards/ia.yaml`, which holds the one thing that
can't be inferred from prose — the map from OpenAPI tags to product families.

Mintlify's `docs.json` is the live structure of the site (which page sits in which
tab and group). When you need to know what currently exists, read `docs.json`. When
you need to know what *should* exist and how it should read, read this file.

## The shape of the site

The docs are organized into **tabs**. There are three kinds:

### 1. Home (a hub tab)

One tab for everything that spans products: onboarding, languages, going to
production, cookbooks, developer tools, API updates. It is the front door.

The Home tab must:
- Orient a new developer (what DeepL's APIs are, how to make a first call).
- Link out to every product tab. Every product family with a tab gets a
  card/link here. If a product exists but Home doesn't point to it, that's a gap.
- Hold only cross-cutting content. Product-specific tutorials and how-tos belong
  in that product's tab, not here.

### 2. Product tabs (one per product family)

Each product family (Translate, Voice, Write, Admin, …) gets its own tab holding
its narrative documentation: the tutorials, how-to guides, and explanations for
that product. A product tab must have:

- **An overview / landing page** — orientation: what the product does, links to
  everything in the tab. (This is a structural page, exempt from one-Diataxis-type.)
- **At least one tutorial** — a guided, start-to-finish first success.
- **A how-to guide for each major capability** the product exposes. If the API
  Reference shows a capability (endpoint group) that has no corresponding how-to in
  the product tab, that's a gap.

A product family can exist in the API Reference before it has a product tab (a new
API often ships reference-first). That reference-only state is itself a gap: the
product needs a tab with at least an overview and a tutorial.

### 3. API Reference (one unified tab)

A single tab for endpoint reference, generated from the OpenAPI spec, grouped by
product family. Rules:

- **One page per endpoint.** Reference mirrors the machinery.
- **No standalone overview or narrative pages.** The API Reference tab is reference
  only. Conceptual material, orientation, and "how it works" narrative live in the
  product tab or Home, never here. If a narrative/overview page appears under the
  API Reference tab, it should be folded into the first endpoint page of its group
  or moved to the product tab, then retired. This is a hard rule.
- Groups use Mintlify `tag` labels (BETA, DEPRECATED, ALPHA) rather than prose
  banners for lifecycle state.

## Product families

A product family is a group of related OpenAPI endpoints that a developer thinks of
as one product. Families are derived from OpenAPI tags; `standards/ia.yaml` maps
tags to families and names each family's product tab and API Reference group. Keep
that map current: when a new OpenAPI tag appears that isn't mapped, the pipeline
flags it for a human to place.

Current families: Translate, Customize, Write, Voice, Admin, Languages. (See
`standards/ia.yaml` for the exact tag membership.)

## Diataxis

Every content page serves exactly one Diataxis type (tutorial, how-to, reference,
explanation). Overview/landing pages are structural and exempt. The rules for each
type — structure, voice, title conventions, the cookbook test — live in
`.claude/agents/diataxis.md`. Don't restate them; read that file.

## What "complete" means (how gaps are judged)

For each product family, walk the three surfaces and check:

1. **API Reference** — is every endpoint in the family represented? (Usually yes,
   it's generated.) Are there any narrative pages that shouldn't be there?
2. **Product tab** — does the family have a tab? Does the tab have an overview, at
   least one tutorial, and a how-to for each major capability in the API Reference?
3. **Home** — does the hub link to this product?

A gap is any place a surface falls short of the above. The canonical example:
a new Voice capability ships in the API Reference, but the Voice tab has no how-to
for it and Home wasn't updated to surface it. All three are gaps.

## Principles for ongoing content

1. One Diataxis type per content page (overviews exempt).
2. Product-first placement: content goes under its product tab; only genuinely
   cross-cutting content goes in Home.
3. No catch-all tabs or groups. "Best Practices" and "Resources" are not valid
   groupings — content belongs under a product or a named cross-cutting section.
4. New products get the full structure: overview + tutorial + how-tos in a product
   tab, endpoint pages in the API Reference, a card on Home.
5. Reference is reference. Narrative never lives in the API Reference tab.
