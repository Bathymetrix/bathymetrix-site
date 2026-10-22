#!/usr/bin/env python3
"""Preflight and publication machinery. Scientific report acceptance is not yet wired."""

import argparse
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import tempfile
from urllib.parse import quote, urlsplit
from urllib.request import Request, urlopen

from snapshot import fingerprint, json_bytes, require_external_workspace, verify_candidate


class AcceptanceUnavailable(RuntimeError):
    pass


def require_scientific_acceptance(candidate, report):
    """Fail closed until mermaid-geocsv defines its full-archive report protocol.

    Do not accept an arbitrary {"passed": true}, the sampled fixture checker,
    a report from another candidate, or an operator override.
    """
    raise AcceptanceUnavailable(
        "Publication blocked: mermaid-geocsv/scripts/validate_snapshot.py and its "
        "candidate-bound full-archive report format are not yet implemented/agreed. "
        "No reports can currently authorize production publication."
    )


class R2Store:
    """Small S3 transport; credentials are resolved by the SDK, never inspected here."""

    def __init__(self, endpoint_url, bucket):
        import boto3  # Optional deployment dependency; offline staging needs no SDK.
        self.client = boto3.client("s3", endpoint_url=endpoint_url, region_name="auto")
        self.bucket = bucket

    def get(self, key):
        try:
            return self.client.get_object(Bucket=self.bucket, Key=key)
        except self.client.exceptions.ClientError as exc:
            if exc.response["Error"]["Code"] in {"NoSuchKey", "404"}:
                return None
            raise

    def keys(self, prefix):
        paginator = self.client.get_paginator("list_objects_v2")
        return {obj["Key"] for page in paginator.paginate(Bucket=self.bucket, Prefix=prefix)
                for obj in page.get("Contents", [])}

    def put(self, key, path, *, etag=None, immutable=True):
        condition = {"IfNoneMatch": "*"} if immutable or etag is None else {"IfMatch": etag}
        with Path(path).open("rb") as stream:
            self.client.put_object(
                Bucket=self.bucket, Key=key, Body=stream, **condition,
                ContentType="application/json" if key.endswith(".json") else "text/csv; charset=utf-8",
                CacheControl="public, max-age=31536000, immutable, no-transform" if immutable else "no-store",
            )


def remote_fingerprint(response):
    checksum, size = hashlib.sha256(), 0
    with response["Body"] as stream:
        while chunk := stream.read(1024 * 1024):
            checksum.update(chunk)
            size += len(chunk)
    return size, checksum.hexdigest()


def upload_identical_or_new(store, key, path):
    expected = fingerprint(path)
    existing = store.get(key)
    if existing is not None:
        if remote_fingerprint(existing) != expected:
            raise FileExistsError(f"immutable remote object conflicts: {key}")
        return
    # Conditional create prevents overwriting a concurrent upload.
    store.put(key, path)
    if remote_fingerprint(store.get(key)) != expected:
        raise ValueError(f"uploaded bytes differ: {key}")


def verify_https(url, expected):
    request = Request(url, headers={"Accept-Encoding": "identity", "Cache-Control": "no-cache"})
    checksum, size = hashlib.sha256(), 0
    with urlopen(request, timeout=60) as response:
        if response.geturl() != url:
            raise ValueError(f"immutable URL unexpectedly redirected: {url}")
        if response.headers.get("Content-Encoding", "identity").lower() != "identity":
            raise ValueError(f"server transformed exact bytes: {url}")
        while chunk := response.read(1024 * 1024):
            checksum.update(chunk)
            size += len(chunk)
    if (size, checksum.hexdigest()) != expected:
        raise ValueError(f"public HTTPS checksum mismatch: {url}")


