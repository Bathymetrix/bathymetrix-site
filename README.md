# Bathymetrix

Public website and GeoCSV data publication tooling for Bathymetrix.

## Repository

- **Website:** HTML, CSS and JavaScript served by GitHub Pages.
- **Snapshot workflow:** Python tools in `scripts/geocsv/` create immutable
  snapshots, validate the full waveform archive and require scientific
  acceptance before publication.
- **Download service:** Cloudflare Worker code in `workers/geocsv/` streams
  releases from R2 and serves the latest-release pointer.
- **Legacy test fixtures:** small illustrative files retained in
  [`data/geocsv/testing/`](data/geocsv/testing/README.md).

Production payloads, validation reports and operational configuration remain
outside Git. Scientific parsing, association and SAC export use `mermaid-geocsv`.

## GeoCSV status

- Planned collection: `https://bathymetrix.com/geocsv/`.
- Creation, validation, acceptance and publication tools are implemented locally.
- The initial full-archive run passed all 43,365 waveform pairs and the acceptance
  gate; see [archive findings](docs/GEOCSV_ARCHIVE_FINDINGS.md).
- Cloudflare DNS onboarding and website proxy/TLS setup are complete; public
  website HTTPS, redirects and email checks passed. Automated-client access and
  DNSSEC restoration remain pending; DNSSEC is disabled.
- Data licensing/citation, R2/Worker deployment and live download verification
  remain pending. The production download service is not deployed.

## Local website preview

```bash
python3 -m http.server 8000
```

Open `http://localhost:8000`. This previews the static pages and test collection;
it does not run the Worker or publish data.

## Technical documentation

- [Hosting architecture, workflow, tests and deployment](docs/GEOCSV_HOSTING.md)
- [Scientific validation and acceptance report](docs/GEOCSV_VALIDATION.md)
- [Publication and download contract](data/geocsv/testing/CONTRACT.md)
