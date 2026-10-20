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

## Shared download agreement

See [the download agreement](CONTRACT.md) for the shared URL layout, manifest
fields, checksum definitions, release selection, and repository ownership.
The website chat maintains this agreement; the `mermaid-geocsv` chat implements
and tests the Python client against it.

## Local preview

From the website repository, run `python3 -m http.server 8000` and visit
`http://localhost:8000/data/geocsv/testing/`. Use that directory URL as the
fetcher's collection base URL. A future deployed test uses the same relative
layout, with a configurable base URL.

Routine automated fetch tests should serve the Python package's local fixture
through a local HTTP server and must not require this website checkout or an
internet connection. The fetcher and its tests remain to be implemented.
