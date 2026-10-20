# GeoCSV download agreement

This is the shared agreement between the Bathymetrix website and
`mermaid-geocsv` for developing and testing downloads. It describes the existing
`test-001` collection. Production hosting and the public Python fetch API remain
to be established; this is not a production data release.

## Ownership

- The `bathymetrix-site` chat owns hosting, website documentation, release
  publication, URLs, and manifests.
- The `mermaid-geocsv` chat owns the Python fetch API, downloads, local caching,
  and tests.
- URL layout, manifest fields, checksum meaning, and release selection are
  shared decisions, recorded here. Coordinate changes before changing either
  side; each chat edits its own repository.

## URLs

A collection base URL ends with `/`. The current local test base is
`http://localhost:8000/data/geocsv/testing/` when serving the website repository.
The downloader must accept a configurable base URL so local tests and a future
HTTPS endpoint can use the same layout. A production hostname is not configured
by this agreement.

Relative to that base:

```text
latest.json
releases/<release_id>/manifest.json
releases/<release_id>/<filename>
```

The current release ID is `test-001`. Each release has a complete inventory of
its files. Instrument identifiers and filenames retain their declared spelling
and case. Files are discovered from the manifest, not by scraping HTML or
probing sequential instrument numbers.

## JSON fields

`latest.json` contains:

| Field | Meaning |
| --- | --- |
| `release_id` | ID of the complete release selected as latest |
| `testing_only` | Boolean; `true` for this test collection |
| `manifest` | Relative path resolved against the collection base URL |

The release manifest contains:

| Field | Meaning |
| --- | --- |
| `release_id` | Release ID, matching the selected release |
| `testing_only` | Boolean; `true` for this test collection |
| `created_utc` | UTC timestamp when the release manifest was created; not observation coverage or proof of publication |
| `description` | Human-readable collection description |
| `files` | Complete array of available files in the release |

Each file entry contains:

| Field | Meaning |
| --- | --- |
| `instrument_id` | Instrument identifier, such as `P0006` |
| `filename` | Filename resolved relative to the manifest URL |
| `size_bytes` | Integer byte count of the downloaded GeoCSV file |
| `sha256` | Lowercase hexadecimal SHA-256 of those same file bytes |
| `provenance` | Source description retained with the manifest |

Current provenance fields are `source_path`, `manual_edits` (boolean), and
`notes`. The source path is descriptive provenance, not a URL or an instruction
to access the publisher's filesystem. Checksums describe the released test
fixture only. Neither checksums nor copies of earlier source variants are part
of the collection.

## Release selection and verification

For latest selection, fetch `latest.json` once per operation, resolve its
manifest path, and verify the manifest's release ID matches the pointer.
Download all requested files from that manifest's release. Do not reread latest
between files, which could mix releases during a publication update.

For an explicit release ID, request `releases/<release_id>/manifest.json`
directly and verify its release ID. Do not consult latest or silently fall back
to another release when an explicit release is unavailable.

Select instruments from `files`. A missing instrument is an error, not an
invitation to retrieve it from a different release. Verify byte count and
SHA-256 before accepting each download into the local cache or returning it as
successful. Preserve the release ID and manifest alongside downloaded files.
A cache must distinguish releases; an instrument ID alone is insufficient.
Exact Python signatures, return values, and cache locations belong to the
`mermaid-geocsv` chat.

The current endpoint serves plain `.geocsv` files. No compressed-file checksum
semantics are defined here. Coordinate that addition if compression is adopted.

## Publication and testing

A published release ID is immutable. Corrections require a new release ID.
Upload a complete release, verify its files against the manifest, then update
`latest.json`. The latest pointer may change; release files and manifests do not.

Routine Python tests use a local HTTP server and package-local fixtures without
requiring internet access or the website checkout. A public test endpoint is an
optional integration check. Test fixtures are explicitly marked `testing_only`;
production adoption requires agreement on its base URL and release policy.
