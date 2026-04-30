# DeepL Developer Docs

This repo is home to the [DeepL Developer Docs](https://developers.deepl.com/)
and the authoritative [OpenAPI specification](https://openapis.org/) of the
[DeepL API](https://www.deepl.com/pro-api).

## Development

Install the [Mintlify CLI](https://www.npmjs.com/package/mint) to preview the documentation changes locally. To install, use the following command

```
npm i -g mint
```

Run the following command at the root of your documentation (where docs.json is)

```
mint dev
```

### Migrating from the old `mintlify` CLI

If you have the deprecated `mintlify` package installed, replace it with `mint`:

```
npm uninstall -g mintlify
npm cache clean --force
npm i -g mint
```

### Publishing Changes

Install our Github App to auto propagate changes from your repo to your deployment. Changes will be deployed to production automatically after pushing to the default branch. Find the link to install on your dashboard.

#### Troubleshooting

- Mint dev isn't running - Run `mint install` to re-install dependencies.
- Page loads as a 404 - Make sure you are running in a folder with `docs.json`

## AI Workflow

Agents in `.claude/agents/` are automatically available to anyone who clones this repo:

| Agent | Purpose | When to use |
|-------|---------|-------------|
| `diataxis` | Full Diataxis framework expert for both writing and reviewing | Writing new content or checking type adherence |
| `docs-review` | Orchestrator that runs editorial + Diataxis reviews in parallel and writes a single report | Before opening a PR, or reviewing someone else's PR |
| `editorial-reviewer` | Checks style, structure, code examples against CLAUDE.md | Called by `docs-review` (you don't need to invoke directly) |

### Recommended Workflow

**Writing new content:**
```
Use the diataxis agent to help me write a how-to guide for [topic]
```

**Before opening a PR:**
```
Use the docs-review agent on [filename]
```

**Check for broken links:**
```
mint broken-links
mint broken-links --check-anchors
```

## OpenAPI specification

This project contains an [OpenAPI specification](https://openapis.org/) of the [DeepL API](https://www.deepl.com/pro-api), in YAML and JSON formats.

| File | Purpose |
|---|---|
| [`api-reference/openapi.yaml`](api-reference/openapi.yaml) | Main REST API spec (source of truth) |
| [`api-reference/openapi.json`](api-reference/openapi.json) | Same content, JSON format (auto-generated) |
| [`api-reference/voice/voice.asyncapi.yaml`](api-reference/voice/voice.asyncapi.yaml) | AsyncAPI spec for the streaming voice API (source of truth) |
| [`api-reference/voice/voice.asyncapi.json`](api-reference/voice/voice.asyncapi.json) | Same content, JSON format (auto-generated) |

You can use this specification to explore the API in tools like [Postman](https://www.postman.com/), or to auto-generate documentation, SDKs, and code libraries using tools such as [Swagger Editor](https://editor.swagger.io/?url=https://raw.githubusercontent.com/DeepLcom/api-docs/main/api-reference/openapi.yaml) or [OpenAPI Generator](https://openapi-generator.tech/).

Note that Swagger's "Try it out" in-browser simulator creates valid Curl requests, the requests will fail due to [CORS](https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS) restrictions.

For release notes and the latest API changes, see [Roadmap and release notes](https://developers.deepl.com/docs/resources/roadmap-and-release-notes).

If you encounter issues while using this OpenAPI specification or have feature requests, please [create an issue](https://github.com/DeepLcom/api-docs/issues).

### Regenerating the JSON files

The JSON files are auto-generated from the YAML sources. **Don't edit them by hand.**

A GitHub Actions workflow regenerates them on any PR that touches the YAML sources and commits the result back to the PR branch. To preview locally:

```bash
yq -o=json '.' api-reference/openapi.yaml > api-reference/openapi.json
yq -o=json '.' api-reference/voice/voice.asyncapi.yaml > api-reference/voice/voice.asyncapi.json
```
