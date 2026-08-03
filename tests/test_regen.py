#!/usr/bin/env python3
"""The metadata gate: regenerating must not change the catalog.

Copies catalog/ to a temp tree, re-runs every generator that does not need to
re-render or re-convert, and requires byte-identical output. Hand-edit a
generated file without changing the generator that emits it and this fails —
which is the point, because the next build would silently undo the edit.

Two modes, chosen by whether catalog/ is clean relative to git HEAD:

**strict** — catalog/ is unmodified, so regeneration must reproduce the
committed catalog exactly. This is the state when authoring, and it is the gate
that catches a hand-edit or a generator change that was never rebuilt.

**idempotence** — catalog/ is already dirty, which is the normal state in CI:
the data is rebuilt from TriMet's Shapefiles with a different GDAL, zstd and
tippecanoe than produced the committed checksums, and the metadata is re-synced
to match. Byte-identical Parquet across toolchain versions is not something to
expect, so comparing against the committed tree there would only prove GDAL
changed. Regenerating twice and requiring the second run to be a no-op still
catches a non-deterministic generator, which is what CI can meaningfully check.

Not covered: the data files and thumbnails themselves. Those are verified by
checksum in test_catalog.py.

    python3 tests/test_regen.py
"""
import filecmp
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "catalog"

# Generators that read only committed inputs, in dependency order.
GENERATORS = ["tools/make_styles.py", "tools/make_collections.py", "tools/make_docs.py"]

# Regenerated from the manifest; everything else in catalog/ is data or renders.
GENERATED = ("*.json", "*.md")


def snapshot(dst):
    for p in CATALOG.rglob("*"):
        if p.is_file() and any(p.match(g) for g in GENERATED):
            t = dst / p.relative_to(CATALOG)
            t.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, t)


def regenerate():
    for g in GENERATORS:
        r = subprocess.run([sys.executable, g], cwd=ROOT, capture_output=True,
                           text=True)
        if r.returncode != 0:
            print(f"FAIL: {g} exited {r.returncode}\n{r.stderr}")
            sys.exit(1)


def metadata_matches_git():
    """True when catalog/ metadata is unmodified relative to git HEAD.

    Locally that is the normal state and the strong gate applies: regeneration
    must reproduce exactly what is committed. CI rebuilds the Parquet with a
    different GDAL, zstd and tippecanoe than produced the committed checksums —
    byte-identical Parquet across toolchain versions is not something to expect
    — and then re-syncs the metadata, so catalog/ is legitimately dirty there.
    """
    r = subprocess.run(["git", "diff", "--quiet", "HEAD", "--", "catalog"],
                       cwd=ROOT, capture_output=True)
    if r.returncode not in (0, 1):
        return False  # not a git repo, or git unavailable
    return r.returncode == 0


def main():
    strict = metadata_matches_git()
    if strict:
        print("mode: strict — catalog/ is clean, so regeneration must reproduce "
              "the committed tree\n")
    else:
        print("mode: idempotence — catalog/ differs from git HEAD (the data was")
        print("      rebuilt with a different toolchain, so checksums differ).")
        print("      Checking that regeneration is deterministic instead.\n")

    with tempfile.TemporaryDirectory() as tmp:
        before = Path(tmp) / "before"
        snapshot(before)

        regenerate()

        after = Path(tmp) / "after"
        snapshot(after)

        rels = sorted({p.relative_to(before) for p in before.rglob("*") if p.is_file()} |
                      {p.relative_to(after) for p in after.rglob("*") if p.is_file()})
        diffs = []
        for rel in rels:
            a, b = before / rel, after / rel
            if not a.exists():
                diffs.append(f"{rel}: created by regeneration but not committed")
            elif not b.exists():
                diffs.append(f"{rel}: committed but not regenerated")
            elif not filecmp.cmp(a, b, shallow=False):
                diffs.append(f"{rel}: differs after regeneration")

        if diffs:
            print(f"{len(diffs)} file(s) not reproducible:\n")
            for d in diffs:
                print(f"  - {d}")
            if strict:
                print("\nEither the generator changed and catalog/ was not rebuilt,")
                print("or a generated file was hand-edited. Run: python3 tools/build.py")
            else:
                print("\nA generator is not deterministic: running it twice over the")
                print("same inputs produced different output.")
            sys.exit(1)
        how = "byte-identically" if strict else "byte-identically (idempotence only)"
        print(f"ok: {len(rels)} generated files reproduce {how}")


if __name__ == "__main__":
    main()
