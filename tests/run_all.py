#!/usr/bin/env python3
"""Run every test. Dependency-light: plain python3, plus duckdb for the recipes.

    python3 tests/run_all.py
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TESTS = ["test_catalog.py", "test_conformance.py", "test_styles.py",
         "test_recipes.py", "test_doc_sql.py", "test_regen.py"]


def main():
    failed = []
    for t in TESTS:
        print(f"\n{'=' * 70}\n{t}\n{'=' * 70}")
        r = subprocess.run([sys.executable, f"tests/{t}"], cwd=ROOT)
        if r.returncode != 0:
            failed.append(t)
    print(f"\n{'=' * 70}")
    if failed:
        print(f"FAILED: {', '.join(failed)}")
        sys.exit(1)
    print(f"All {len(TESTS)} test files passed.")


if __name__ == "__main__":
    main()
