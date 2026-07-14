// Unit tests for the language-docs generators. Zero dependencies:
//   node --test scripts/*.test.mjs

import assert from 'node:assert/strict';
import { test } from 'node:test';
import { joinList, replaceGeneratedBlock } from './lib.mjs';
import { buildRows, renderRow } from './generate-language-table.mjs';
import { mark } from './generate-voice-languages.mjs';

const lang = (code, name, features = {}, extra = {}) => ({
  lang: code,
  name,
  usable_as_source: true,
  usable_as_target: true,
  status: 'stable',
  features,
  ...extra,
});

test('joinList handles empty, one, two, and many items', () => {
  assert.equal(joinList([]), '');
  assert.equal(joinList(['a']), 'a');
  assert.equal(joinList(['a', 'b']), 'a and b');
  assert.equal(joinList(['a', 'b', 'c']), 'a, b, and c');
  assert.equal(joinList(['a', 'b'], 'or'), 'a or b');
  assert.equal(joinList(['a', 'b', 'c'], 'or'), 'a, b, or c');
});

test('replaceGeneratedBlock swaps content and keeps the markers', () => {
  const source = [
    'before',
    '{/* BEGIN GENERATED my-block (run: x) */}',
    'old content',
    '{/* END GENERATED my-block */}',
    'after',
  ].join('\n');
  const updated = replaceGeneratedBlock(source, 'my-block', 'new content');
  assert.equal(
    updated,
    [
      'before',
      '{/* BEGIN GENERATED my-block (run: x) */}',
      'new content',
      '{/* END GENERATED my-block */}',
      'after',
    ].join('\n'),
  );
});

test('replaceGeneratedBlock does not cross-match prefix ids', () => {
  const source = [
    '{/* BEGIN GENERATED write (run: x) */}',
    'write content',
    '{/* END GENERATED write */}',
    '{/* BEGIN GENERATED write-target (run: x) */}',
    'target content',
    '{/* END GENERATED write-target */}',
  ].join('\n');
  const updated = replaceGeneratedBlock(source, 'write', 'replaced');
  assert.match(updated, /replaced/);
  assert.match(updated, /target content/);
  assert.doesNotMatch(updated, /write content/);
});

test('replaceGeneratedBlock returns null when markers are missing', () => {
  assert.equal(replaceGeneratedBlock('no markers here', 'my-block', 'x'), null);
});

test('replaceGeneratedBlock is idempotent', () => {
  const source = [
    '{/* BEGIN GENERATED b (run: x) */}',
    'old',
    '{/* END GENERATED b */}',
  ].join('\n');
  const once = replaceGeneratedBlock(source, 'b', 'new');
  assert.equal(replaceGeneratedBlock(once, 'b', 'new'), once);
});

test('replaceGeneratedBlock preserves dollar sequences in content', () => {
  const source = ['{/* BEGIN GENERATED b (run: x) */}', 'old', '{/* END GENERATED b */}'].join('\n');
  const updated = replaceGeneratedBlock(source, 'b', "costs $& and $' or $1");
  assert.match(updated, /costs \$& and \$' or \$1/);
});

// buildRows takes one feature list per FEATURE_RESOURCES entry, in key order:
// write, style_rules, translation_memory.
const rows = (translateText, { write = [], styleRules = [], tm = [] } = {}) =>
  buildRows(translateText, [write, styleRules, tm]);

test('buildRows maps API flags to table columns', () => {
  const [de] = rows([lang('de', 'German', { glossary: {}, tag_handling: {} })], {
    write: [lang('de', 'German')],
    tm: [lang('de', 'German')],
  });
  assert.deepEqual(de, {
    code: 'DE',
    name: 'German',
    translation: true,
    isVariant: false,
    isBeta: false,
    glossaries: true,
    tagHandling: true,
    textImprovement: true,
    translationMemory: true,
    styleRules: false,
  });
});

test('buildRows flags target-only languages as variants and non-stable status as beta', () => {
  const result = rows([
    lang('en-GB', 'English (British)', {}, { usable_as_source: false }),
    lang('fr-CA', 'French (Canadian)', {}, { usable_as_source: false, status: 'beta' }),
    lang('fr', 'French'),
    lang('xx', 'Xxish', {}, { status: 'early_access' }),
  ]);
  assert.deepEqual(
    result.map((l) => [l.code, l.isVariant, l.isBeta]),
    [['EN-GB', true, false], ['FR', false, false], ['FR-CA', true, true], ['XX', false, true]],
  );
});

test('buildRows applies display-name overrides and sorts rows by display name', () => {
  const result = rows([lang('pt', 'Portuguese'), lang('en', 'English'), lang('cs', 'Czech')]);
  assert.deepEqual(
    result.map((l) => l.name),
    ['Czech', 'English (all variants)', 'Portuguese (unspecified variant)'],
  );
});

test('buildRows ignores feature entries that are not usable as target', () => {
  const [de] = rows([lang('de', 'German')], {
    write: [lang('de', 'German', {}, { usable_as_target: false })],
  });
  assert.equal(de.textImprovement, false);
});

test('buildRows skips feature languages missing from translate_text', () => {
  const result = rows([lang('de', 'German')], { styleRules: [lang('xx', 'Xxish')] });
  assert.deepEqual(result.map((l) => [l.code, l.styleRules]), [['DE', false]]);
});

test('renderRow emits isBeta only for beta rows and escapes quotes in names', () => {
  const [beta, plain] = rows([
    lang('xx', "X'ish", {}, { status: 'beta' }),
    lang('yy', 'Yish'),
  ]);
  assert.match(renderRow(beta), /name: 'X\\'ish', translation: true, isVariant: false, isBeta: true,/);
  assert.doesNotMatch(renderRow(plain), /isBeta/);
});

test('renderRow cannot be broken out of by backslashes or newlines in API values', () => {
  const [row] = rows([lang('xx', 'Trailing\\', {}, {})]);
  row.name = 'a\\\nb';
  const rendered = renderRow(row);
  assert.match(rendered, /name: 'a\\\\\\nb',/);
  // the emitted line must be a valid JS expression, not a syntax error
  const parsed = new Function(`return [${rendered}]`)();
  assert.equal(parsed[0].name, 'a\\\nb');
});

test('mark maps voice features to matrix symbols', () => {
  assert.equal(mark({ status: 'stable' }), '✓');
  assert.equal(mark({ status: 'beta', external: true }), '⎋');
  assert.equal(mark(undefined), '—');
});
