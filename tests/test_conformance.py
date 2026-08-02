#!/usr/bin/env python3
"""Portolan conformance, via rashid. Only documented deviations may fail.

Conformance means passing the validator, not claiming to conform, so this runs
the real thing. Findings whose rule id is in ACCEPTED are tolerated; anything
else fails the build. **ACCEPTED must never grow without an entry in
docs/conformance.md explaining why.**

SKIPs when rashid is not installed, so a fresh clone still runs the suite.
Install it with `uv tool install rashid`.

    python3 tests/test_conformance.py
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "catalog"

# rule_id -> why it is accepted. See docs/conformance.md.
ACCEPTED = {
    "PTL-VIZ-001": (
        "Thumbnails are WebP. Portolan 0.1 allows only PNG and JPEG; "
        "image/webp is added by portolan-sdi/portolan-spec#121, which this "
        "catalog targets. WebP holds every thumbnail under 50 KB where the "
        "same image as PNG runs several times larger."
    ),
}


def main():
    rashid = shutil.which("rashid")
    if not rashid:
        print("SKIP: rashid not installed (`uv tool install rashid`)")
        return

    proc = subprocess.run([rashid, "check", str(CATALOG), "--no-data", "--json"],
                          capture_output=True, text=True)
    try:
        report = json.loads(proc.stdout)
    except json.JSONDecodeError:
        print(proc.stdout[-2000:])
        print(proc.stderr[-2000:], file=sys.stderr)
        sys.exit("rashid did not return JSON")

    errors, accepted, infos = [], [], []
    for f in report.get("findings", []):
        sev = f.get("severity")
        if sev == "info":
            infos.append(f)
        elif f.get("rule_id") in ACCEPTED:
            accepted.append(f)
        elif sev in ("error", "warning"):
            errors.append(f)

    for rule, why in ACCEPTED.items():
        n = sum(1 for f in accepted if f["rule_id"] == rule)
        print(f"accepted  {rule}  x{n}\n          {why}")
    if infos:
        seen = sorted({f["rule_id"] for f in infos})
        print(f"info      {', '.join(seen)}  ({len(infos)} finding(s), not failures)")

    if errors:
        print(f"\n{len(errors)} unaccepted finding(s):\n")
        for f in errors[:40]:
            print(f"  {f.get('severity'):<8} {f.get('rule_id')}  "
                  f"{f.get('path', '')}\n           {f.get('message')}")
        if len(errors) > 40:
            print(f"  ... and {len(errors) - 40} more")
        print("\nEither fix them, or add the rule to ACCEPTED *and* to "
              "docs/conformance.md.")
        sys.exit(1)

    print(f"\nok: conforms to Portolan, with {len(accepted)} accepted deviation(s)")


if __name__ == "__main__":
    main()
