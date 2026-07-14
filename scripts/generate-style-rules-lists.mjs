#!/usr/bin/env node
// Regenerates the style-rules language callout on the supported-languages page
// from GET /v3/languages?resource=style_rules.
//
// Usage: node scripts/generate-style-rules-lists.mjs <api-key> [--dry-run]

import { fileURLToPath } from 'node:url';
import { byCode, fetchLanguages, joinList, parseArgs, replaceBlock } from './lib.mjs';

export async function update({ authKey, dryRun = false }) {
  const languages = await fetchLanguages(authKey, 'style_rules');
  const codes = languages
    .filter((l) => l.usable_as_target)
    .sort(byCode)
    .map((l) => `\`${l.lang}\``);

  await replaceBlock(
    'docs/getting-started/supported-languages.mdx',
    'style-rules-languages',
    `  Style rules are supported for the following target languages: ${joinList(codes)}.`,
    { dryRun },
  );
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  await update(parseArgs());
}
