# Bathymetrix

Public website and read-only data hosting for Bathymetrix.

## Repository

- **Website:** HTML, CSS and JavaScript served by GitHub Pages.
- **Download service:** Cloudflare Worker in `workers/geocsv/` streams R2 objects,
  serves collection pointers and handles temporary latest redirects.

[mermaid-publisher](../mermaid-publisher/README.md) owns snapshot creation,
scientific validation, gating, upload and activation. Its local Git archive is
separate from this checkout. Scientific APIs remain in `mermaid-geocsv`.

## GeoCSV status

All hosted data remain **testing only**. The isolated `/geocsv/testing/` Worker
was deployed on 2026-10-23; read-only SDK/HTTPS checks passed and no data have
been uploaded. Initial testing is limited to P0006/P0045 and its artifacts may
be retired through authorized cleanup. Production `/geocsv/` activation and
first release remain unauthorized. The testing scope, MH network citation and
initial-artifact retirement notice are published on the landing page. Live transfer/download checks and DNSSEC restoration remain pending. DNS authority,
website proxy/TLS, email and scoped automated-client access passed on 2026-10-22.

## Local website preview

```bash
python3 -m http.server 8000
```

Open `http://localhost:8000`. This previews the static pages; it does not run
the Worker or publish data.

## Technical documentation

- [Hosting architecture and deployment](docs/GEOCSV_HOSTING.md)
- [Publisher workflow](../mermaid-publisher/docs/geocsv/WORKFLOW.md)
- [Publication/download contract](../mermaid-publisher/docs/geocsv/CONTRACT.md)
- [Scientific report and historical findings](../mermaid-publisher/docs/geocsv/VALIDATION.md)
