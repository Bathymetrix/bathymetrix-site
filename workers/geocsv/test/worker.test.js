import assert from "node:assert/strict";
import test from "node:test";
import { handle, releaseKey, validRelease } from "../src/index.js";

const release = "2026-10-21T22:48:33.277000001Z";
const encoded = encodeURIComponent(release);
const prefix = `geocsv/releases/${release}/`;
const payload = "#dataset: GeoCSV\n#created: " + release + "\nStation\nP0006\n";

function setup() {
  const data = new Map([
    ["geocsv/latest.json", JSON.stringify({ release_id: release, testing_only: false, manifest: `releases/${encoded}/manifest.json` })],
    [prefix + "manifest.json", JSON.stringify({ release_id: release, testing_only: false, files: [{ filename: "P0006.geocsv" }] })],
    [prefix + "P0006.geocsv", payload],
  ]);
  const reads = [];
  const object = key => {
    reads.push(key);
    if (!data.has(key)) return null;
    const value = data.get(key);
    return { body: new Blob([value]).stream(), text: async () => value,
      size: Buffer.byteLength(value), httpEtag: '"test-etag"', writeHttpMetadata: () => {} };
  };
  const env = { GEOCSV: { get: async key => object(key), head: async key => object(key) } };
  const entries = new Map();
  const cache = {
    match: async request => entries.get(request.url)?.clone(),
    put: async (request, response) => { entries.set(request.url, response); },
  };
  const pending = [];
  const ctx = { waitUntil: promise => pending.push(promise) };
  const originFetch = async () => new Response("GitHub Pages origin");
  const request = (path, options = {}) => handle(new Request(`https://bathymetrix.com${path}`, options), env, ctx, { cache, originFetch });
  return { data, reads, entries, pending, request };
}

test("timestamp validation preserves fractional spelling and calendar limits", () => {
  for (const id of [release, "test-001", "2024-02-29T00:00:00Z"]) assert.ok(validRelease(id));
  for (const id of [encoded, "2026-02-29T00:00:00Z", "0000-01-01T00:00:00Z", "2026-01-01T24:00:00Z", "2026-01-01T00:00:60Z"]) assert.equal(validRelease(id), false);
});

test("decode timestamp exactly once into literal R2 key", () => {
  assert.equal(releaseKey(`/geocsv/releases/${encoded}/P0006.geocsv`), prefix + "P0006.geocsv");
  assert.equal(releaseKey(`/geocsv/releases/${encodeURIComponent(encoded)}/P0006.geocsv`), null);
  assert.equal(releaseKey(`/geocsv/releases/${release}/P0006.geocsv`), null);
  assert.equal(releaseKey("/geocsv/releases/%ZZ/P0006.geocsv"), null);
  assert.equal(releaseKey(`/geocsv/releases/${encoded}/%2Fsecret`), null);
});

test("stream immutable payload and cache successful bytes", async () => {
  const state = setup();
  const path = `/geocsv/releases/${encoded}/P0006.geocsv`;
  const response = await state.request(path, { headers: { "Accept-Encoding": "identity" } });
  assert.equal(response.status, 200);
  assert.equal(await response.text(), payload);
  assert.match(response.headers.get("Cache-Control"), /immutable.*no-transform/);
  assert.equal(response.headers.get("Content-Encoding"), null);
  await Promise.all(state.pending);
  const readCount = state.reads.length;
  assert.equal(await (await state.request(path)).text(), payload);
  assert.equal(state.reads.length, readCount);
  await state.request(path, { headers: { "Cache-Control": "no-cache" } });
  assert.equal(state.reads.length, readCount + 1);
});

test("no negative caching: publication after a 404 is immediately visible", async () => {
  const state = setup();
  const path = `/geocsv/releases/${encoded}/N0001.geocsv`;
  const missing = await state.request(path);
  assert.equal(missing.status, 404);
  assert.match(missing.headers.get("Cache-Control"), /no-store/);
  assert.equal(state.entries.size, 0);
  state.data.set(prefix + "N0001.geocsv", "new publication");
  assert.equal(await (await state.request(path)).text(), "new publication");
});

test("latest pointer bypasses cache on every read", async () => {
  const state = setup();
  for (let i = 0; i < 2; i++) {
    const response = await state.request("/geocsv/latest.json");
    assert.match(response.headers.get("Cache-Control"), /no-store/);
    assert.equal((await response.json()).release_id, release);
  }
  assert.equal(state.entries.size, 0);
  assert.equal(state.reads.filter(key => key === "geocsv/latest.json").length, 2);
});

