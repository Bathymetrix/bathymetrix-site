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
serves the website, R2 stores payloads, and a Worker route serves `/geocsv/*`.
See [the implementation and DNS migration runbook](docs/GEOCSV_HOSTING.md) and
[the shared production contract](data/geocsv/testing/CONTRACT.md).

Snapshot staging and Worker routing are implemented locally. The publisher's
scientific acceptance gate remains closed pending the package-owned full-archive
validator/report protocol. No production service is activated by these files.
