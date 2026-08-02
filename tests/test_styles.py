#!/usr/bin/env python3
"""Validate every generated MapLibre style against the real style spec.

An invalid style is not a cosmetic problem: MapLibre GL JS and GL Native both
reject the whole document, so the layer silently does not draw. This caught a
real bug once already — `["zoom"]` nested inside another expression, which the
spec allows only as the direct input of a top-level `step`/`interpolate`.

Validation uses `@maplibre/maplibre-gl-style-spec`, which ships inside the
chiitiler checkout used for thumbnails. SKIPs when that is not installed, so a
fresh clone still runs the suite.

    python3 tests/test_styles.py
"""
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "catalog"
CHIITILER = Path(os.environ.get("CHIITILER_DIR", "/tmp/chiitiler"))
SPEC = CHIITILER / "node_modules" / "@maplibre" / "maplibre-gl-style-spec"

# The Node that can load the spec package. Homebrew's node@24 is keg-only.
NODE_CANDIDATES = ["/opt/homebrew/opt/node@24/bin/node",
                   "/opt/homebrew/opt/node@22/bin/node",
                   shutil.which("node") or ""]

VALIDATOR = """
const {validateStyleMin} = require(process.argv[2]);
const fs = require('fs');
let bad = 0;
for (const f of process.argv.slice(3)) {
  const errs = validateStyleMin(JSON.parse(fs.readFileSync(f, 'utf8')));
  if (errs.length) {
    bad++;
    console.log('FAIL ' + f);
    for (const e of errs) console.log('     ' + e.message);
  } else {
    console.log('ok   ' + f);
  }
}
process.exit(bad ? 1 : 0);
"""


def pick_node():
    for n in NODE_CANDIDATES:
        if n and Path(n).exists():
            out = subprocess.run([n, "--version"], capture_output=True, text=True)
            major = int(out.stdout.strip().lstrip("v").split(".")[0])
            # The spec package itself is pure JS, so any modern Node will do.
            if major >= 18:
                return n
    return None


def main():
    styles = sorted(
        p for p in CATALOG.glob("*/styles/*.json")
        # Mirrored TriMet source styles are theirs, not ours to conform.
        if not p.name.startswith("trimet-")
    )
    if not styles:
        sys.exit("no styles found")

    if not SPEC.exists():
        print(f"SKIP: {SPEC} not installed "
              f"(run tools/make_thumbnails.sh once, or set CHIITILER_DIR)")
        return
    node = pick_node()
    if not node:
        print("SKIP: no Node 18+ found")
        return

    with tempfile.NamedTemporaryFile("w", suffix=".cjs", delete=False) as f:
        f.write(VALIDATOR)
        script = f.name
    try:
        proc = subprocess.run(
            [node, script, str(SPEC)] + [str(p) for p in styles],
            capture_output=True, text=True)
        print(proc.stdout.strip())
        if proc.stderr.strip():
            print(proc.stderr.strip(), file=sys.stderr)
        n = len(styles)
        bad = proc.stdout.count("FAIL ")
        print(f"\n{n - bad}/{n} styles valid")
        sys.exit(proc.returncode)
    finally:
        os.unlink(script)


if __name__ == "__main__":
    main()
