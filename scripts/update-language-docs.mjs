#!/usr/bin/env node
// Updates every generated language list in the docs from GET /v3/languages.
// Each target also has its own script for running individually:
//   generate-language-table.mjs       the table on docs/getting-started/supported-languages
//   generate-voice-languages.mjs      Voice API matrix and input/target lists
//   generate-style-rules-lists.mjs    style-rules language mentions
//
// Usage: node scripts/update-language-docs.mjs <api-key> [--dry-run]

import { parseArgs } from './lib.mjs';
import { update as languageTable } from './generate-language-table.mjs';
import { update as voiceLanguages } from './generate-voice-languages.mjs';
import { update as styleRulesLists } from './generate-style-rules-lists.mjs';

const args = parseArgs();
try {
  await languageTable(args);
  await voiceLanguages(args);
  await styleRulesLists(args);
} catch (err) {
  console.error(err.message);
  console.error('Aborted mid-run: earlier targets may already be rewritten. Revert with `git checkout -- .` and retry.');
  process.exit(1);
}
console.log('All language docs updated.');
