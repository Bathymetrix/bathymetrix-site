# Bathymetrix

Public website and read-only data hosting for Bathymetrix.

## Repository

- **Website:** HTML, CSS and JavaScript served by GitHub Pages.
- **GeoCSV download service (testing only):** Read-only Cloudflare Worker in
  `workers/geocsv/`. Hosting details and current status are documented separately.
  Browser archive listings are served at `/geocsv/testing/` and
  `/geocsv/releases/`, with snapshot dates and pinned download links.

## Local website preview

```bash
python3 -m http.server 8000
```

Open `http://localhost:8000`. This previews the static pages; it does not run
the Worker or publish data.

## Documentation

- [Static-site launch and deployment](LAUNCH.md)
- [GeoCSV hosting, ownership and current status](docs/geocsv-hosting.md)
