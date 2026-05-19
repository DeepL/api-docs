#!/usr/bin/env python3
"""Fetch v3/languages responses and write them to data/v3-languages/.

Reads DEEPL_AUTH_KEY from the environment. By default uses the Pro
endpoint; pass --free to hit api-free.deepl.com, or --base-url to point
at any other host (e.g. a staging environment or local mock for
testing). The DEEPL_API_BASE_URL environment variable does the same.

The fetcher requests every resource with ?include=beta&include=external so
the vended files contain the full superset of languages and features.
Consumers filter client-side using the status field on languages/features.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

INCLUDES = ("beta", "external")
DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "v3-languages"
PRO_URL = "https://api.deepl.com"
FREE_URL = "https://api-free.deepl.com"


def get(url: str, key: str) -> object:
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"DeepL-Auth-Key {key}",
            "Accept": "application/json",
            "User-Agent": "deepl-api-docs-vendor/1.0",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def fetch(base_url: str, key: str) -> dict[str, object]:
    resources = get(f"{base_url}/v3/languages/resources", key)
    if not isinstance(resources, list):
        raise RuntimeError(f"Unexpected resources payload: {resources!r}")

    out: dict[str, object] = {"resources.json": resources}
    qs = urllib.parse.urlencode([("include", v) for v in INCLUDES], doseq=True)
    for entry in resources:
        name = entry["name"]
        langs = get(f"{base_url}/v3/languages?resource={name}&{qs}", key)
        out[f"{name}.json"] = langs
    return out


def write_files(payloads: dict[str, object], out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for filename, payload in payloads.items():
        path = out_dir / filename
        with path.open("w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False, sort_keys=False)
            f.write("\n")
        written.append(path)
    return written


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
        help=f"Output directory (default: {DATA_DIR})",
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

    paths = write_files(payloads, args.out)
    for p in paths:
        print(p)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
