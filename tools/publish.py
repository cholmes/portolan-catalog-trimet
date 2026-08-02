#!/usr/bin/env python3
"""Sync catalog/ to the remote bucket, 1:1.

``catalog/`` *is* the published catalog: everything in it is published, nothing
outside it ever is. Config lives in ``catalog.publish.yaml``.

    python3 tools/publish.py            # dry run — show what would change
    python3 tools/publish.py --confirm  # upload (needs AWS credentials)
    python3 tools/publish.py --confirm --force   # re-upload everything

Change detection compares local size and MD5 against the object's size and
ETag, so a normal publish uploads only what changed. Two caveats, inherited from
what a bucket listing can tell you:

- A listing carries no Content-Type, so a file whose bytes are unchanged but
  whose content-type mapping changed is skipped. Run ``--force`` after editing
  CONTENT_TYPES.
- Multipart-uploaded objects have a compound ETag that is not an MD5. Those are
  compared on size alone; at this catalog's file sizes nothing is multipart.

**It never deletes.** Removing a file from catalog/ does not unpublish it.
"""
import argparse
import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "catalog"

CONTENT_TYPES = {
    ".json": "application/json",
    ".parquet": "application/vnd.apache.parquet",
    ".pmtiles": "application/vnd.pmtiles",
    ".md": "text/markdown; charset=utf-8",
    ".webp": "image/webp",
    ".png": "image/png",
    ".xml": "application/xml",
    ".txt": "text/plain; charset=utf-8",
}

# MapLibre style files are .json but carry a more specific type.
STYLE_SUFFIX = "application/vnd.mapbox.style+json"


def content_type(path):
    if path.parent.name == "styles" and path.suffix == ".json":
        return STYLE_SUFFIX
    return CONTENT_TYPES.get(path.suffix, "application/octet-stream")


def load_config():
    cfg = ROOT / "catalog.publish.yaml"
    if not cfg.exists():
        sys.exit("catalog.publish.yaml not found")
    out = {}
    for line in cfg.read_text().splitlines():
        line = line.split("#", 1)[0].strip()
        if ":" in line:
            k, v = line.split(":", 1)
            out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def local_files():
    for p in sorted(CATALOG.rglob("*")):
        if not p.is_file():
            continue
        # Portolan's internal bookkeeping is not part of the published tree.
        if any(part == ".portolan" for part in p.parts):
            continue
        if p.name.startswith("."):
            continue
        yield p


def md5(path):
    h = hashlib.md5()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def remote_index(s3, bucket, prefix):
    """List the prefix once and index by key. Returns {} if listing fails, in
    which case every file is treated as changed and a dry run still works."""
    index = {}
    try:
        paginator = s3.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
            for obj in page.get("Contents", []):
                index[obj["Key"]] = (obj["Size"], obj["ETag"].strip('"'))
    except Exception as e:  # noqa: BLE001
        print(f"warning: could not list s3://{bucket}/{prefix} ({e});")
        print("         treating every file as changed")
        return None
    return index


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--confirm", action="store_true", help="actually upload")
    ap.add_argument("--force", action="store_true", help="upload even if unchanged")
    args = ap.parse_args()

    cfg = load_config()
    bucket, prefix = cfg["bucket"], cfg["prefix"].strip("/") + "/"

    files = list(local_files())
    if not files:
        sys.exit("nothing in catalog/ to publish")

    index = None
    if not args.force:
        try:
            import boto3
            index = remote_index(boto3.client("s3"), bucket, prefix)
        except ImportError:
            print("warning: boto3 not installed; cannot compare against remote")

    changed, skipped, total_bytes = [], 0, 0
    for p in files:
        key = prefix + str(p.relative_to(CATALOG))
        if index is not None and key in index:
            size, etag = index[key]
            same = size == p.stat().st_size and ("-" in etag or etag == md5(p))
            if same and not args.force:
                skipped += 1
                continue
        changed.append((p, key))
        total_bytes += p.stat().st_size

    print(f"catalog/ has {len(files)} files")
    print(f"  unchanged, skipping: {skipped}")
    print(f"  to upload:           {len(changed)}  ({total_bytes / 1e6:.1f} MB)")
    print(f"  destination:         s3://{bucket}/{prefix}")

    if not changed:
        print("\nNothing to do.")
        return

    if not args.confirm:
        for p, key in changed[:40]:
            print(f"    {p.relative_to(CATALOG)}  ->  {content_type(p)}")
        if len(changed) > 40:
            print(f"    ... and {len(changed) - 40} more")
        print("\nDry run. Re-run with --confirm to upload.")
        return

    import boto3
    s3 = boto3.client("s3")
    for i, (p, key) in enumerate(changed, 1):
        s3.upload_file(str(p), bucket, key,
                       ExtraArgs={"ContentType": content_type(p)})
        print(f"  [{i}/{len(changed)}] {p.relative_to(CATALOG)}")
    print(f"\nUploaded {len(changed)} files to s3://{bucket}/{prefix}")
    print(f"Public: {cfg.get('public_base', '')}")


if __name__ == "__main__":
    main()
