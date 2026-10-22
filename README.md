# Bathymetrix

Public website for Bathymetrix, a research consultancy specializing in ocean acoustics and global seismology.

## Site

This repository contains a lightweight static website built with plain HTML, CSS, and JavaScript.

Current public pages:

- `index.html`
- `about.html`
- `work.html`
- `contact.html`

## Development

To preview locally, open `index.html` in a browser or run a simple local server:

```bash
python3 -m http.server 8000
```

Then visit `http://localhost:8000`.

## Deployment

The site is intended for simple static hosting, including GitHub Pages.

## GeoCSV download testing

A test-only file collection is prepared under [`data/geocsv/testing/`](data/geocsv/testing/README.md).
It is separate from future scientific data releases.

## GeoCSV production hosting preparation

The planned public collection is `https://bathymetrix.com/geocsv/`. GitHub Pages
serves the website. The planned data service uses R2 for payload storage and a
Worker route for `/geocsv/*`; that infrastructure is not deployed.
See [the implementation and DNS migration runbook](docs/GEOCSV_HOSTING.md) and
[the shared production contract](data/geocsv/testing/CONTRACT.md).

The website owns snapshot creation, full-archive validation, the versioned
acceptance report and publication gate. These tools and Worker routing are
implemented locally. Scientific acceptance requires a successful full archive
run. See [validation and report requirements](docs/GEOCSV_VALIDATION.md).
No production service is activated by these files.
