#!/usr/bin/env node
// Regenerates the Voice API language tables from GET /v3/languages?resource=voice:
// the support matrix in docs/voice/supported-voice-languages.mdx and
// the input/target lists in api-reference/voice/deepl-voice-api-service-specification-updates.mdx.
//
// Usage: node scripts/generate-voice-languages.mjs <api-key> [--dry-run]

import { fileURLToPath } from 'node:url';
import { byCode, byName, fetchLanguages, parseArgs, replaceBlock } from './lib.mjs';

// feature values are objects like { status, external? }; presence means the
// capability exists, external: true means an external partner provides it
export const mark = (feature) => (feature ? (feature.external ? '⎋' : '✓') : '—');

export async function update({ authKey, dryRun = false }) {
  const languages = await fetchLanguages(authKey, 'voice');
  const sources = languages.filter((l) => l.usable_as_source);
  const targets = languages.filter((l) => l.usable_as_target);

  const languagesByCode = new Map(languages.map((language) => [language.lang, language]));

  const rows = languages
    // Skip the row for a base language if variants are available
    .filter((l) => l.lang.includes('-') || !languages.some((f) => f.lang.startsWith(`${l.lang}-`)))
    .sort(byName)
    .map((l) => {
      const isVariant = l.lang.includes('-');
      const baseCode = l.lang.split('-')[0];
      const base = languagesByCode.get(baseCode);

      if (isVariant && !base) {
        console.warn(`voice variant ${l.lang} has no base language (${baseCode})`);
      }

      // Transcription for variants is determined by base language
      const transcription = isVariant ? base?.features?.transcription : l.features.transcription;
      const name = l.status !== 'stable' ? `${l.name} <Badge color="blue">beta</Badge>` : l.name;

      return `| ${name} | ${mark(transcription)} | ✓ | ${mark(l.features.translated_speech)} |`;
    });
  const matrix = [
    '| **Language** | **Transcription** | **Translation** | **Translated Speech** |',
    '| :--- | :---: | :---: | :---: |',
    ...rows,
  ].join('\n');
  await replaceBlock('docs/voice/supported-voice-languages.mdx', 'voice-language-matrix', matrix, { dryRun });

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
