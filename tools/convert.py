#!/usr/bin/env python3
"""Convert the TriMet source Shapefiles into GeoParquet and PMTiles.

Reads from ``sources/shp/<layer>/`` and writes ``catalog/<collection>/``.
Both outputs are reproducible: re-running overwrites in place.

    python3 tools/convert.py            # everything
    python3 tools/convert.py routes     # one collection

Requires ogr2ogr (GDAL 3.9+, for SORT_BY_BBOX) and tippecanoe.
"""
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from manifest import COLLECTIONS  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "sources" / "shp"
OUT = ROOT / "catalog"

# Zoom ceiling per collection. Point layers and the generalized rail
# cartography are legible by z14; the single district polygon needs far less.
MAXZOOM = {"district-boundary": 12}
DEFAULT_MAXZOOM = 14


def run(cmd, **kw):
    print("   $", " ".join(str(c) for c in cmd[:6]), "...")
    subprocess.run(cmd, check=True, **kw)


def to_geoparquet(coll):
    src = SRC / coll["source"] / f"{coll['source']}.shp"
    dst = OUT / coll["id"] / f"{coll['id']}.parquet"
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        dst.unlink()
    run([
        "ogr2ogr", "-f", "Parquet", str(dst), str(src),
        # Everything TriMet ships is EPSG:2913 (NAD83 HARN / Oregon North, intl
        # feet). WGS84 is what GeoParquet readers and tippecanoe expect.
        "-t_srs", "EPSG:4326",
        "-nln", coll["id"],
        "-lco", "COMPRESSION=ZSTD",
        "-lco", "GEOMETRY_ENCODING=WKB",
        # GeoParquet 1.1 covering column, so readers can prune row groups from
        # metadata alone.
        "-lco", "WRITE_COVERING_BBOX=YES",
        # Hilbert-orders rows so nearby features land in the same row group.
        "-lco", "SORT_BY_BBOX=YES",
        "-lco", "ROW_GROUP_SIZE=20000",
    ])
    return dst


def to_pmtiles(coll):
    parquet = OUT / coll["id"] / f"{coll['id']}.parquet"
    dst = OUT / coll["id"] / f"{coll['id']}.pmtiles"
    tmp = dst.with_suffix(".geojsonl")
    run(["ogr2ogr", "-f", "GeoJSONSeq", str(tmp), str(parquet)])
    maxzoom = MAXZOOM.get(coll["id"], DEFAULT_MAXZOOM)
    run([
        "tippecanoe", "-o", str(dst), "--force",
        "-l", coll["id"],
        "-Z0", f"-z{maxzoom}",
        # These layers are small enough to keep every feature at every zoom.
        # Dropping would silently change what a map shows.
        "-r1", "--no-feature-limit", "--no-tile-size-limit",
        "--preserve-input-order",
        str(tmp),
    ])
    tmp.unlink()
    return dst


def main():
    wanted = sys.argv[1:]
    colls = [c for c in COLLECTIONS if not wanted or c["id"] in wanted]
    if wanted and len(colls) != len(wanted):
        sys.exit(f"unknown collection(s): {set(wanted) - {c['id'] for c in colls}}")
    if not shutil.which("tippecanoe"):
        sys.exit("tippecanoe not found on PATH")
    for coll in colls:
        print(f"-- {coll['id']}")
        p = to_geoparquet(coll)
        t = to_pmtiles(coll)
        print(f"   parquet {p.stat().st_size:>9,} B   pmtiles {t.stat().st_size:>9,} B")


if __name__ == "__main__":
    main()
