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

export async function archivePage(bucket, root, latest, validRelease, releaseComponent, selectedComponent = null) {
  const testing = root === "/geocsv/testing/";
  const prefix = `${root.slice(1)}releases/`;
  const snapshots = [];
  async function readSnapshot(directory) {
    const object = await bucket.get(`${directory}manifest.json`);
    if (!object) return null;
    const manifest = JSON.parse(await object.text());
    if (!validRelease(manifest.release_id) || manifest.testing_only !== testing
        || directory !== `${prefix}${releaseComponent(manifest.release_id)}/`
        || !Array.isArray(manifest.files)
        || manifest.files.some(file => !/^[A-Za-z0-9][A-Za-z0-9._-]*\.geocsv$/.test(file.filename))) {
      throw new Error("Invalid archive manifest");
    }
    const reportNames = ['comparison.json', ...manifest.files.flatMap(file => {
      const id = file.filename.slice(0, -'.geocsv'.length);
      return [`${id}.mapping.csv`, `${id}.diff`];
    })];
    const reports = [];
    for (const name of reportNames) {
      if (await bucket.head(`${directory}${name}`)) reports.push(name);
    }
    // Include diffs for instruments removed from the new manifest. Listing
    // inventories stored objects; it does not interpret comparison evidence.
    let reportCursor;
    do {
      const page = await bucket.list({ prefix: directory, delimiter: "/",
        ...(reportCursor ? { cursor: reportCursor } : {}) });
      for (const object of page.objects || []) {
        const name = object.key.slice(directory.length);
        if (/^[A-Za-z0-9][A-Za-z0-9._-]*\.(diff|mapping\.csv)$/.test(name)
            && !reports.includes(name)) reports.push(name);
      }
      reportCursor = page.truncated ? page.cursor : undefined;
    } while (reportCursor);
    return { ...manifest, reports, validation: Boolean(await bucket.head(`${directory}validation.json`)),
      bundle: Boolean(await bucket.head(`${directory}MERMAID.geocsv.tar.gz`)) };
  }
  if (selectedComponent !== null) {
    const snapshot = await readSnapshot(`${prefix}${selectedComponent}/`);
    if (!snapshot) return null;
    snapshots.push(snapshot);
  } else {
    let cursor;
    do {
      const page = await bucket.list({ prefix, delimiter: "/", ...(cursor ? { cursor } : {}) });
      for (const directory of page.delimitedPrefixes) {
        const snapshot = await readSnapshot(directory);
        if (snapshot) snapshots.push(snapshot);
      }
      cursor = page.truncated ? page.cursor : undefined;
    } while (cursor);
    snapshots.sort(newestFirst);
  }

  function filenames(snapshot) {
    return [...snapshot.files.map(file => file.filename), "manifest.json", ...snapshot.reports,
      ...(snapshot.validation ? ["validation.json"] : []),
      ...(snapshot.bundle ? ["MERMAID.geocsv.tar.gz"] : [])].sort();
  }
  const directory = selectedComponent !== null ? `${root}releases/${selectedComponent}/` : `${root}releases/`;
  const lines = [`<a href="${selectedComponent !== null ? `${root}releases/` : "/geocsv/"}">../</a>`];
  if (selectedComponent !== null) {
    const files = filenames(snapshots[0]);
    files.forEach((filename, index) => {
      lines.push(`${index === files.length - 1 ? "└──" : "├──"} <a href="${directory}${escapeHtml(filename)}">${escapeHtml(filename)}</a>`);
    });
  } else {
    snapshots.forEach((snapshot, index) => {
      const component = releaseComponent(snapshot.release_id);
      const base = `${root}releases/${component}/`;
      const last = index === snapshots.length - 1;
      const current = snapshot.release_id === latest?.value.release_id ? " (latest)" : "";
      lines.push(`${last ? "└──" : "├──"} <a href="${base}">${escapeHtml(component)}/</a>${current}`);
      const files = filenames(snapshot);
      files.forEach((filename, fileIndex) => {
        lines.push(`${last ? "    " : "│   "}${fileIndex === files.length - 1 ? "└──" : "├──"} <a href="${base}${escapeHtml(filename)}">${escapeHtml(filename)}</a>`);
      });
    });
    if (!snapshots.length) lines.push(`No ${testing ? "testing" : "production"} snapshots are currently available.`);
  }
  return `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Index of ${escapeHtml(directory)}</title>
  <style>body { margin: 2rem; font-family: monospace; } h1 { font-size: 1.2rem; } pre { line-height: 1.5; overflow-x: auto; }</style>
</head>
<body>
  <h1>Index of ${escapeHtml(directory)}</h1>
  <p>${testing ? "Testing only" : "Production"}</p>
  <pre>${lines.join("\n")}</pre>
  <p>MERMAID MH: <a href="https://doi.org/10.7914/SN/MH">10.7914/SN/MH</a></p>
</body>
</html>`;
}
