// Public, read-only GeoCSV route. R2 keys and URLs use hyphenated release components.
import { archivePage } from "./archives.js";

const ROOT = "/geocsv/";
const NO_CACHE = "no-store, max-age=0";
const IMMUTABLE = "public, max-age=31536000, immutable, no-transform";
const component = /^[A-Za-z0-9][A-Za-z0-9._-]*$/;

export function validRelease(value) {
  if (typeof value !== "string") return false;
  if (component.test(value)) return true; // Existing test-token collection.
  const match = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.\d+)?Z$/.exec(value);
  if (!match) return false;
  const [, y, m, d, h, minute, s] = match.map(Number);
  const leap = y % 4 === 0 && (y % 100 !== 0 || y % 400 === 0);
  const days = [31, leap ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
  return y >= 1 && m >= 1 && m <= 12 && d >= 1 && d <= days[m - 1]
    && h <= 23 && minute <= 59 && s <= 59;
}

function releaseComponent(release) {
  return release.replaceAll(":", "-");
}

function message(text, status, extra = {}) {
  return new Response(text, {
    status, headers: { "Cache-Control": NO_CACHE, "Content-Type": "text/plain; charset=utf-8", ...extra },
  });
}

export function releaseKey(pathname) {
  const match = /^\/geocsv\/(testing\/)?releases\/([^/]+)\/([^/]+)$/.exec(pathname);
  if (!match) return null;
  const release = match[2];
  const filename = match[3];
  if (!component.test(release)) return null;
  if (!component.test(filename)
      || !(filename.endsWith(".geocsv") || ["manifest.json", "validation.json"].includes(filename))) return null;
  return `geocsv/${match[1] || ""}releases/${release}/${filename}`;
}

async function pointer(bucket, root) {
  const object = await bucket.get(`${root.slice(1)}latest.json`);
  if (!object) return null;
  const text = await object.text();
  const value = JSON.parse(text);
  if (!validRelease(value.release_id) || value.testing_only !== (root !== ROOT)
      || value.manifest !== `releases/${releaseComponent(value.release_id)}/manifest.json`) {
    throw new Error("Invalid latest pointer");
  }
  return { value, text };
}

export async function handle(request, env, ctx, dependencies = {}) {
  const originFetch = dependencies.originFetch || fetch;
  const url = new URL(request.url);
  if (!url.pathname.startsWith(ROOT)) return originFetch(request);
  const collectionRoot = url.pathname.startsWith(`${ROOT}testing/`) ? `${ROOT}testing/` : ROOT;
  const testing = collectionRoot !== ROOT;
  const testingHeaders = testing ? { "X-MERMAID-Testing": "true" } : {};
  if (!["GET", "HEAD"].includes(request.method)) return message("Method not allowed", 405, { Allow: "GET, HEAD" });
  if (!testing && [ROOT, `${ROOT}index.html`].includes(url.pathname)) return originFetch(request);
  try {
    if (url.pathname === `${collectionRoot}releases/`
        || (testing && [collectionRoot, `${collectionRoot}index.html`].includes(url.pathname))) {
      const selected = await pointer(env.GEOCSV, collectionRoot);
      const html = await archivePage(env.GEOCSV, collectionRoot, selected, validRelease, releaseComponent);
      return new Response(request.method === "HEAD" ? null : html, {
        headers: { "Content-Type": "text/html; charset=utf-8", "Cache-Control": NO_CACHE, ...testingHeaders },
      });
    }
    if (url.pathname === `${collectionRoot}latest.json`) {
      const selected = await pointer(env.GEOCSV, collectionRoot);
      if (!selected) return message("No release published", 404);
      return new Response(request.method === "HEAD" ? null : selected.text, {
        headers: { "Content-Type": "application/json; charset=utf-8", "Cache-Control": NO_CACHE, ...testingHeaders },
      });
    }
    const latest = /^latest\/([A-Za-z0-9][A-Za-z0-9._-]*\.geocsv)$/.exec(url.pathname.slice(collectionRoot.length));
    if (latest) {
      const selected = await pointer(env.GEOCSV, collectionRoot);
      if (!selected) return message("No release published", 404);
      const filename = latest[1];
      const prefix = `${collectionRoot.slice(1)}releases/${releaseComponent(selected.value.release_id)}/`;
      const manifestObject = await env.GEOCSV.get(`${prefix}manifest.json`);
      if (!manifestObject) return message("Selected manifest unavailable", 503);
      const manifest = JSON.parse(await manifestObject.text());
      if (manifest.release_id !== selected.value.release_id
          || manifest.testing_only !== selected.value.testing_only || !Array.isArray(manifest.files)) {
        return message("Selected manifest inconsistent", 503);
      }
      if (!manifest.files.some(entry => entry.filename === filename)) return message("Instrument not found", 404);
      const location = new URL(`releases/${releaseComponent(selected.value.release_id)}/${filename}`, new URL(collectionRoot, url));
      return new Response(null, { status: 302, headers: { Location: location.href, "Cache-Control": NO_CACHE, ...testingHeaders } });
    }
    const key = releaseKey(url.pathname);
    if (!key) return message("Not found", 404);
    const cache = dependencies.cache || globalThis.caches?.default;
    // Publication checks can explicitly force an R2 read. Never cache misses.
    const bypass = /no-cache|no-store/.test(request.headers.get("Cache-Control") || "");
    const cacheKey = new Request(`${url.origin}${url.pathname}`, { method: "GET" });
    if (request.method === "GET" && cache && !bypass) {
      const cached = await cache.match(cacheKey);
      if (cached) return cached;
    }
    const object = request.method === "HEAD" ? await env.GEOCSV.head(key) : await env.GEOCSV.get(key);
    if (!object) return message("Not found", 404);
    const headers = new Headers();
    object.writeHttpMetadata(headers);
    headers.delete("Content-Encoding"); // Publisher stores uncompressed, exact bytes.
    headers.set("Content-Type", key.endsWith(".json") ? "application/json; charset=utf-8" : "text/csv; charset=utf-8");
    headers.set("Content-Length", String(object.size));
    headers.set("ETag", object.httpEtag);
    headers.set("Cache-Control", IMMUTABLE);
    headers.set("X-Content-Type-Options", "nosniff");
    if (testing) headers.set("X-MERMAID-Testing", "true");
    const response = new Response(request.method === "HEAD" ? null : object.body, { headers, encodeBody: "manual" });
    if (cache && request.method === "GET") ctx.waitUntil(cache.put(cacheKey, response.clone()));
    return response;
  } catch {
    return message("GeoCSV storage unavailable", 503);
  }
}

export default { fetch: handle };
