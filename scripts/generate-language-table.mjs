#!/usr/bin/env node
// Regenerates the languageData array in snippets/language-table.jsx from the
// live GET /v3/languages endpoint, so the "Languages supported" docs page
// reflects the API instead of a hand-maintained list.
//
// Usage:
//   node scripts/generate-language-table.mjs <api-key> [--dry-run]
//
// The API key is passed as the first argument; it is not read from the
// environment or from any file. Set DEEPL_SERVER_URL to target a different
// API host (e.g. a local mock).

import { readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { ROOT, fetchLanguages, parseArgs } from './lib.mjs';

const SNIPPET_PATH = path.join(ROOT, 'snippets', 'language-table.jsx');
const BEGIN_MARKER = '// BEGIN GENERATED languageData';
const END_MARKER = '// END GENERATED languageData';

// resource to table column derived from it
const FEATURE_RESOURCES = {
  write: 'textImprovement',
  style_rules: 'styleRules',
  translation_memory: 'translationMemory',
};

// Display names curated for the docs page where the raw API name is ambiguous.
const NAME_OVERRIDES = {
  EN: 'English (all variants)',
  PT: 'Portuguese (unspecified variant)',
  ZH: 'Chinese (unspecified variant)',
  'DE-DE': 'German (Germany)',
  'FR-FR': 'French (France)',
};

// Builds the table rows from the translate_text list plus one feature list per
// FEATURE_RESOURCES entry (in key order), sorted alphabetically by display name.
export function buildRows(translateText, featureLists) {
  const languages = new Map();
  for (const lang of translateText) {
    const code = lang.lang.toUpperCase();
    languages.set(code, {
      code,
      name: NAME_OVERRIDES[code] ?? lang.name,
      translation: true,
      isVariant: !lang.usable_as_source && lang.usable_as_target,
      // early_access also gets the beta badge: the table has no separate concept
      isBeta: lang.status !== 'stable',
      glossaries: 'glossary' in lang.features,
      tagHandling: 'tag_handling' in lang.features,
      textImprovement: false,
      translationMemory: false,
      styleRules: false,
    });
  }

  Object.values(FEATURE_RESOURCES).forEach((column, i) => {
    for (const lang of featureLists[i].filter((l) => l.usable_as_target)) {
      const entry = languages.get(lang.lang.toUpperCase());
      if (!entry) {
        console.warn(`${lang.lang} supports ${column} but is not a translate_text language, skipped`);
        continue;
      }
      entry[column] = true;
    }
  });

  return [...languages.values()].sort((a, b) => a.name.localeCompare(b.name, 'en'));
}

// Single-quoted JS string literal; the API values end up in executable JSX,
// so backslashes and newlines must not be able to break out of the literal.
const quote = (s) => `'${s.replace(/\\/g, '\\\\').replace(/'/g, "\\'").replace(/\r?\n/g, '\\n')}'`;

export function renderRow(l) {
  const beta = l.isBeta ? ' isBeta: true,' : '';
  return (
    `        { code: ${quote(l.code)}, name: ${quote(l.name)}, ` +
    `translation: ${l.translation}, isVariant: ${l.isVariant},${beta} ` +
    `glossaries: ${l.glossaries}, tagHandling: ${l.tagHandling}, ` +
    `textImprovement: ${l.textImprovement}, translationMemory: ${l.translationMemory}, ` +
    `styleRules: ${l.styleRules} },`
  );
}

export async function update({ authKey, dryRun = false }) {
  const snippet = await readFile(SNIPPET_PATH, 'utf8');
  const pattern = new RegExp(`[ \\t]*${BEGIN_MARKER}[\\s\\S]*?${END_MARKER}`);
  if (!pattern.test(snippet)) {
    throw new Error(`Markers not found in ${SNIPPET_PATH}`);
  }

  const [translateText, ...featureLists] = await Promise.all([
    fetchLanguages(authKey, 'translate_text'),
    ...Object.keys(FEATURE_RESOURCES).map((r) => fetchLanguages(authKey, r)),
  ]);

  const sorted = buildRows(translateText, featureLists);
  const generated = `    ${BEGIN_MARKER} (run: node scripts/update-language-docs.mjs)
    const languageData = [
${sorted.map(renderRow).join('\n')}
    ]
    ${END_MARKER}`;

  if (dryRun) {
    console.log(generated);
    return;
  }

  await writeFile(SNIPPET_PATH, snippet.replace(pattern, () => generated));
  console.log(`Updated snippets/language-table.jsx (${sorted.length} languages)`);
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  await update(parseArgs());
}