test("latest convenience URL is a temporary encoded release redirect", async () => {
  const state = setup();
  const response = await state.request("/geocsv/latest/P0006.geocsv");
  assert.equal(response.status, 302);
  assert.equal(response.headers.get("Location"), `https://bathymetrix.com/geocsv/releases/${encoded}/P0006.geocsv`);
  assert.match(response.headers.get("Cache-Control"), /no-store/);
  assert.equal((await state.request("/geocsv/latest/N0001.geocsv")).status, 404);
});

test("HEAD has content metadata and no body; POST is rejected", async () => {
  const state = setup();
  const response = await state.request(`/geocsv/releases/${encoded}/P0006.geocsv`, { method: "HEAD" });
  assert.equal(response.headers.get("Content-Length"), String(Buffer.byteLength(payload)));
  assert.equal(await response.text(), "");
  assert.equal((await state.request("/geocsv/latest.json", { method: "POST" })).status, 405);
});

test("missing storage, malformed pointer and inconsistent manifest are not cached", async () => {
  const state = setup();
  state.data.delete("geocsv/latest.json");
  assert.equal((await state.request("/geocsv/latest.json")).status, 404);
  state.data.set("geocsv/latest.json", "invalid JSON");
  assert.equal((await state.request("/geocsv/latest.json")).status, 503);
  state.data.set("geocsv/latest.json", JSON.stringify({ release_id: release, testing_only: false, manifest: `releases/${encoded}/manifest.json` }));
  state.data.set(prefix + "manifest.json", JSON.stringify({ release_id: "wrong", testing_only: false, files: [] }));
  assert.equal((await state.request("/geocsv/latest/P0006.geocsv")).status, 503);
  assert.equal(state.entries.size, 0);
});

test("landing and unrelated routes retain GitHub Pages origin", async () => {
  const state = setup();
  for (const path of ["/geocsv/", "/geocsv/index.html", "/about.html"]) {
    assert.equal(await (await state.request(path)).text(), "GitHub Pages origin");
  }
  assert.equal(state.reads.length, 0);
});


test("testing collection uses isolated objects, pointer and redirects", async () => {
  const state = setup();
  const testPrefix = `geocsv/testing/releases/${release}/`;
  state.data.set("geocsv/testing/latest.json", JSON.stringify({ release_id: release, testing_only: true, manifest: `releases/${encoded}/manifest.json` }));
  state.data.set(testPrefix + "manifest.json", JSON.stringify({ release_id: release, testing_only: true, files: [{ filename: "P0006.geocsv" }] }));
  state.data.set(testPrefix + "P0006.geocsv", "testing payload");
  assert.equal(releaseKey(`/geocsv/testing/releases/${encoded}/P0006.geocsv`), testPrefix + "P0006.geocsv");
  const latest = await state.request("/geocsv/testing/latest.json");
  assert.equal((await latest.json()).testing_only, true);
  assert.equal(latest.headers.get("X-MERMAID-Testing"), "true");
  const payloadResponse = await state.request(`/geocsv/testing/releases/${encoded}/P0006.geocsv`);
  assert.equal(await payloadResponse.text(), "testing payload");
  assert.equal(payloadResponse.headers.get("X-MERMAID-Testing"), "true");
  const redirected = await state.request("/geocsv/testing/latest/P0006.geocsv");
  assert.equal(redirected.headers.get("X-MERMAID-Testing"), "true");
  assert.match(redirected.headers.get("Cache-Control"), /no-store/);
  assert.equal(redirected.headers.get("Location"), `https://bathymetrix.com/geocsv/testing/releases/${encoded}/P0006.geocsv`);
  assert.equal((await (await state.request("/geocsv/latest.json")).json()).testing_only, false);
  assert.equal(await (await state.request(`/geocsv/releases/${encoded}/P0006.geocsv`)).text(), payload);
});

test("testing pointer rejects production flags without consulting production objects", async () => {
  const state = setup();
  assert.equal((await state.request("/geocsv/testing/latest.json")).status, 404);
  state.data.set("geocsv/testing/latest.json", state.data.get("geocsv/latest.json"));
  assert.equal((await state.request("/geocsv/testing/latest.json")).status, 503);
  assert.equal((await state.request("/geocsv/testing/latest/P0006.geocsv")).status, 503);
});
