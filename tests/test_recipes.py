#!/usr/bin/env python3
"""Run every SQL recipe published in the docs, against the real files.

A broken Quick Start costs more trust than no Quick Start, so this is a gate:
every snippet in docs_content.RECIPES executes, and must return without error.
Run from the repo root with plain python3; needs the `duckdb` CLI.
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import docs_content as C  # noqa: E402

CATALOG = ROOT / "catalog"


def run_sql(sql):
    """Recipes are written with catalog-relative paths, so run from catalog/."""
    proc = subprocess.run(
        ["duckdb", "-c", "INSTALL spatial; LOAD spatial;\n" + sql],
        cwd=CATALOG, capture_output=True, text=True,
    )
    return proc.returncode, proc.stdout, proc.stderr


def main():
    failures = []
    total = 0
    for cid, content in C.COLLECTIONS.items():
        for title, sql in content["recipes"]:
            total += 1
            rc, out, err = run_sql(sql)
            if rc != 0:
                failures.append((cid, title, err.strip()[:400]))
                print(f"FAIL {cid}: {title}")
            elif not out.strip():
                failures.append((cid, title, "returned no output"))
                print(f"FAIL {cid}: {title} (empty result)")
            else:
                print(f"ok   {cid}: {title}")

    print(f"\n{total - len(failures)}/{total} recipes ran")
    if failures:
        print("\nFailures:")
        for cid, title, err in failures:
            print(f"\n--- {cid}: {title}\n{err}")
        sys.exit(1)


if __name__ == "__main__":
    main()
