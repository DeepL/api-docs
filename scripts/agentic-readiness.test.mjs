// Guards for the machine-readable surface of the docs: docs.json configuration, the redirects and
// agent instruction file that agents rely on, and the OpenAPI error contract. Zero dependencies:
//   node --test scripts/*.test.mjs

import assert from 'node:assert/strict';
import { test } from 'node:test';
import { readFileSync, existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const read = (p) => readFileSync(join(root, p), 'utf8');
const readJson = (p) => JSON.parse(read(p));

const docs = readJson('docs.json');
const agentsMd = read('AGENTS.md');
const openapi = readJson('api-reference/openapi.json');
const openapiYaml = read('api-reference/openapi.yaml');

// Top-level properties accepted by https://mintlify.com/docs.json. The schema sets
// additionalProperties: false, so anything outside this list is silently dropped at build time
// rather than reported as an error. A "head" key used to sit here and never reached the page.
const MINTLIFY_TOP_LEVEL_KEYS = new Set([
  '$schema', 'api', 'appearance', 'background', 'banner', 'colors', 'contextual', 'description',
  'errors', 'favicon', 'fonts', 'footer', 'icons', 'integrations', 'interaction', 'logo',
  'markdown', 'metadata', 'name', 'navbar', 'navigation', 'public', 'redirects', 'search', 'seo',
  'styling', 'theme', 'thumbnails', 'variables', 'variations',
]);

// Fields accepted under seo.organization, which is the only structured-data hook Mintlify exposes.
const MINTLIFY_ORGANIZATION_KEYS = new Set(['id', 'name', 'legalName', 'url', 'logo', 'sameAs']);

const navigationPages = (() => {
  const pages = new Set();
  const walk = (node, key) => {
    if (typeof node === 'string') {
      if (key === 'pages') pages.add(node);
    } else if (Array.isArray(node)) node.forEach((child) => walk(child, key));
    else if (node && typeof node === 'object') {
      for (const [k, v] of Object.entries(node)) walk(v, k);
    }
  };
  walk(docs.navigation);
  return pages;
})();

// Routes Mintlify generates rather than files in this repo, plus wildcard redirect patterns.
const isGeneratedRoute = (target) =>
  target.includes(':page*')
  || /^(llms\.txt|llms-full\.txt|mcp|sitemap\.xml)$/.test(target)
  || target.startsWith('.well-known/')
  || target.endsWith('rss.xml');

const resolves = (destination) => {
  const target = destination.split('#')[0].replace(/^\//, '');
  return isGeneratedRoute(target)
    || navigationPages.has(target)
    || existsSync(join(root, `${target}.mdx`))
    || existsSync(join(root, target));
};

test('docs.json uses only properties Mintlify recognizes', () => {
  const unknown = Object.keys(docs).filter((k) => !MINTLIFY_TOP_LEVEL_KEYS.has(k));
  assert.deepEqual(unknown, [], `unknown docs.json keys are ignored at build time: ${unknown}`);

  const unknownOrg = Object.keys(docs.seo.organization)
    .filter((k) => !MINTLIFY_ORGANIZATION_KEYS.has(k));
  assert.deepEqual(unknownOrg, [], `unknown seo.organization keys: ${unknownOrg}`);
});

test('every page in the navigation exists', () => {
  const missing = [...navigationPages].filter((p) => !existsSync(join(root, `${p}.mdx`)));
  assert.deepEqual(missing, []);
});

test('the page every auth error links to is in the navigation', () => {
  // DeepL API 403 bodies point at /docs/getting-started/auth. With seo.indexing "navigable", a page
  // outside the navigation is left out of the sitemap and llms.txt, so agents cannot discover it.
  assert.ok(navigationPages.has('docs/getting-started/auth'));
});

test('redirect sources are unique and destinations resolve', () => {
  const sources = docs.redirects.map((r) => r.source);
  assert.equal(new Set(sources).size, sources.length, 'duplicate redirect source');

  for (const { source, destination } of docs.redirects) {
    assert.ok(source.startsWith('/'), `${source} must be rooted`);
    if (destination.startsWith('http')) {
      assert.ok(destination.startsWith('https://'), `${source} must redirect over https`);
      continue;
    }
    assert.ok(destination.startsWith('/'), `${source} -> ${destination} must be rooted`);
    assert.ok(resolves(destination), `${source} -> ${destination} has no target`);
  }
});

test('no redirect points at another redirect', () => {
  // A chain costs an extra hop, and agents that follow a single Location header land on a 3xx.
  const bySource = new Map(docs.redirects.map((r) => [r.source, r.destination]));
  const chains = docs.redirects
    .filter((r) => bySource.has(r.destination))
    .map((r) => `${r.source} -> ${r.destination} -> ${bySource.get(r.destination)}`);
  assert.deepEqual(chains, []);
});

test('/pricing redirects to the DeepL pricing page', () => {
  const pricing = docs.redirects.find((r) => r.source === '/pricing');
  assert.ok(pricing, '/pricing redirect is missing');
  assert.equal(pricing.destination, 'https://www.deepl.com/pricing');
});

test('agent-facing shortcuts avoid file extensions', () => {
  // Mintlify routes any path with a file extension as an asset and never applies redirects to it,
  // so a shortcut like /openapi.json cannot work. Extension-less sources can.
  for (const source of ['/openapi', '/asyncapi', '/agents']) {
    const redirect = docs.redirects.find((r) => r.source === source);
    assert.ok(redirect, `${source} redirect is missing`);
    assert.ok(!/\.[a-z0-9]+$/i.test(redirect.source), `${source} would be routed as an asset`);
  }
});

test('markdown instructions tell agents when to use the API and where to read more', () => {
  const instructions = docs.markdown.instructions.join('\n');
  assert.match(instructions, /Use the DeepL API when/);
  assert.match(instructions, /Do not use the DeepL API to/);
  assert.match(instructions, /developers\.deepl\.com\/AGENTS\.md/);
  assert.match(instructions, /api-reference\/openapi\.yaml/);
  assert.match(instructions, /DeepL-Auth-Key/);
});

test('AGENTS.md names its best-fit jobs and how to call the API', () => {
  assert.match(agentsMd, /^## When to use the DeepL API$/m);
  assert.match(agentsMd, /^### When to use something else$/m);
  assert.match(agentsMd, /^## Base URLs and authentication$/m);
  assert.match(agentsMd, /^## Machine-readable API surface$/m);
  assert.match(agentsMd, /^## Error handling$/m);
  assert.match(agentsMd, /^## Rate limits and throttling$/m);
  assert.match(agentsMd, /Authorization: DeepL-Auth-Key/);
});

test('AGENTS.md links point at pages and files that exist', () => {
  const links = [...agentsMd.matchAll(/https:\/\/developers\.deepl\.com(\/[^\s)>]*)/g)]
    .map((m) => m[1].replace(/[.,`]+$/, ''));
  assert.ok(links.length > 10, 'expected AGENTS.md to link into the docs');
  for (const link of links) {
    assert.ok(resolves(link), `AGENTS.md links to ${link}, which does not exist`);
  }
});

test('every OpenAPI operation is usable as a tool definition', () => {
  const seen = new Map();
  for (const [path, item] of Object.entries(openapi.paths)) {
    for (const [method, op] of Object.entries(item)) {
      if (!['get', 'post', 'put', 'patch', 'delete'].includes(method)) continue;
      const where = `${method.toUpperCase()} ${path}`;
      assert.ok(op.operationId, `${where} has no operationId`);
      assert.ok(!seen.has(op.operationId), `duplicate operationId ${op.operationId}`);
      seen.set(op.operationId, where);
      assert.ok(op.summary, `${where} has no summary`);
      assert.ok(op.description, `${where} has no description`);
      const errors = Object.keys(op.responses ?? {}).filter((c) => /^[45]/.test(c));
      assert.ok(errors.length > 0, `${where} documents no error responses`);
    }
  }
});

test('error responses document their JSON body and trace header', () => {
  const responses = openapi.components.responses;
  const headers = openapi.components.headers;
  assert.ok(headers['X-Trace-ID'], 'X-Trace-ID header component is missing');
  assert.ok(headers['Retry-After'], 'Retry-After header component is missing');

  for (const [name, response] of Object.entries(responses)) {
    assert.ok(
      response.content?.['application/json']?.schema,
      `${name} does not document a JSON body; agents cannot parse an HTML error page`,
    );
    assert.equal(
      response.headers?.['X-Trace-ID']?.$ref,
      '#/components/headers/X-Trace-ID',
      `${name} does not document X-Trace-ID`,
    );
  }

  assert.equal(
    responses.TooManyRequests.headers['Retry-After'].$ref,
    '#/components/headers/Retry-After',
    'the rate-limit response must document Retry-After so agents can self-throttle',
  );
});

test('every 429 and 529 uses the response that documents Retry-After', () => {
  const rateLimited = [];
  for (const [path, item] of Object.entries(openapi.paths)) {
    for (const [method, op] of Object.entries(item)) {
      if (!['get', 'post', 'put', 'patch', 'delete'].includes(method)) continue;
      for (const code of ['429', '529']) {
        const response = op.responses?.[code];
        if (response) rateLimited.push([`${method.toUpperCase()} ${path} ${code}`, response.$ref]);
      }
    }
  }
  assert.ok(rateLimited.length > 0, 'expected rate-limit responses in the spec');
  for (const [where, ref] of rateLimited) {
    assert.match(ref ?? '', /#\/components\/responses\/(TooManyRequests|QuotaExceeded)/, where);
  }
});

test('openapi.json is regenerated from openapi.yaml', () => {
  // openapi.json is generated (see .github/workflows/update_openapi_json.yml), so header wiring
  // added to the YAML has to be present in both files.
  const count = (text, needle) => text.split(needle).length - 1;
  for (const header of ['X-Trace-ID', 'Retry-After']) {
    assert.equal(
      count(openapiYaml, `#/components/headers/${header}'`),
      count(read('api-reference/openapi.json'), `#/components/headers/${header}"`),
      `${header} references differ between openapi.yaml and openapi.json`,
    );
  }
});
