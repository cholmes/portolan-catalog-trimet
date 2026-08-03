#!/usr/bin/env python3
"""Run every SQL block that appears in the generated documentation.

test_recipes.py covers the curated recipes in docs_content.RECIPES. This covers
everything else the docs show: the Quick Start, the row-group pruning example,
the coordinate-transform snippet — the boilerplate in make_docs.py that no one
thinks of as a query until it is wrong in front of a user.

It earned its place immediately. The pruning example named the covering column
`bbox`; GDAL actually writes `<geometry column>_bbox`, so the published snippet
would have failed for every reader who pasted it.

Remote URLs are rewritten to local paths so this runs offline and tests the
files in the working tree rather than whatever is currently published.

    python3 tests/test_doc_sql.py
"""
import importlib.util
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "catalog"
sys.path.insert(0, str(ROOT / "tools"))
import manifest as M  # noqa: E402

PREAMBLE = "INSTALL spatial; LOAD spatial;\n"
SQL_BLOCK = re.compile(r"```sql\n(.*?)```", re.S)

# Fragments, not statements: shown to explain a function's units or an
# expression's shape, and not runnable on their own.
FRAGMENT = re.compile(r"^\s*(ST_\w+\(|--)", re.M)


def statements(text):
    """SQL blocks that are actual queries, with remote URLs made local."""
    out = []
    for block in SQL_BLOCK.findall(text):
        sql = block.strip()
        if not re.search(r"\bSELECT\b", sql, re.I):
            continue          # INSTALL/LOAD-only blocks
        if not sql.rstrip().endswith(";"):
            continue          # a fragment, e.g. the units cheat-sheet
        sql = sql.replace(M.PUBLIC_BASE + "/", "")
        out.append(sql)
    return out


def run_sql(sql):
    if importlib.util.find_spec("duckdb"):
        import duckdb
        cwd = os.getcwd()
        os.chdir(CATALOG)
        try:
            con = duckdb.connect()
            try:
                con.execute(PREAMBLE)
                con.execute(sql).fetchall()
                return 0, ""
            finally:
                con.close()
        except Exception as e:  # noqa: BLE001
            return 1, str(e)
        finally:
            os.chdir(cwd)
    proc = subprocess.run(["duckdb", "-c", PREAMBLE + sql],
                          cwd=CATALOG, capture_output=True, text=True)
    return proc.returncode, proc.stderr


def main():
    if not importlib.util.find_spec("duckdb") and not shutil.which("duckdb"):
        print("SKIP: no duckdb available")
        return

    docs = sorted(CATALOG.glob("*.md")) + sorted(CATALOG.glob("*/*.md"))
    failures, total = [], 0
    for doc in docs:
        for i, sql in enumerate(statements(doc.read_text()), 1):
            total += 1
            rc, err = run_sql(sql)
            label = f"{doc.relative_to(CATALOG)} block {i}"
            if rc != 0:
                failures.append((label, sql, err.strip()[:300]))
                print(f"FAIL {label}")
            else:
                print(f"ok   {label}")

    print(f"\n{total - len(failures)}/{total} documented SQL blocks ran")
    if failures:
        print("\nFailures:")
        for label, sql, err in failures:
            print(f"\n--- {label}\n{sql}\n  -> {err}")
        sys.exit(1)


if __name__ == "__main__":
    main()
