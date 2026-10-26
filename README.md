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

All hosted data remain **testing only**. The initial P0006/P0045 snapshot was
published on 2026-10-26 through the isolated `/geocsv/testing/` service. Exact
HTTPS bytes, cache behavior, conditional-write rejection, and the complete
fetch/read/associate/write_sac workflow passed; all 3,292 original waveform pairs
passed again using hosted downloads. The testing artifacts may be retired
through authorized cleanup. Production activation and a first formal release
remain unauthorized. The landing page publishes the scope, MH network citation
and retirement notice. DNSSEC was restored on 2026-10-26; independent validation,
HTTPS/download checks and email sending/receiving passed.

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
