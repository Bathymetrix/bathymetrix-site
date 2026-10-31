# GeoCSV hosting

The read-only Cloudflare Worker serves GeoCSV snapshots from private R2.
`mermaid-publisher` owns snapshot creation, exhaustive scientific validation,
gating, upload, latest activation and archive recording. Follow its
[contract](../../mermaid-publisher/docs/geocsv/contract.md) and
[workflow](../../mermaid-publisher/docs/geocsv/workflow.md).
The [payload schema](../../mermaid-geocsv/docs/format-spec.md) and scientific
APIs belong to the consumer. Hosting never interprets or rewrites scientific data.

## Current service

Testing latest selects P0006/P0045 schema 1.0.0 snapshot
`2026-10-30T18:08:32.316000Z`, compatible with consumer >= 0.27.0.
Production latest is absent. The Worker and browser archive listings are live.
The [publication record](../../mermaid-publisher/docs/geocsv/schema1-testing-publication.md)
identifies accepted artifact hashes and the receipt; other retained snapshots
can use unsupported schemas. A successful download does not establish parser
compatibility. No snapshot retirement is part of documentation maintenance.

| Public service identifier | Value |
| --- | --- |
| Worker | `bathymetrix-geocsv` |
| Route | `bathymetrix.com/geocsv/*` |
| R2 binding | `GEOCSV` |
| Testing collection | `https://bathymetrix.com/geocsv/testing/` |
| Testing key prefix | `geocsv/testing` |
| Production pointer | `/geocsv/latest.json` (inactive) |

The static overview at `/geocsv/` and unrelated pages retain GitHub Pages as
origin. Testing and production have separate pointers, object namespaces and
flag requirements. Testing successes carry `X-MERMAID-Testing: true`.

All hosted data are testing only. Approved distribution is limited to P0006
and P0045; full-corpus licensing remains unresolved. Cite MH network DOI
`10.7914/SN/MH`. Software licensing does not establish a data license.
Scientific acceptance, an available service and testing publication do not
authorize uploads, production activation or a formal release. Further uploads,
deployment and retirement require explicit authorization. Retain exact bytes
until authorized retirement; never reuse a retired identity for different bytes.
Testing pinned links do not promise indefinite availability; production retention
is indefinite. [Evidence records](../../mermaid-publisher/docs/geocsv/evidence.md)
remain bound to their original inputs and software.

## Routes and bytes

The Worker accepts only GET/HEAD. It serves isolated collection-relative
`latest.json`, `latest/<instrument>.geocsv` temporary 302 redirects, and
`releases/<component>/{manifest.json,validation.json,<instrument>.geocsv}`.
Latest and redirect responses bypass caches. Successful immutable objects use
`public, max-age=31536000, immutable, no-transform`; misses and errors are not
cached. `Cache-Control: no-cache` or `no-store` forces a storage read for
verification. HEAD returns object metadata without a body. Payloads are stored
uncompressed, streamed without transformation and served with exact byte counts.

Only the two creation-timestamp time-separator colons become hyphens in paths.
JSON release identities retain the original spelling and fractional digits.
Literal-colon and percent-encoded release components are rejected before cache
lookup. There are no upload/admin routes, schema-dependent rewrites or aliases.

### Browser archive listings

Listings are available at `/geocsv/testing/`, `/geocsv/testing/index.html`,
`/geocsv/testing/releases/` and the separate production `/geocsv/releases/`.
They use paginated read-only R2 listing and manifests; directories without a
manifest are omitted. Identity/path/collection flags must agree or return an
uncached 503. Rows show exact snapshot creation UTC, collection status, latest
selection and pinned manifest/payload links. A report link appears if present.
Creation timestamps are not upload dates. Listings do not parse schemas or
establish acceptance. They use no browser JavaScript and respond `no-store`.
The static preview cannot generate these Worker-owned pages.

## Deployment and access constraints

Use `workers/geocsv/wrangler.example.jsonc` as a portable template. Actual
configuration, approved bucket/account settings, SDK credentials and DNS records
remain in private locations outside checkouts. Resolve an external configuration's
entry point relative to that file or use an absolute path. Keep public bucket
URLs disabled and the Worker binding read-only. The SDK provider owns credentials.
Do not print them or store them in repository files, including ignored files.

Cloudflare is authoritative, DNSSEC is enabled, website TLS uses Full (strict),
and GitHub Pages remains origin. Only the approved website hostnames are proxied;
mail/service records retain their intended routing. The GeoCSV route requires
proxied DNS. Python GET/HEAD clients require the scoped Browser Integrity Check
exception for the collection; do not disable unrelated security controls.
No zone-wide cache rule should override exact-byte, no-store or uncached-error
behavior. Actual DNS inventories and account settings remain private.

Before an authorized deployment, run Worker tests and review the external
configuration, route and binding. After deployment verify static pass-through,
GET/HEAD, testing flags, pointer isolation, immutable exact bytes and uncached
misses using ordinary Python clients. Verify schema compatibility separately
through public fetch/read APIs. A deployment does not authorize data upload.

### Recovery

Inspect live state before retries or activation recovery. A Worker fault can be
isolated by removing its route or reverting website proxying while preserving
GitHub Pages; either is an explicitly authorized infrastructure operation.
DNS-provider rollback requires compatible DNSSEC/DS state and verification of
website, redirects and mail after resolver caches expire. Do not restore an
incompatible DS record. Data rollback changes only a separately authorized latest
pointer after verification; immutable snapshots are never rewritten.

## Verification

From the repository root:

```bash
cd workers/geocsv
node --test test/*.test.js
```

Tests cover streaming, identity encoding, exact bytes, caching, collection
isolation, flags, pointer/manifest consistency, redirects, listings, HEAD and
write rejection. Scientific/publication tests belong to the publisher.
For read-only live checks, request testing latest, fetch its manifest-pinned
payloads, verify hashes and parse with the current consumer. Check production
latest separately. Do not infer deployed behavior from local source alone.

Primary references: [Worker routes](https://developers.cloudflare.com/workers/configuration/routing/routes/),
[Full strict TLS](https://developers.cloudflare.com/ssl/origin-configuration/ssl-modes/full-strict/),
[R2 Worker API](https://developers.cloudflare.com/r2/api/workers/workers-api-reference/) and
[conditional S3 writes](https://developers.cloudflare.com/r2/api/s3/extensions/).
