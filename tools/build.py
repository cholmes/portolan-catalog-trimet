#!/usr/bin/env python3
"""Run the whole pipeline, in the order the steps depend on each other.

    python3 tools/build.py            # everything except fetching sources
    python3 tools/build.py --fetch    # re-download from TriMet first

Order matters:

1. ``convert``     Shapefile -> GeoParquet + PMTiles
2. ``styles``      MapLibre styles (need the PMTiles layer name, not the data)
3. ``thumbnails``  renders styles/default.json, so styles must exist
4. ``webp``        converts the rendered PNGs under a size budget
5. ``collections`` embeds file sizes and checksums, so all files must be final
6. ``docs``        reads collection.json and the styles, so those must be final

Steps 3 and 4 need Node 20/22/24 (not 23 — MapLibre Native ships no binary for
it) and are skipped with a warning if no usable Node is found, leaving whatever
thumbnails are already on disk in place.
"""
import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NODE_CANDIDATES = ["/opt/homebrew/opt/node@24/bin", "/opt/homebrew/opt/node@22/bin",
                   "/opt/homebrew/opt/node@20/bin"]


def step(name, cmd, **kw):
    print(f"\n=== {name}")
    r = subprocess.run(cmd, cwd=ROOT, **kw)
    if r.returncode != 0:
        sys.exit(f"step '{name}' failed with exit {r.returncode}")


def node_bin():
    """A Node with a prebuilt MapLibre Native binary, or None.

    Node 23 is ABI v131, for which maplibre-gl-native publishes no prebuilt and
    which it refuses to build from source, so the default `node` is checked last
    and only accepted on a supported major.
    """
    for d in NODE_CANDIDATES:
        if (Path(d) / "node").exists():
            return d
    n = shutil.which("node")
    if n:
        out = subprocess.run([n, "--version"], capture_output=True, text=True)
        if int(out.stdout.strip().lstrip("v").split(".")[0]) in (20, 22, 24):
            return str(Path(n).parent)
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fetch", action="store_true", help="re-download TriMet sources first")
    ap.add_argument("--skip-thumbnails", action="store_true")
    args = ap.parse_args()

    if args.fetch:
        step("fetch", [sys.executable, "tools/fetch.py"])

    step("convert", [sys.executable, "tools/convert.py"])
    step("styles", [sys.executable, "tools/make_styles.py"])

    if args.skip_thumbnails:
        print("\n=== thumbnails: skipped by request")
    else:
        nb = node_bin()
        if not nb:
            print("\n=== thumbnails: SKIPPED — no Node 20/22/24 found.")
            print("    Install one (`brew install node@24`); existing thumbnails kept.")
        else:
            import os
            env = dict(os.environ, PATH=f"{nb}:{os.environ['PATH']}")
            step("thumbnails", ["bash", "tools/make_thumbnails.sh"], env=env)
            step("webp", [sys.executable, "tools/to_webp.py"])

    step("collections", [sys.executable, "tools/make_collections.py"])
    step("docs", [sys.executable, "tools/make_docs.py"])

    print("\nBuilt. Verify with:  python3 tests/run_all.py")


if __name__ == "__main__":
    main()
