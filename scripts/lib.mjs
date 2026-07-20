// Shared helpers for the generate-*-languages scripts.
// See update-language-docs.mjs for the entry point that runs all of them.

import { readFile, writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

export const ROOT = path.join(path.dirname(fileURLToPath(import.meta.url)), '..');

export function parseArgs() {
  const args = process.argv.slice(2);
  const authKey = args.find((a) => !a.startsWith('--'));
  const unknownFlags = args.filter((a) => a.startsWith('--') && a !== '--dry-run');
  if (!authKey || unknownFlags.length > 0) {
    if (unknownFlags.length > 0) console.error(`Unknown flag: ${unknownFlags.join(', ')}`);
    console.error(`Usage: node ${path.relative(process.cwd(), process.argv[1])} <api-key> [--dry-run]`);
    process.exit(1);
  }
  return { authKey, dryRun: args.includes('--dry-run') };
}

export async function fetchLanguages(authKey, resource) {
  const baseUrl =
    process.env.DEEPL_SERVER_URL ??
    (authKey.endsWith(':fx') ? 'https://api-free.deepl.com' : 'https://api.deepl.com');
  const url = `${baseUrl}/v3/languages?resource=${resource}&include=beta&include=external`;
  const res = await fetch(url, {
    headers: { Authorization: `DeepL-Auth-Key ${authKey}` },
    signal: AbortSignal.timeout(30_000),
  });
  if (!res.ok) {
    throw new Error(`GET ${url} failed: ${res.status} ${await res.text()}`);
  }
  return res.json();
}

const escapeRegExp = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

// Pure core of replaceBlock: swaps the lines between {/* BEGIN GENERATED <id> ... */}
// and {/* END GENERATED <id> */}, keeping the markers. Returns null if the
// markers are missing. The space after the id in both markers keeps prefix ids
// (e.g. "write" vs "write-target") from matching each other's blocks.
export function replaceGeneratedBlock(source, id, content) {
  const escaped = escapeRegExp(id);
  const pattern = new RegExp(
    `(\\{/\\* BEGIN GENERATED ${escaped} [^}]*\\*/\\})[\\s\\S]*?(\\{/\\* END GENERATED ${escaped} \\*/\\})`,
  );
  if (!pattern.test(source)) return null;
  return source.replace(pattern, (_, begin, end) => `${begin}\n${content}\n${end}`);
}

export async function replaceBlock(relPath, id, content, { dryRun = false } = {}) {
  const filePath = path.join(ROOT, relPath);
  const source = await readFile(filePath, 'utf8');
  const updated = replaceGeneratedBlock(source, id, content);
  if (updated === null) {
    throw new Error(`Markers for "${id}" not found in ${relPath}`);
  }
  if (dryRun) {
    console.log(`--- ${relPath} [${id}] ---`);
    console.log(content);
    return;
  }
  await writeFile(filePath, updated);
  console.log(`Updated ${relPath} [${id}]`);
}

// Sort helper: alphabetical by English name, stable for identical names.
export const byName = (a, b) => a.name.localeCompare(b.name, 'en') || a.lang.localeCompare(b.lang, 'en');

// Sort helper: alphabetical by language code.
export const byCode = (a, b) => a.lang.localeCompare(b.lang, 'en');

// Joins items grammatically: "a", "a and b", "a, b, and c".
export function joinList(items, conjunction = 'and') {
  if (items.length <= 1) return items[0] ?? '';
  if (items.length === 2) return `${items[0]} ${conjunction} ${items[1]}`;
  return `${items.slice(0, -1).join(', ')}, ${conjunction} ${items.at(-1)}`;
}
