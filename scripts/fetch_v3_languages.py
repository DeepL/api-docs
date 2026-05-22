#!/usr/bin/env python3
"""Fetch /v3/languages responses and refresh the vended copies in this repo.

What this script does, in order:

1. Calls `GET /v3/languages/resources` and, for every resource, calls
   `GET /v3/languages?resource=<name>&include=beta&include=external`.
2. Writes each response verbatim to `data/v3-languages/<name>.json`
   (plus `resources.json`). These files are the single source of truth
   that the rest of the repo reads.
3. Regenerates the inline `RESOURCES` object in
   `snippets/supported-languages.jsx` between its `// BEGIN GENERATED` /
   `// END GENERATED` markers so the `<SupportedLanguages>` snippet
   stays in sync with the vended JSON. Mintlify's snippet sandbox does
   not honour ES module imports, so the data has to ship inline.

Auth and endpoint:

  - Reads `DEEPL_AUTH_KEY` from the environment (required).
  - Defaults to the Pro endpoint (`https://api.deepl.com`).
  - `--free` switches to `https://api-free.deepl.com`.
  - `--base-url <url>` (or `DEEPL_API_BASE_URL`) points at any other host,
    e.g. a staging environment or a local mock for testing. `--base-url`
    and `--free` are mutually exclusive.

Other flags:

  - `--out <dir>` overrides the JSON output directory (defaults to
    `data/v3-languages/` relative to this repo).
  - `--no-snippet` skips step 3 when you only want to refresh the JSON.

The hourly `refresh-v3-languages` GitHub Action runs this script and
opens a pull request whenever the responses change. Manual runs are
only needed for local testing or after editing the script itself.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

INCLUDES = ("beta", "external")
REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data" / "v3-languages"
SNIPPET = REPO_ROOT / "snippets" / "supported-languages.jsx"
PRO_URL = "https://api.deepl.com"
FREE_URL = "https://api-free.deepl.com"
BEGIN_MARKER = "    // BEGIN GENERATED: RESOURCES (do not edit; run scripts/fetch_v3_languages.py)"
END_MARKER = "    // END GENERATED"

# Retry config for transient failures (429s, 5xx, network errors).
MAX_RETRIES = 5
INITIAL_BACKOFF_S = 1.0
RETRYABLE_STATUSES = frozenset({429, 500, 502, 503, 504})

def _retry_delay(attempt: int, retry_after: str | None) -> float:
    """Honour Retry-After (seconds) when present; otherwise exponential backoff."""
    if retry_after:
        try:
            return max(0.0, float(retry_after))
        except ValueError:
            # HTTP-date form is rare; fall through to backoff.
            pass
    return INITIAL_BACKOFF_S * (2 ** attempt)


def http_get_json(url: str, key: str) -> object:
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"DeepL-Auth-Key {key}",
            "Accept": "application/json",
            "User-Agent": "deepl-api-docs-vendor/1.0",
        },
    )
    for attempt in range(MAX_RETRIES + 1):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            if e.code in RETRYABLE_STATUSES and attempt < MAX_RETRIES:
                delay = _retry_delay(attempt, e.headers.get("Retry-After"))
                print(
                    f"retry {attempt + 1}/{MAX_RETRIES}: {e.code} {e.reason} from {url} "
                    f"(sleeping {delay:.1f}s)",
                    file=sys.stderr,
                )
                time.sleep(delay)
                continue
            raise
        except urllib.error.URLError as e:
            # Network-level failure (connection reset, DNS, timeout, etc.).
            if attempt < MAX_RETRIES:
                delay = _retry_delay(attempt, None)
                print(
                    f"retry {attempt + 1}/{MAX_RETRIES}: network error {e.reason} "
                    f"from {url} (sleeping {delay:.1f}s)",
                    file=sys.stderr,
                )
                time.sleep(delay)
                continue
            raise
    # Unreachable: loop either returns or raises.
    raise RuntimeError("retry loop exited unexpectedly")


def _require_str(value: object, path: str) -> str:
    if not isinstance(value, str) or not value:
        raise RuntimeError(f"unexpected schema at {path}: want non-empty string, got {value!r}")
    return value


def _validate_resources(resources: object) -> list[dict]:
    if not isinstance(resources, list):
        raise RuntimeError(f"unexpected /v3/languages/resources payload: want list, got {type(resources).__name__}")
    validated: list[dict] = []
    for i, entry in enumerate(resources):
        if not isinstance(entry, dict):
            raise RuntimeError(f"unexpected schema at resources[{i}]: want object, got {type(entry).__name__}")
        _require_str(entry.get("name"), f"resources[{i}].name")
        validated.append(entry)
    return validated


def _validate_languages(payload: object, resource: str) -> list[dict]:
    if not isinstance(payload, list):
        raise RuntimeError(
            f"unexpected /v3/languages?resource={resource} payload: "
            f"want list, got {type(payload).__name__}"
        )
    for i, entry in enumerate(payload):
        if not isinstance(entry, dict):
            raise RuntimeError(
                f"unexpected schema at {resource}[{i}]: want object, got {type(entry).__name__}"
            )
        _require_str(entry.get("lang"), f"{resource}[{i}].lang")
        _require_str(entry.get("name"), f"{resource}[{i}].name")
    return payload


def fetch(base_url: str, key: str) -> dict[str, object]:
    resources = _validate_resources(
        http_get_json(f"{base_url}/v3/languages/resources", key)
    )

    payloads: dict[str, object] = {"resources.json": resources}
    qs = urllib.parse.urlencode([("include", v) for v in INCLUDES], doseq=True)
    for entry in resources:
        name = entry["name"]
        langs = _validate_languages(
            http_get_json(f"{base_url}/v3/languages?resource={name}&{qs}", key),
            name,
        )
        payloads[f"{name}.json"] = langs
    return payloads


def write_json_files(payloads: dict[str, object], out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for filename, payload in payloads.items():
        path = out_dir / filename
        with path.open("w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
            f.write("\n")
        written.append(path)
    return written


def render_resources_block(data_dir: Path) -> str:
    """Build the `const RESOURCES = {...}` literal from every per-resource
    JSON file in `data_dir`. `resources.json` (the index) is skipped; every
    other `*.json` file is treated as a resource response, including manual
    files like `translation_memory.json`.
    """
    lines = [BEGIN_MARKER, "    const RESOURCES = {"]
    for path in sorted(data_dir.glob("*.json")):
        if path.stem == "resources":
            continue
        entries = json.loads(path.read_text(encoding="utf-8"))
        lines.append(f'        {json.dumps(path.stem)}: [')
        for entry in entries:
            lines.append(f"            {json.dumps(entry, ensure_ascii=False)},")
        lines.append("        ],")
    lines.append("    }")
    lines.append(END_MARKER)
    return "\n".join(lines)


def update_snippet(data_dir: Path) -> bool:
    if not SNIPPET.exists():
        raise SystemExit(f"error: snippet not found at {SNIPPET}")
    text = SNIPPET.read_text(encoding="utf-8")
    if BEGIN_MARKER not in text or END_MARKER not in text:
        raise SystemExit(
            f"error: {SNIPPET} is missing the BEGIN/END GENERATED markers"
        )
    new_block = render_resources_block(data_dir)
    start = text.index(BEGIN_MARKER)
    end = text.index(END_MARKER, start) + len(END_MARKER)
    updated = text[:start] + new_block + text[end:]
    if updated == text:
        return False
    SNIPPET.write_text(updated, encoding="utf-8")
    return True


def resolve_base_url(cli_base_url: str | None, free: bool) -> str:
    if cli_base_url and free:
        raise SystemExit("error: --base-url and --free are mutually exclusive")
    if cli_base_url:
        return cli_base_url.rstrip("/")
    env_url = os.environ.get("DEEPL_API_BASE_URL")
    if env_url:
        return env_url.rstrip("/")
    return FREE_URL if free else PRO_URL


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base-url",
        help=(
            "API base URL to fetch from (e.g. https://api.example.test). "
            "Overrides --free and the DEEPL_API_BASE_URL env var. "
            f"Defaults to {PRO_URL}, or {FREE_URL} with --free."
        ),
    )
    parser.add_argument(
        "--free",
        action="store_true",
        help=f"Use {FREE_URL} instead of {PRO_URL}",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=DATA_DIR,
        help=f"Output directory for the vended JSON (default: {DATA_DIR})",
    )
    parser.add_argument(
        "--no-snippet",
        action="store_true",
        help="Skip regenerating snippets/supported-languages.jsx",
    )
    args = parser.parse_args()

    key = os.environ.get("DEEPL_AUTH_KEY")
    if not key:
        print("error: DEEPL_AUTH_KEY is not set", file=sys.stderr)
        return 2

    base_url = resolve_base_url(args.base_url, args.free)
    try:
        payloads = fetch(base_url, key)
    except urllib.error.HTTPError as e:
        print(f"error: {e.code} {e.reason} from {e.url}", file=sys.stderr)
        return 1

    paths = write_json_files(payloads, args.out)
    for p in paths:
        print(p)

    if not args.no_snippet:
        if update_snippet(args.out):
            print(SNIPPET)
        else:
            print(f"{SNIPPET}: up to date")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
