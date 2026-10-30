function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, character => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  })[character]);
}

// Compare the original fractional digits without rounding to milliseconds.
function newestFirst(left, right) {
  const [secondsA, fractionA = ""] = left.release_id.replace(/Z$/, "").split(".");
  const [secondsB, fractionB = ""] = right.release_id.replace(/Z$/, "").split(".");
  const length = Math.max(fractionA.length, fractionB.length);
  const paddedA = secondsA + fractionA.padEnd(length, "0");
  const paddedB = secondsB + fractionB.padEnd(length, "0");
  return paddedA < paddedB ? 1 : paddedA > paddedB ? -1 : 0;
}

export async function archivePage(bucket, root, latest, validRelease, releaseComponent) {
  const testing = root === "/geocsv/testing/";
  const prefix = `${root.slice(1)}releases/`;
  const snapshots = [];
  let cursor;
  do {
    const page = await bucket.list({ prefix, delimiter: "/", ...(cursor ? { cursor } : {}) });
    for (const directory of page.delimitedPrefixes) {
      const object = await bucket.get(`${directory}manifest.json`);
      // Payloads may be uploaded before their manifest, or retired separately.
      if (!object) continue;
      const manifest = JSON.parse(await object.text());
      if (!validRelease(manifest.release_id) || manifest.testing_only !== testing
          || directory !== `${prefix}${releaseComponent(manifest.release_id)}/`
          || !Array.isArray(manifest.files)
          || manifest.files.some(file => !/^[A-Za-z0-9][A-Za-z0-9._-]*\.geocsv$/.test(file.filename))) {
        throw new Error("Invalid archive manifest");
      }
      snapshots.push({ ...manifest, validation: Boolean(await bucket.head(`${directory}validation.json`)) });
    }
    cursor = page.truncated ? page.cursor : undefined;
  } while (cursor);
  snapshots.sort(newestFirst);

  const rows = snapshots.map(snapshot => {
    const base = `${root}releases/${releaseComponent(snapshot.release_id)}/`;
    const timestamp = snapshot.release_id.includes(":")
      ? `<time datetime="${escapeHtml(snapshot.release_id)}">${escapeHtml(snapshot.release_id.replace("T", " ").replace(/Z$/, " UTC"))}</time>`
      : escapeHtml(snapshot.release_id);
    const current = snapshot.release_id === latest?.value.release_id ? ' <span class="archive-badge">Latest</span>' : "";
    const files = snapshot.files.map(file => `<li><a href="${base}${escapeHtml(file.filename)}">${escapeHtml(file.filename)}</a></li>`).join("");
    return `<tr>
      <th scope="row">${timestamp}${current}</th>
      <td>${testing ? "Testing only" : "Production"}</td>
      <td><a href="${base}manifest.json">Manifest</a>${snapshot.validation ? ` · <a href="${base}validation.json">Validation report</a>` : ""}
        <details><summary>${snapshot.files.length} instrument file${snapshot.files.length === 1 ? "" : "s"}</summary><ul>${files}</ul></details></td>
    </tr>`;
  }).join("");
  const title = testing ? "GeoCSV testing archives" : "GeoCSV production archives";
  return `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>${title} | Bathymetrix</title>
  <link rel="icon" href="/favicon.ico?v=2">
  <link rel="stylesheet" href="/css/styles.css">
  <style>
    .archive-page { max-width: 1000px; padding-top: 3rem; padding-bottom: 3rem; }
    .archive-page a { color: var(--accent); text-decoration: underline; text-underline-offset: 0.2em; }
    .archive-nav { display: flex; flex-wrap: wrap; gap: 0.5rem 1.5rem; margin: 1.5rem 0 2rem; }
    .archive-table { overflow-x: auto; }
    table { width: 100%; border-collapse: collapse; text-align: left; }
    caption { text-align: left; padding-bottom: 1rem; color: var(--muted); }
    th, td { padding: 1rem 0.75rem; border-bottom: 1px solid var(--line); vertical-align: top; }
    tbody th { font-weight: 500; min-width: 17rem; overflow-wrap: anywhere; }
    thead { background: var(--surface-2); }
    .archive-badge { display: inline-block; background: var(--accent-soft); color: var(--accent); border-radius: 1rem; padding: 0.1rem 0.6rem; font-size: 0.8rem; }
    details { margin-top: 0.6rem; } summary { cursor: pointer; } details ul { margin-top: 0.5rem; }
    .archive-note { margin-top: 2rem; color: var(--muted); }
    @media (max-width: 640px) {
      table, caption, tbody, tr, th, td { display: block; }
      thead { display: none; }
      tr { padding: 1rem 0; border-bottom: 1px solid var(--line); }
      th, td { padding: 0.3rem 0; border: 0; }
      tbody th { min-width: 0; font-weight: 600; }
      .archive-table { overflow-wrap: anywhere; }
    }
  </style>
</head>
<body>
  <header class="site-header"><div class="header-inner">
    <a class="brand" href="/"><img class="brand-mark" src="/assets/bathymetrix-wordmark.png" alt="Bathymetrix® home"></a>
    <a class="inline-link" href="/geocsv/">GeoCSV overview</a>
  </div></header>
  <main class="container archive-page">
    <h1>${title}</h1>
    <p>${testing ? "Testing snapshots are qualification artifacts and may be retired. They are not production scientific releases." : "Production snapshots are listed separately from testing artifacts."}</p>
    <nav class="archive-nav" aria-label="Archive collections">
      <a href="/geocsv/testing/"${testing ? ' aria-current="page"' : ""}>Testing archives</a>
      <a href="/geocsv/releases/"${testing ? "" : ' aria-current="page"'}>Production archives</a>
    </nav>
    ${snapshots.length ? `<div class="archive-table" role="region" aria-label="Available snapshots" tabindex="0"><table>
      <caption>Available snapshots, newest first. Dates are snapshot creation times, not upload dates.</caption>
      <thead><tr><th scope="col">Snapshot date (UTC)</th><th scope="col">Status</th><th scope="col">Downloads</th></tr></thead>
      <tbody>${rows}</tbody>
    </table></div>` : `<p>No ${testing ? "testing" : "production"} snapshots are currently available.</p>`}
    <p class="archive-note">Downloads are pinned to each snapshot. Older snapshots may use a different GeoCSV schema; consult their file headers before choosing a reader.</p>
    <p class="archive-note">MERMAID MH network citation: <a href="https://doi.org/10.7914/SN/MH">10.7914/SN/MH</a>.</p>
  </main>
</body>
</html>`;
}
