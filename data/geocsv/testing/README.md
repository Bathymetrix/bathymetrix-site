# Legacy GeoCSV download test collection

This illustrative collection is retained for historical/local testing. Planned
hosting and new public-client checks use `/geocsv/`; this legacy path is outside
the production BIC exception. It is not a published scientific data release.
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
`bathymetrix-site` maintains the publication and download contract.
`mermaid-geocsv` implements and tests the Python client against that contract.

## Local preview

From the website repository, run `python3 -m http.server 8000` and visit
`http://localhost:8000/data/geocsv/testing/`. Use that directory URL as the
fetcher's collection base URL for legacy testing. New hosted-client verification
uses an illustrative release under `/geocsv/` after test hosting is prepared.

Routine package fetch tests serve package-local fixtures through a local HTTP
server and do not require this website checkout or an internet connection. The
fetch client and its tests are implemented in `mermaid-geocsv`. Website integration
tests exercise that client against locally generated timestamp snapshots.
