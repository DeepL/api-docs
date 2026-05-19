# Vended `/v3/languages` responses

This directory holds verbatim JSON responses from the DeepL `/v3/languages` endpoints, fetched against `https://api.deepl.com`. Other tooling in this repo (e.g. generated docs and snippets) reads these files instead of calling the API directly.

## Files

| File | Endpoint |
|---|---|
| `resources.json` | `GET /v3/languages/resources` |
| `translate_text.json` | `GET /v3/languages?resource=translate_text&include=beta&include=external` |
| `translate_document.json` | `GET /v3/languages?resource=translate_document&include=beta&include=external` |
| `voice.json` | `GET /v3/languages?resource=voice&include=beta&include=external` |
| `write.json` | `GET /v3/languages?resource=write&include=beta&include=external` |
| `glossary.json` | `GET /v3/languages?resource=glossary&include=beta&include=external` |
| `style_rules.json` | `GET /v3/languages?resource=style_rules&include=beta&include=external` |

Each per-resource file requests `include=beta&include=external` so the vended data is the full superset. Consumers filter on the `status` and per-feature `external` fields when they want a narrower view.

## Refreshing

Set `DEEPL_AUTH_KEY` in your environment, then run:

```sh
python3 scripts/fetch_v3_languages.py
```

Flags:

- `--free` — hit `https://api-free.deepl.com` instead of the Pro endpoint.
- `--base-url <url>` — point at any other host (staging, mock, local server). Also configurable via the `DEEPL_API_BASE_URL` environment variable.

The script overwrites every file in this directory.

A scheduled GitHub Action refreshes these files automatically and opens a pull request when the responses change; manual runs are only needed for local testing.
