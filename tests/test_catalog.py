#!/usr/bin/env python3
"""Structural checks on the generated catalog.

Covers the Portolan core requirements that are checkable without a validator:
every relative link and asset href resolves to a file that is actually there,
required fields are present, checksums match the bytes on disk, and the
documentation does not contradict the metadata.

`rashid` is the authority on conformance; this is the fast gate that catches the
common breakages before you get there.

    python3 tests/test_catalog.py
"""
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "catalog"
sys.path.insert(0, str(ROOT / "tools"))
import manifest as M  # noqa: E402

failures = []


def check(cond, msg):
    if not cond:
        failures.append(msg)
    return cond


def load(p):
    return json.loads(p.read_text())


def resolve(base, href):
    """Relative hrefs resolve against the file's own directory."""
    return (base.parent / href).resolve()


def check_object(path, obj, is_root):
    rel = path.relative_to(ROOT)

    check(M.PORTOLAN_SCHEMA in obj.get("stac_extensions", []),
          f"{rel}: missing Portolan schema URI in stac_extensions")
    check(obj.get("title"), f"{rel}: missing title")
    check(obj.get("description") or obj.get("type") == "Catalog",
          f"{rel}: missing description")
    check("self" not in {l.get("rel") for l in obj.get("links", [])},
          f"{rel}: must not carry a self link")

    rels = {l.get("rel") for l in obj.get("links", [])}
    check("root" in rels, f"{rel}: missing root link")
    if not is_root:
        check("parent" in rels, f"{rel}: missing parent link")
    check("describedby" in rels, f"{rel}: missing describedby link to README.md")
    check("agents" in rels, f"{rel}: missing agents link to AGENTS.md")

    for link in obj.get("links", []):
        href = link.get("href", "")
        check(link.get("type"), f"{rel}: link {href} has no type")
        if href.startswith("http"):
            continue
        target = resolve(path, href)
        check(target.exists(), f"{rel}: link {href} does not resolve ({target})")
        if link["rel"] in ("child", "item"):
            check(link.get("title"), f"{rel}: {link['rel']} link {href} has no title")

    for name, a in obj.get("assets", {}).items():
        href = a.get("href", "")
        check(a.get("type"), f"{rel}: asset {name} has no type")
        check(a.get("roles"), f"{rel}: asset {name} has no roles")
        if href.startswith("http"):
            check(href.startswith("https"), f"{rel}: asset {name} href is not https")
            continue
        target = resolve(path, href)
        if not check(target.exists(), f"{rel}: asset {name} href {href} missing"):
            continue
        if "file:size" in a:
            check(a["file:size"] == target.stat().st_size,
                  f"{rel}: asset {name} file:size stale")
        if "file:checksum" in a:
            digest = "1220" + hashlib.sha256(target.read_bytes()).hexdigest()
            check(a["file:checksum"] == digest,
                  f"{rel}: asset {name} file:checksum stale")
            check(a["file:checksum"].startswith("1220"),
                  f"{rel}: asset {name} checksum is not multihash-encoded")


def check_collection(path):
    obj = load(path)
    check_object(path, obj, is_root=False)
    rel = path.relative_to(ROOT)

    check(obj.get("license"), f"{rel}: missing license")
    if obj.get("license") == "other":
        rels = [l for l in obj["links"] if l.get("rel") == "license"]
        check(rels, f"{rel}: license 'other' requires a rel=license link")
    check(obj.get("license") != "proprietary",
          f"{rel}: deprecated license value 'proprietary'")

    provs = obj.get("providers", [])
    roles = [r for p in provs for r in p.get("roles", [])]
    check("producer" in roles, f"{rel}: no provider with role producer")
    check(roles.count("host") == 1, f"{rel}: must have exactly one host provider")
    check(provs and "host" in provs[-1].get("roles", []),
          f"{rel}: host provider must be last")
    host = next((p for p in provs if "host" in p.get("roles", [])), {})
    check(host.get("url") or host.get("email"),
          f"{rel}: host provider needs a url or email")

    # A mirror must say where the data came from and when it last synced.
    check(any(l.get("rel") == "via" for l in obj["links"]),
          f"{rel}: mirror requires a via link")
    check(obj.get("updated"), f"{rel}: mirror requires an updated timestamp")

    bbox = obj["extent"]["spatial"]["bbox"][0]
    w, s, e, n = bbox[:4]
    check(-180 <= w <= 180 and -180 <= e <= 180, f"{rel}: bbox longitude out of range")
    check(-90 <= s <= 90 and -90 <= n <= 90, f"{rel}: bbox latitude out of range")
    check(s <= n, f"{rel}: bbox south > north")
    check(all(v == v and abs(v) < 1e30 for v in bbox), f"{rel}: bbox has NaN/inf")

    # Visualization: PMTiles must be registered as a web-map-links link with a
    # non-empty layer list, and at least one style asset must exist.
    pm = [l for l in obj["links"] if l.get("rel") == "pmtiles"]
    check(pm, f"{rel}: missing rel=pmtiles link")
    if pm:
        check(pm[0].get("pmtiles:layers"), f"{rel}: pmtiles:layers is empty")
    styles = [n for n, a in obj["assets"].items() if "style" in a.get("roles", [])]
    check(styles, f"{rel}: no asset with role 'style'")
    check("thumbnail" in obj["assets"], f"{rel}: no thumbnail asset")

    # The first style asset should be the default, per the spec's SHOULD.
    ordered = [n for n, a in obj["assets"].items() if "style" in a.get("roles", [])]
    check(ordered[0] == "style" if ordered else False,
          f"{rel}: default style is not listed first")


def check_docs():
    """Documentation must not contradict the metadata it describes."""
    for coll in M.COLLECTIONS:
        d = CATALOG / coll["id"]
        for fn in ("README.md", "AGENTS.md"):
            p = d / fn
            if not check(p.exists(), f"{coll['id']}: missing {fn}"):
                continue
            text = p.read_text()
            # Every local link in the docs must resolve.
            for href in re.findall(r"\]\((\./[^)]+)\)", text):
                target = (d / href[2:]).resolve()
                check(target.exists(), f"{coll['id']}/{fn}: link {href} does not resolve")
        # Feature counts stated in the manifest must match the parquet.
        import pyarrow.parquet as pq
        rows = pq.ParquetFile(d / f"{coll['id']}.parquet").metadata.num_rows
        check(rows == coll["count"],
              f"{coll['id']}: manifest count {coll['count']} != {rows} rows in parquet")


def main():
    root = CATALOG / "catalog.json"
    if not root.exists():
        sys.exit("catalog/catalog.json not found — run tools/build.py")
    check_object(root, load(root), is_root=True)

    children = [l for l in load(root)["links"] if l.get("rel") == "child"]
    check(len(children) == len(M.COLLECTIONS),
          f"catalog.json: {len(children)} child links for {len(M.COLLECTIONS)} collections")

    for coll in M.COLLECTIONS:
        p = CATALOG / coll["id"] / "collection.json"
        if check(p.exists(), f"{coll['id']}: missing collection.json"):
            check_collection(p)

    for fn in ("README.md", "AGENTS.md"):
        check((CATALOG / fn).exists(), f"catalog: missing {fn}")
    check_docs()

    if failures:
        print(f"{len(failures)} problem(s):\n")
        for f in failures:
            print(f"  - {f}")
        sys.exit(1)
    n = len(M.COLLECTIONS)
    print(f"ok: root catalog + {n} collections, all links, assets, checksums and docs check out")


if __name__ == "__main__":
    main()