def _transfer_and_verify(candidate, report, store, base_url):
    """Publication sequence, reachable from the CLI only after scientific acceptance.

    Kept separate to test ordering and failures with an in-memory transport;
    it is not an alternate publication interface or acceptance override.
    """
    manifest = verify_candidate(candidate)
    candidate = Path(candidate)
    frozen_manifest = (candidate / "manifest.json").read_bytes()
    frozen_report = fingerprint(report)
    release = manifest["release_id"]
    component = quote(release, safe="")
    prefix = f"geocsv/releases/{release}/"
    latest_before = store.get("geocsv/latest.json")
    etag = None
    if latest_before is not None:
        etag = latest_before["ETag"]
        with latest_before["Body"] as stream:
            old = json.load(stream)
        old_id = old["release_id"]
        previous = store.get(f"geocsv/releases/{old_id}/manifest.json")
        if previous is None:
            raise ValueError("current latest manifest is missing")
        with previous["Body"] as stream:
            old_manifest = json.load(stream)
        missing = {entry["instrument_id"] for entry in old_manifest["files"]} - {
            entry["instrument_id"] for entry in manifest["files"]}
        if missing:
            raise ValueError(f"previously published instruments missing: {sorted(missing)}")
    paths = [(entry["filename"], candidate / entry["filename"]) for entry in manifest["files"]]
    paths += [("manifest.json", candidate / "manifest.json"), ("validation.json", Path(report))]
    expected_keys = {prefix + name for name, _ in paths}
    unexpected = store.keys(prefix) - expected_keys
    if unexpected:
        raise FileExistsError(f"conflicting remote inventory: {sorted(unexpected)}")
    # Preflight ALL existing objects before uploading anything.
    for name, path in paths:
        existing = store.get(prefix + name)
        if existing is not None and remote_fingerprint(existing) != fingerprint(path):
            raise FileExistsError(f"immutable remote object conflicts: {prefix + name}")
    for name, path in paths:  # Payloads before manifest, then independent evidence.
        upload_identical_or_new(store, prefix + name, path)
    for name, path in paths:
        verify_https(f"{base_url}releases/{component}/{name}", fingerprint(path))
    from mermaid import geocsv  # Public API, not private scientific logic.
    with tempfile.TemporaryDirectory(prefix="fetch-check-") as output:
        results = geocsv.fetch(base_url=base_url, release=release, output_dir=output)
        if {item.provenance.instrument_id for item in results} != {entry["instrument_id"] for entry in manifest["files"]}:
            raise ValueError("pinned fetch returned a different inventory")
        if any(item.provenance.manifest != (candidate / "manifest.json").read_bytes() for item in results):
            raise ValueError("pinned fetch returned a different manifest")
    # Detect candidate changes during upload/verification before touching latest.
    verify_candidate(candidate)
    if (candidate / "manifest.json").read_bytes() != frozen_manifest or fingerprint(report) != frozen_report:
        raise ValueError("candidate manifest or validation report changed during publication")
    with tempfile.TemporaryDirectory(prefix="latest-") as directory:
        path = Path(directory) / "latest.json"
        path.write_bytes(json_bytes({"release_id": release, "testing_only": False,
                                    "manifest": f"releases/{component}/manifest.json"}))
        # Compare-and-swap: a competing publisher must not be silently overwritten.
        store.put("geocsv/latest.json", path, etag=etag, immutable=False)


@contextmanager
def publication_lock(workspace):
    lock = Path(workspace) / ".geocsv-publication-lock"
    lock.mkdir()  # All operators use one external workspace. Crash leaves a visible lock.
    try:
        yield
    finally:
        lock.rmdir()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--plan", action="store_true", help="verify local candidate and display plan; no network writes")
    parser.add_argument("--base-url", default="https://bathymetrix.com/geocsv/")
    parser.add_argument("--endpoint-url", help="R2 S3 API endpoint; no credentials in arguments")
    parser.add_argument("--bucket")
    args = parser.parse_args()
    try:
        candidate = args.candidate.resolve()
        manifest = verify_candidate(candidate)
        workspace = candidate.parent.parent
        require_external_workspace(workspace, Path(__file__).resolve().parents[2])
        if candidate.parent.name != "snapshots":
            raise ValueError("candidate must be under <external workspace>/snapshots/")
        parsed = urlsplit(args.base_url)
        if parsed.scheme != "https" or not parsed.netloc or parsed.query or parsed.fragment:
            raise ValueError("production verification requires an HTTPS collection base")
        base_url = args.base_url.rstrip("/") + "/"
        if args.plan:
            print(json.dumps({"release_id": manifest["release_id"], "files": len(manifest["files"]),
                              "manifest_sha256": fingerprint(candidate / "manifest.json")[1],
                              "base_url": base_url,
                              "publication": "BLOCKED pending scientific report protocol"}, indent=2))
            return
        with publication_lock(workspace):
            require_scientific_acceptance(candidate, args.report)
            # Deliberately unreachable until the owner-supplied report gate is implemented.
            if not args.endpoint_url or not args.bucket:
                raise ValueError("R2 endpoint and bucket required")
            store = R2Store(args.endpoint_url, args.bucket)
            _transfer_and_verify(candidate, args.report, store, base_url)
    except (ValueError, OSError, RuntimeError) as exc:
        parser.exit(1, f"Not published: {exc}\n")


if __name__ == "__main__":
    main()
