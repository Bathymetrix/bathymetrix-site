# GeoCSV publication and download agreement

The canonical cross-repository design is `mermaid-geocsv/docs/HOSTING.md`, agreed
2026-10-22 and implemented by the fetch client in 0.24.0. This document adopts
that production protocol for the website. It supersedes the earlier test-only
plan. [Website implementation and deployment status](../../../docs/GEOCSV_HOSTING.md)
records the current scripts, diagram, and remaining launch gates.

## Ownership

The website chat owns staging, hosting, publication, URLs and manifests in
`bathymetrix-site`. The package chat owns fetch, reading, association, SAC export,
and scientific validation in `mermaid-geocsv`. Upstream automaid owns processed
outputs. Coordinate shared URL/manifest/report changes across owners; each chat
edits its own repository. No scientific validation logic is copied into the
website. Keep both hosting diagrams/checklists synchronized through handoffs.

## Production collection and legacy test collection

Production base: **`https://bathymetrix.com/geocsv/`**. GitHub Pages remains the
website origin, Squarespace remains registrar, and a Cloudflare Worker route
serves `/geocsv/*` from R2 after approved DNS/proxy onboarding. This architecture
is prepared locally, not operational. The landing page remains on GitHub Pages.

Relative public paths:

```text
latest.json
latest/<instrument_id>.geocsv
releases/<encoded-release-component>/manifest.json
releases/<encoded-release-component>/<instrument_id>.geocsv
releases/<encoded-release-component>/validation.json
```

`latest/<instrument_id>.geocsv` returns a temporary 302 redirect. Fetch clients
use latest.json once and pin an immutable release, not convenience redirects.
The publisher stores keys under `geocsv/` inside the private R2 bucket.

The existing illustrative test collection remains at
`/data/geocsv/testing/`, with `testing_only: true` and token `test-001`. Its fixture,
manifest, and checksum are unchanged. Serve the website locally at
`http://localhost:8000/data/geocsv/testing/` for integration development. Production
snapshots are not based on the manually edited test example and stay outside Git.

## Literal release identity and encoded paths

Production `release_id` is the exact GeoCSV `#created` value, with grammar
`YYYY-MM-DDTHH:MM:SS[.digits]Z`, a valid calendar date, hours 00–23 and seconds
00–59. There must be exactly one declaration per file and exact spelling agreement
across the complete snapshot. Missing, repeated or mixed declarations raise.
Preserve all fractional digits; do not round or reformat the identity.

Compute `release_component = urllib.parse.quote(release_id, safe="")`:

| Context | Example |
| --- | --- |
| JSON and fetch argument | `2026-10-21T22:48:33.277Z` |
| URL and local staging/download directory | `2026-10-21T22%3A48%3A33.277Z` |
| R2 release-key component | `2026-10-21T22:48:33.277Z` |

Worker lookup decodes the URL release component exactly once. It never decodes
again or stores `%3A` in keys. Do not double-encode `%` as `%25`. Equivalent
instants with different fractional spellings are distinct release IDs. Token IDs
remain supported by the client/Worker for legacy illustrative tests only.

## Exact manifest protocol

Latest pointer:

```json
{
  "release_id": "2026-10-21T22:48:33.277Z",
  "testing_only": false,
  "manifest": "releases/2026-10-21T22%3A48%3A33.277Z/manifest.json"
}
```

The relative manifest path must exactly match its encoded release. No
`release_component` JSON field is needed.

The immutable manifest requires `release_id`, boolean `testing_only`, and a
`files` array. Each entry requires:

| Field | Meaning |
| --- | --- |
| `instrument_id` | Unique nonempty ID, with exact spelling and case |
| `filename` | Unique filename, resolved relative to the manifest URL |
| `size_bytes` | Nonnegative integer count of complete uncompressed file bytes |
| `sha256` | Lowercase 64-hex SHA-256 of those exact bytes, including comments |
| `provenance` | Descriptive object; never interpreted as filesystem instructions |

Production filenames are `{instrument_id}.geocsv`. Website staging accepts IDs
starting with an ASCII letter/digit and otherwise containing only ASCII letters,
digits, `.`, `_`, `-`. Filenames have the same character rule; `manifest.json` is
reserved by the client. The creator uses a reviewed serial-to-ID mapping and
requires all Station values to agree; it does not infer an ID from a serial.

The creator emits entries sorted by ID. Production provenance uses a
processed-root-relative `source_path` (`<serial>/geo_DET_REQ.csv`) and
`manual_edits: false`. Payloads are copied verbatim. Manifests are deterministic;
publication/report times must not cause same-ID manifest regeneration. Optional
descriptive fields are retained by clients, without becoming instructions.
`created_utc` in the legacy test manifest is descriptive, not a release ID.

## Fetch and immutable releases

An explicit literal release ID bypasses latest. Latest is read once per fetch
operation; manifest identity and test flags must agree. A missing release or
instrument raises without fallback. Files are discovered from the manifest,
not HTML scraping or guessed sequential IDs. Downloads are streamed and accepted
only after size/SHA-256 checks. Pin/cache directories by encoded release, and
retain the exact manifest and literal release provenance.

Under an existing release ID, payloads and manifests are immutable. Identical
retries reuse them; differing bytes (including comments) or inventories raise.
Unchanged historical records with updated comments and a new shared timestamp
are valid. Retain prior releases. Large files, full snapshots, inventories, and
validation reports live in an external publication workspace outside Git and
the protected processed tree.

Latest responses and redirects bypass caches. Successful immutable objects are
cached deliberately; misses/errors are not. Downloads honor
`Accept-Encoding: identity` with exact bytes and no transformation. Compression
is outside this protocol; coordinate any change before implementation.

## Scientific publication gate

Freeze the candidate, obtain its full-archive scientific acceptance report,
recheck the complete manifest/inventory/hashes, upload payloads before the
manifest, verify public HTTPS bytes and explicitly pinned `geocsv.fetch`, then
update latest last. Failure leaves the previous latest selected. Serialize
publication and use conditional object writes to prevent conflicting updates.

The package owns `scripts/validate_snapshot.py`, the concrete report format,
and the full local run against original MiniSEED and independently read paired
SAC. Its sampled fixture checker is insufficient. Reports must bind the exact
frozen manifest and complete file inventory, cover every waveform pair, and
record failures, unsupported/unexamined inputs, versions, checks, and limits.
No report schema or passing report is invented here. The publisher currently
rejects all activation attempts until that acceptance protocol is implemented.

An accepted report may be stored as `validation.json` outside the manifest's
GeoCSV files list. It binds the manifest; the manifest never depends on its hash.
Public report provenance is source-relative. Data license and citation remain
owner decisions before publication. No DNS activation, production publication,
commit, or software release is authorized by this document.
