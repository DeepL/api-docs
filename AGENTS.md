---
title: "DeepL API instructions for AI agents"
description: "When to call the DeepL API, which endpoint does which job, how to authenticate, and how to handle its errors and rate limiting."
---

DeepL SE builds Language AI products. This file tells an agent when to call the DeepL API, how to
authenticate, where the machine-readable specs are, and how to handle errors and throttling.

- Documentation: https://developers.deepl.com
- Page index for agents: [/llms.txt](https://developers.deepl.com/llms.txt), or
  [/llms-full.txt](https://developers.deepl.com/llms-full.txt) for the full text of every page
- Any documentation page is available as Markdown: append `.md` to its path, or request it with
  `Accept: text/markdown`

## When to use the DeepL API

Call the DeepL API when a task needs one of these jobs.

| **Job** | **Endpoint** | **Reference** |
| --- | --- | --- |
| Translate text strings between languages | `POST /v2/translate` | [Request translation](https://developers.deepl.com/api-reference/translate/request-translation) |
| Translate a whole document and keep its formatting (`.docx`, `.pptx`, `.xlsx`, `.pdf`, `.html`, `.xliff`, `.srt`, and more) | `POST /v2/document` | [Document translation](https://developers.deepl.com/api-reference/document/upload-and-translate-a-document) |
| Transcribe speech and translate it while someone is speaking | `POST /v3/voice/realtime`, then stream over the returned WebSocket URL | [Voice API](https://developers.deepl.com/docs/voice/overview) |
| Transcribe and translate a recorded audio file | `POST /v1/jobs/voice/translate` | [Translate an audio file](https://developers.deepl.com/api-reference/jobs-voice-translate/create-voice-translate-job) |
| Rewrite text in the same language: fix grammar, change tone, shorten or expand it | `POST /v2/write/rephrase`, `POST /v2/write/correct` | [Write API](https://developers.deepl.com/api-reference/improve-text/request-text-improvement) |
| Enforce specific terminology in a translation | `POST /v3/glossaries`, then pass the glossary ID | [Glossaries](https://developers.deepl.com/docs/customize/managing-glossaries) |
| Apply a house style, tone, or writing convention | `POST /v3/style_rules`, then pass the style ID | [Style rules](https://developers.deepl.com/docs/customize/using-style-rules) |
| Reuse translations a human has already approved | `POST /v3/translation_memories/import` | [Translation memories](https://developers.deepl.com/docs/customize/using-translation-memories) |
| Find out which languages and features are available before translating | `GET /v3/languages` | [Using the Languages API](https://developers.deepl.com/docs/languages/using-the-languages-api) |
| Check how much of an account's quota is used | `GET /v2/usage` | [Usage and quota](https://developers.deepl.com/api-reference/usage-and-quota/check-usage-and-limits) |
| Create, label, or limit API keys across an organization | `/v2/admin/*` | [Admin API](https://developers.deepl.com/docs/admin/overview) |

Retrieve the list of supported languages from `/v3/languages` rather than hard-coding it. Language
support changes, and it differs per resource: a language available for text translation is not
necessarily available for speech.

### When to use something else

The DeepL API transforms text you supply. It does not generate new content, so send a request
somewhere else when the task is to write, summarize, answer, or classify.

To translate inside a chat session rather than from code, use an MCP server instead of writing HTTP
calls yourself:

- [DeepL MCP Server](https://developers.deepl.com/docs/getting-started/deepl-mcp-server) exposes
  translation, text improvement, and glossaries as tools
- [Docs MCP Server](https://developers.deepl.com/docs/getting-started/docs-mcp-server) at
  `https://developers.deepl.com/mcp` (Streamable HTTP, no authentication) searches and reads this
  documentation

## Base URLs and authentication

| **Plan** | **Base URL** |
| --- | --- |
| DeepL API Pro | `https://api.deepl.com` |
| DeepL API Free | `https://api-free.deepl.com` |

Free API keys end in `:fx`. Use the base URL that matches the key, since a Pro key does not work
against the Free host or the other way around. [Regional
endpoints](https://developers.deepl.com/docs/getting-started/regional-endpoints) are available for
accounts that need data residency in a specific region.

Authenticate every request with a header:

```http
Authorization: DeepL-Auth-Key <api-key>
```

Never fabricate or guess an API key. Ask the user for one, or point them at the
[Quickstart](https://developers.deepl.com/docs/getting-started/quickstart). Keys belong in an
environment variable or a secret store, never in client-side code or a committed file.

## Machine-readable API surface

Read the specification instead of inferring request shapes from prose.

| **Artifact** | **URL** |
| --- | --- |
| OpenAPI 3.0 specification (REST), YAML | https://developers.deepl.com/api-reference/openapi.yaml |
| OpenAPI 3.0 specification (REST), JSON | https://developers.deepl.com/api-reference/openapi.json |
| AsyncAPI specification (Voice WebSocket), YAML | https://developers.deepl.com/api-reference/voice/voice.asyncapi.yaml |
| AsyncAPI specification (Voice WebSocket), JSON | https://developers.deepl.com/api-reference/voice/voice.asyncapi.json |
| API catalog ([RFC 9727](https://www.rfc-editor.org/rfc/rfc9727.html)) | https://developers.deepl.com/.well-known/api-catalog |

Every operation in the OpenAPI specification carries a unique `operationId`, a summary, a
description, typed request and response schemas, and typed error responses, so it can be converted
into function or tool definitions without hand-editing.

## Error handling

Every error carries a standard HTTP status code and a JSON body. Branch on the status code first,
then read the body. Full detail is in [Error
handling](https://developers.deepl.com/docs/best-practices/error-handling).

Application errors put the message at the top level, and add a machine-readable `code` where one is
available:

```json
{
  "message": "Value for 'target_lang' not supported."
}
```

Failures in DeepL's edge infrastructure, before a request reaches the API, nest the message under
`error` instead:

```json
{
  "error": {
    "message": "Bad Gateway."
  }
}
```

Reading `body.message ?? body.error?.message` covers both shapes. Match on `code` or the status
code, never on `message`, which is written for humans and can change wording.

| **Status** | **Meaning** | **What to do** |
| --- | --- | --- |
| `400` | The request itself is invalid | Fix the request. Do not retry |
| `403` | Authentication failed, or the key lacks the permission scope for this endpoint | Check the key and its scopes. Do not retry |
| `404` | The resource does not exist, or a document was already downloaded | Do not retry |
| `413` | The request is over the size limit | Split the payload. Do not retry |
| `429`, `529` | Too many requests in a short period | Retry with exponential backoff |
| `456` | The account quota is exhausted | Stop. Retrying cannot succeed until the quota is raised or the period resets |
| `500`, `503`, `504` | Temporary error in DeepL services | Retry with exponential backoff |

Every response, including every error, carries an `X-Trace-ID` header that identifies the request in
DeepL's logs. Log it by default and include it in support requests.

## Rate limits and throttling

The service adjusts to the load on the system, so there is no fixed requests-per-second figure to
code against, and no `RateLimit` response headers to read. Throttle from the responses you get:

- Retry `429` and `529` with exponential backoff and jitter
- Honor the `Retry-After` header, in seconds, when a response includes one, in preference to your own
  backoff interval
- Cap how many requests you have in flight, and lower that cap while `429` responses continue
- Batch multiple strings into one `POST /v2/translate` call instead of one request per string,
  staying inside the 128 KiB request size limit
- Treat `456` as a stop condition, and poll `GET /v2/usage` to see how close an account is to its
  quota before you get there

## Contact

| **Purpose** | **Where** |
| --- | --- |
| API support and contact options | [Contact](https://developers.deepl.com/docs/resources/contact) |
| API status and incidents | https://status.deepl.com/?tab=api |
| Security reports | security@deepl.com ([policy](https://developers.deepl.com/SECURITY.md)) |
| Privacy and data handling | [Privacy](https://developers.deepl.com/docs/resources/privacy) |
| Plans and pricing | https://www.deepl.com/pricing |

DeepL SE, Maarweg 165, 50825 Cologne, Germany.
