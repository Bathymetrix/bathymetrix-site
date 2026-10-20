# GeoCSV download test collection

Download testing only—example collection, not a published scientific data release.
This directory prepares a static HTTPS endpoint; adding files locally does not
publish them or configure R2, DNS, or a data subdomain.

`releases/test-001/P0006.geocsv` introduces the first GeoCSV download test
fixture. A byte-identical fixture lives in
`mermaid-geocsv/tests/fixtures/geocsv/P0006.geocsv`. Both copies are tracked in
their respective repositories; neither requires Git LFS.

Source provenance: `$MERMAID/processed/452.020-P-06/geo_DET_REQ.csv`, renamed to
`P0006.geocsv` with three comment lines removed. The attribution comment records
this edit; data records are retained. The manifest records provenance, size,
and SHA-256 for the test fixture.

## Provisional test layout

- Fetch `latest.json` once per operation and retain its `release_id`.
- Resolve its `manifest` relative to the collection base URL.
- Resolve each manifest file's `filename` relative to the manifest URL.
- Verify each downloaded file's `size_bytes` and SHA-256 checksum.
- Keep the release ID and manifest with downloaded files.

These JSON structures are provisional for fetcher development. They are not yet
a production API. Treat a published test release as immutable; use `test-002`
for subsequent changes and update `latest.json` only after uploads are verified.

## Local preview

From the website repository, run `python3 -m http.server 8000` and visit
`http://localhost:8000/data/geocsv/testing/`. Use that directory URL as the
fetcher's collection base URL. A future deployed test uses the same relative
layout, with a configurable base URL.

Routine automated fetch tests should serve the Python package's local fixture
through a local HTTP server and must not require this website checkout or an
internet connection. The fetcher and its tests remain to be implemented.
