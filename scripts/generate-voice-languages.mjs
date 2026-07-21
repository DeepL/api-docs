#!/usr/bin/env node
// Regenerates the Voice API language tables from GET /v3/languages?resource=voice:
// the support matrix in docs/voice/supported-languages-formats-and-limits.mdx and
// the input/target lists in api-reference/voice/deepl-voice-api-service-specification-updates.mdx.
//
// Usage: node scripts/generate-voice-languages.mjs <api-key> [--dry-run]

import { fileURLToPath } from 'node:url';
import { byCode, byName, fetchLanguages, parseArgs, replaceBlock } from './lib.mjs';

// The matrix folds target-only variants into their base language's row.
const MATRIX_NAME_OVERRIDES = {
  en: 'English (American/British)',
  pt: 'Portuguese (Brazil/Portugal)',
  zh: 'Chinese (Simplified/Traditional)',
};

// feature values are objects like { status, external? }; presence means the
// capability exists, external: true means an external partner provides it
export const mark = (feature) => (feature ? (feature.external ? '⎋' : '✓') : '—');

export async function update({ authKey, dryRun = false }) {
  const languages = await fetchLanguages(authKey, 'voice');
  const sources = languages.filter((l) => l.usable_as_source);
  const targets = languages.filter((l) => l.usable_as_target);

  // The matrix only shows source languages (variants fold into the base row),
  // so a target-only language without a source base would silently vanish.
  const sourceBases = new Set(sources.map((l) => l.lang.split('-')[0]));
  for (const t of targets.filter((t) => !sourceBases.has(t.lang.split('-')[0]))) {
    console.warn(`voice target ${t.lang} has no source base language and is missing from the matrix`);
  }

  const rows = sources
    .map((l) => ({ ...l, name: MATRIX_NAME_OVERRIDES[l.lang] ?? l.name }))
    .sort(byName)
    .map((l) => {
      const name = l.status !== 'stable' ? `${l.name} <Badge color="blue">beta</Badge>` : l.name;
      return `| ${name} | ${mark(l.features.transcription)} | ✓ | ${mark(l.features.translated_speech)} |`;
    });
  const matrix = [
    '| **Language** | **Transcription** | **Translation** | Translated Speech |',
    '| :--- | :---: | :---: | :---: |',
    ...rows,
  ].join('\n');
  await replaceBlock('docs/voice/supported-languages-formats-and-limits.mdx', 'voice-language-matrix', matrix, { dryRun });

  const item = (l) => `                <li>\`${l.lang}\` (${l.name})</li>`;
  await replaceBlock(
    'api-reference/voice/deepl-voice-api-service-specification-updates.mdx',
    'voice-input-languages',
    sources.sort(byCode).map(item).join('\n'),
    { dryRun },
  );
  await replaceBlock(
    'api-reference/voice/deepl-voice-api-service-specification-updates.mdx',
    'voice-target-languages',
    targets.sort(byCode).map(item).join('\n'),
    { dryRun },
  );
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  await update(parseArgs());
}
