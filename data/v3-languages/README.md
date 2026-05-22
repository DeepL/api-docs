# Vended `/v3/languages` responses

This directory holds verbatim JSON responses from the DeepL `/v3/languages` endpoints, fetched against `https://api.deepl.com`. Other tooling in this repo (e.g. generated docs and snippets) reads these files instead of calling the API directly.

## Files

| File | Endpoint |
|---|---|
| `resources.json` | `GET /v3/languages/resources` |
| `<resource>.json` | `GET /v3/languages?resource=<resource>&include=beta&include=external` |

where <resource> is one of the resources returned by `/resources` (`translate_text`, `translate_document`,
`voice`, `write`, etc.).

Each per-resource file requests `include=beta&include=external` so the vended data is the full superset. Consumers filter on the `status` and per-feature `external` fields when they want a narrower view.

These files are refreshed hourly by the [`refresh-v3-languages`](../../.github/workflows/refresh-v3-languages.yml) GitHub Action, which runs [`scripts/fetch_v3_languages.py`](../../scripts/fetch_v3_languages.py) and opens a pull request whenever the API responses change. See that script's module docstring or `--help` for flags and behaviour (auth, alternate endpoints, manual local refresh).

## Stand-in files for APIs not yet in `/v3/languages`

When a DeepL API needs a supported-languages list in the docs but is not yet exposed as a `/v3/languages` resource, you can hand-write a stand-in file here and the rest of the tooling will treat it like a real response. This is how `translation_memory.json` works today, and the same pattern applies to any future API that has not landed in `/v3/languages` yet.

To add one:

1. Create `data/v3-languages/<api>.json`, where `<api>` is the resource name you expect the API to expose (snake_case, no spaces).
2. Fill it with an array shaped exactly like a real `/v3/languages?resource=<api>` response — each entry needs `lang`, `name`, `status`, `usable_as_source`, `usable_as_target`, and a `features` object (use `{}` if there are no per-language features yet).
3. Commit the file. The snippet generator picks it up on the next run (it walks `data/v3-languages/*.json` and inlines every file it finds), so `<SupportedLanguages resource="<api>" ... />` immediately works in MDX.

You do not need to touch `scripts/fetch_v3_languages.py` or the workflow. The fetcher only writes files it actually fetched, so the manual file is left alone every run.

Once the API does land in `/v3/languages/resources`, the very next refresh will overwrite the stand-in file with the real response and the docs stay in sync — no code change required. When that happens, double-check the fields match (the manual schema was a best guess) and delete this paragraph from the README if there are no remaining stand-ins.

### Current stand-ins

- `translation_memory.json` — Translation Memory languages. Will be replaced automatically once Translation Memory ships as a `/v3/languages` resource.
