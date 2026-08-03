#!/usr/bin/env python3
"""Run every SQL recipe published in the docs, against the real files.

A broken Quick Start costs more trust than no Quick Start, so this is a gate:
every snippet in docs_content.RECIPES executes, and must return without error.

Uses the `duckdb` Python module if it is installed, else the `duckdb` CLI, so
this runs both in CI (conda-forge ships the module) and on a machine that only
has the binary. SKIPs if neither is present.
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import docs_content as C  # noqa: E402

CATALOG = ROOT / "catalog"

PREAMBLE = "INSTALL spatial; LOAD spatial;\n"


def run_sql_module(sql):
    """Recipes use catalog-relative paths, so resolve them from catalog/."""
    import duckdb
    cwd = os.getcwd()
    os.chdir(CATALOG)
    try:
        con = duckdb.connect()
        try:
            con.execute(PREAMBLE)
            rows = con.execute(sql).fetchall()
            return 0, repr(rows), ""
        finally:
            con.close()
    except Exception as e:  # noqa: BLE001
        return 1, "", str(e)
    finally:
        os.chdir(cwd)


def run_sql_cli(sql):
    proc = subprocess.run(["duckdb", "-c", PREAMBLE + sql],
                          cwd=CATALOG, capture_output=True, text=True)
    return proc.returncode, proc.stdout, proc.stderr


def pick_runner():
    import importlib.util
    if importlib.util.find_spec("duckdb"):
        return run_sql_module, "duckdb python module"
    if shutil.which("duckdb"):
        return run_sql_cli, "duckdb CLI"
    return None, None


def main():
    run_sql, how = pick_runner()
    if not run_sql:
        print("SKIP: neither the duckdb Python module nor the duckdb CLI is available")
        return
    print(f"using {how}\n")

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
