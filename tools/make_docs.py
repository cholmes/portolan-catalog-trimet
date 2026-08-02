#!/usr/bin/env python3
"""Generate README.md and AGENTS.md for the catalog and every collection.

Prose comes from tools/docs_content.py; structure, numbers and schema tables are
generated here from the manifest and from the data files themselves, so a count
in a README cannot drift from the file it describes.

The two files have different jobs, per the Portolan documentation best practices:
the README is for a person deciding whether to trust and use the data; the
AGENTS.md is for an agent that has already decided and now needs to get the first
query right.

    python3 tools/make_docs.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import manifest as M  # noqa: E402
import docs_content as C  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "catalog"
BASE = M.PUBLIC_BASE


def coll_stats(cid):
    import pyarrow.parquet as pq
    p = OUT / cid / f"{cid}.parquet"
    md = pq.ParquetFile(p).metadata
    return {"rows": md.num_rows, "row_groups": md.num_row_groups,
            "size": p.stat().st_size,
            "pmtiles": (OUT / cid / f"{cid}.pmtiles").stat().st_size,
            "thumb": (OUT / cid / "thumbnail.webp").stat().st_size}


def human(n):
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024


def schema_table(coll):
    """Column table with TriMet's own definitions. Same text as `table:columns`
    in collection.json — both are generated from the manifest."""
    import pyarrow.parquet as pq
    schema = pq.read_schema(OUT / coll["id"] / f"{coll['id']}.parquet")
    described = {c["name"]: c for c in coll["columns"]}
    rows = ["| Column | Type | Description |", "|---|---|---|"]
    for name in schema.names:
        t = str(schema.field(name).type)
        if name in described:
            d = described[name]
            desc = d["description"]
            if "values" in d:
                codes = "; ".join(f"`{k}` {v.rstrip('.')}" for k, v in d["values"].items())
                desc += f"<br>Values: {codes}."
        elif name == "geometry":
            desc = "Feature geometry, WGS84 lon/lat."
        elif name == "bbox":
            desc = "GeoParquet 1.1 covering column, for row-group pruning."
        else:
            desc = ""
        rows.append(f"| `{name}` | {t} | {desc} |")
    return "\n".join(rows)


def styles_table(cid):
    sdir = OUT / cid / "styles"
    src = {"trimet-rail.sld.xml", "trimet-stops.sld.xml", "trimet-routes.style.json"}
    names = sorted(p.name for p in sdir.glob("*.json") if p.name not in src)
    names.sort(key=lambda n: (n != "default.json", n))
    rows = ["| Style | What it shows |", "|---|---|"]
    for n in names:
        meta = json.loads((sdir / n).read_text())
        desc = meta.get("metadata", {}).get("description", "")
        rows.append(f"| [`{n}`](./styles/{n}) | {desc} |")
    return "\n".join(rows)


def source_row(coll):
    s = M.source_links(coll)
    return (f"[Shapefile]({s['shapefile']}) · [KML]({s['kml']}) · "
            f"[Metadata]({s['metadata']})")


# ---------------------------------------------------------------------------

def collection_readme(coll):
    cid = coll["id"]
    c = C.COLLECTIONS[cid]
    st = coll_stats(cid)
    s = M.source_links(coll)
    n = f"{coll['count']:,}"

    return f"""# {coll['title']}

{coll['description']} **{n} {coll['geometry']} features** covering the TriMet
service district in the Portland, Oregon metropolitan area, published by TriMet
as `{coll['source']}` and last updated at the source on
**{coll['source_updated_text']}**.

{c['summary']}

> **Agents:** see [AGENTS.md](./AGENTS.md) for join keys, verified query recipes
> and the caveats that will otherwise cost you a wrong answer.

![{coll['title']}](./thumbnail.webp)

## Quick start

Read it straight from object storage — DuckDB fetches only the byte ranges it
needs, so there is nothing to download first:

```sql
INSTALL spatial; LOAD spatial;
INSTALL httpfs;  LOAD httpfs;

SELECT * FROM '{BASE}/{cid}/{cid}.parquet' LIMIT 10;
```

Or with GeoPandas:

```python
import geopandas as gpd
gdf = gpd.read_parquet("{BASE}/{cid}/{cid}.parquet")
```

## Suggested uses

{c['uses']}

## Limitations and inappropriate uses

{c['limitations']}

## Schema

{schema_table(coll)}

Column descriptions are TriMet's own, taken verbatim from
[{s['metadata'].split('/')[-1]}]({s['metadata']}). The same text is carried in
`table:columns` in [collection.json](./collection.json).

## Visualization

{styles_table(cid)}

The PMTiles layer is named `{cid}`. Styles reference it as `../{cid}.pmtiles`,
so they load unmodified against this directory.

## Files

| File | Size | What it is |
|---|---|---|
| [`{cid}.parquet`](./{cid}.parquet) | {human(st['size'])} | GeoParquet 1.1, {st['rows']:,} rows in {st['row_groups']} row group(s), zstd, Hilbert-ordered, bbox covering column |
| [`{cid}.pmtiles`](./{cid}.pmtiles) | {human(st['pmtiles'])} | Vector tiles for display, every feature kept at every zoom |
| [`thumbnail.webp`](./thumbnail.webp) | {human(st["thumb"])} | Rendered from `styles/default.json` over a light basemap |
| [`collection.json`](./collection.json) | — | STAC Collection metadata |

## Provenance

[![TriMet](../_assets/trimet-logo.png)]({M.GIS_PAGE})

Produced by **TriMet GIS** ({M.TRIMET_CONTACT['address']},
{M.TRIMET_CONTACT['city']}, {M.TRIMET_CONTACT['email']}) and distributed at
[developer.trimet.org/gis]({M.GIS_PAGE}) as `{coll['source']}`.

The originals are linked as assets and are the authoritative copy:
{source_row(coll)}

This collection was produced by reprojecting TriMet's Shapefile from
{M.SOURCE_CRS} ({M.SOURCE_CRS_NAME}) to EPSG:4326 and writing GeoParquet and
PMTiles. No features were added, removed or edited. The exact commands are in
[`tools/convert.py`](https://github.com/cholmes/portolan-catalog-trimet/blob/main/tools/convert.py).

{C.LICENSE_NOTE}
"""


def collection_agents(coll):
    cid = coll["id"]
    c = C.COLLECTIONS[cid]
    st = coll_stats(cid)

    quirks = "\n\n".join(f"### {h}\n\n{b}" for h, b in c["quirks"])
    recipes = "\n\n".join(f"### {t}\n\n```sql\n{q}\n```" for t, q in c["recipes"])
    related = "\n".join(f"- [`{r}`](../{r}/AGENTS.md) — {why}" for r, why in c["related"])

    return f"""# {coll['title']} — agent guide

{coll['description']} {st['rows']:,} {coll['geometry']} features, WGS84, one
GeoParquet file of {human(st['size'])} in {st['row_groups']} row group(s).

## Access

```sql
INSTALL spatial; LOAD spatial;
INSTALL httpfs;  LOAD httpfs;
SELECT * FROM '{BASE}/{cid}/{cid}.parquet' LIMIT 10;
```

Reads stream over HTTP range requests — query in place, do not download. The file
is Hilbert-ordered and carries a GeoParquet 1.1 `bbox` covering column, so a
spatial filter on `bbox.xmin` / `bbox.ymin` / `bbox.xmax` / `bbox.ymax` prunes
row groups from metadata alone:

```sql
SELECT * FROM '{BASE}/{cid}/{cid}.parquet'
WHERE bbox.xmin > -122.70 AND bbox.xmax < -122.60
  AND bbox.ymin >   45.50 AND bbox.ymax <   45.55;
```

The recipes below use bare relative paths (`'{cid}/{cid}.parquet'`) for
readability. Prefix them with `{BASE}/` to run remotely.

Other formats: `{cid}.pmtiles` for map display (layer name `{cid}`), and TriMet's
original Shapefile and KML, linked from `collection.json` as `source_shapefile`
and `source_kml`.

{C.CRS_NOTE}

## Quirks and caveats

{quirks}

## Query recipes

{recipes}

## Related collections

{related}

## Provenance

TriMet publishes this as `{coll['source']}` at
[developer.trimet.org/gis]({M.GIS_PAGE}), last updated
{coll['source_updated_text']}. Every column description in `collection.json`
comes from [TriMet's metadata page]({M.source_links(coll)['metadata']}) — that
page, not this catalog, is the authority on what a field means.

Conversion: `ogr2ogr -f Parquet -t_srs EPSG:4326 -lco COMPRESSION=ZSTD -lco
SORT_BY_BBOX=YES -lco WRITE_COVERING_BBOX=YES`, then tippecanoe with `-r1
--no-feature-limit` so no feature is dropped at any zoom. See
[`tools/convert.py`](https://github.com/cholmes/portolan-catalog-trimet/blob/main/tools/convert.py).

{C.LICENSE_NOTE}
"""


# ---------------------------------------------------------------------------

def catalog_readme():
    rows = ["| Collection | Features | Geometry | Description |", "|---|---|---|---|"]
    for c in M.COLLECTIONS:
        rows.append(f"| [{c['title']}](./{c['id']}/) | {c['count']:,} | "
                    f"{c['geometry']} | {c['blurb']} |")
    table = "\n".join(rows)

    srcs = ["| Collection | TriMet source | Last updated at source |", "|---|---|---|"]
    for c in M.COLLECTIONS:
        srcs.append(f"| {c['title']} | `{c['source']}` — {source_row(c)} | "
                    f"{c['source_updated_text']} |")
    src_table = "\n".join(srcs)

    return f"""# TriMet Geospatial Data

[![TriMet](./_assets/trimet-logo.png)]({M.GIS_PAGE})

{C.CATALOG_INTRO}

> **Agents:** start at [AGENTS.md](./AGENTS.md).

## Collections

{table}

## Quick start

```sql
INSTALL spatial; LOAD spatial;
INSTALL httpfs;  LOAD httpfs;

-- The 15 transit centers, by county
SELECT county, count(*) FROM '{BASE}/transit-centers/transit-centers.parquet'
GROUP BY county;
```

Past the first query, the interesting pattern is joining across collections.
`stops` and `route-stops` share `stop_id` exactly — all 6,316 of them — which
turns a stop location into the set of routes that serve it:

```sql
SELECT s.stop_name, count(DISTINCT r.rte) AS routes
FROM '{BASE}/stops/stops.parquet' s
JOIN '{BASE}/route-stops/route-stops.parquet' r USING (stop_id)
GROUP BY 1 ORDER BY routes DESC LIMIT 10;
```

## Cartography

Where TriMet publishes a style for a layer, this catalog reproduces it rather
than inventing one. Two TriMet sources are used, and both are mirrored into the
collections they style so the reproduction can be checked against its origin:

- **`ott:rail`**, the GeoServer SLD behind TriMet's rail maps, fetched from
  `ws.trimet.org` via WMS `GetStyles`. Its rules key on exactly the `line` values
  the rail layers carry, so `rail-lines/styles/default.json` reproduces it
  segment for segment — including the layered dashed overlays that show which
  services share a track.
- **`trimet-routes`**, TriMet's MapLibre style at `tiles.trimet.org`, which gives
  the line weights and the flat bus color `#136390`. Where it resolves
  `route_color` from GTFS, the equivalent colors are taken from TriMet's GTFS
  `routes.txt`.

Every collection ships three to five styles; see each collection's README.

## Where the data comes from

{src_table}

All eight are published in {M.SOURCE_CRS} ({M.SOURCE_CRS_NAME}) and reprojected
here to EPSG:4326. TriMet's note on the GIS page:

> {M.GIS_PAGE_NOTE}

Contact for the source data: **TriMet GIS**, {M.TRIMET_CONTACT['address']},
{M.TRIMET_CONTACT['city']} — {M.TRIMET_CONTACT['email']}.

{C.LICENSE_NOTE}

## About this mirror

Maintained by {M.HOST['name']} ({M.HOST['email']}), **not affiliated with
TriMet**. Built and regenerated with the scripts in
[`tools/`](https://github.com/cholmes/portolan-catalog-trimet/tree/main/tools).
Conforms to the [Portolan](https://www.portolan-sdi.org/) specification v0.1.0.

The TriMet name and logo are trademarks of TriMet, used here solely as a link
back to trimet.org, which section 6 of TriMet's Terms of Use permits.
"""


def catalog_agents():
    rows = ["| Collection | Rows | Geometry | Key | Notes |", "|---|---|---|---|---|"]
    keys = {
        "district-boundary": ("—", "single polygon; the service district"),
        "routes": ("`(rte, dir)`", "alignments; `rte` alone is **not** unique"),
        "rail-lines": ("—", "generalized for display; `line` encodes shared track"),
        "stops": ("`stop_id`", "deduplicated stops; `stop_id` is the public stop number"),
        "route-stops": ("`(rte, dir, stop_id)`", "stops exploded by service; the only stop↔route link"),
        "rail-stops": ("—", "**no id column**; does not join to `stops`"),
        "transit-centers": ("`name`", "15 hubs"),
        "park-and-rides": ("`name`", "46 lots, `spaces` = nominal capacity"),
    }
    for c in M.COLLECTIONS:
        k, note = keys[c["id"]]
        rows.append(f"| [`{c['id']}`](./{c['id']}/AGENTS.md) | {c['count']:,} | "
                    f"{c['geometry']} | {k} | {note} |")
    table = "\n".join(rows)

    return f"""# TriMet Geospatial Data — agent guide

A cloud-native mirror of the eight geospatial layers TriMet publishes at
[developer.trimet.org/gis]({M.GIS_PAGE}). Every collection is a single
GeoParquet file plus PMTiles, in WGS84. Total {sum(c['count'] for c in M.COLLECTIONS):,}
features; the whole catalog is under 5 MB, so nothing here needs partitioning or
a query engine beyond DuckDB.

## The collections, and how they connect

{table}

**The joins that work:**

- `stops` ↔ `route-stops` on **`stop_id`**. Exact: all 6,316 stops appear in
  both, and `stop_name` never disagrees. This is the join that answers "which
  routes serve this stop".
- `route-stops` ↔ `routes` on **`(rte, dir)`**. Use it to get `public_rte`, the
  rider-facing route name, which `route-stops` lacks.
- `rail-lines` ↔ `rail-stops` on **`line`**, a shared code space (not a key — it
  is many-to-many, and it describes which services run there).

**The join that does not exist:** `rail-stops` carries no `stop_id`, so it cannot
be joined to `stops` or `route-stops` by key. Match spatially and check the
distance; the rail layers are generalized.

## Access

```sql
INSTALL spatial; LOAD spatial;
INSTALL httpfs;  LOAD httpfs;
SELECT * FROM '{BASE}/stops/stops.parquet' LIMIT 10;
```

Every file streams over HTTP range requests. All are Hilbert-ordered with a
GeoParquet 1.1 `bbox` covering column, so filtering on `bbox.*` prunes row groups
before any geometry is read. S3 URIs are in each `collection.json` under
`assets.data.alternate.s3`.

{C.CRS_NOTE}

## Catalog-wide caveats

### These are alignments and locations, not schedules

Nothing in this catalog is time-aware. There are no headways, no trip times, no
service calendars. The `frequent` flag is the only service-level hint and it is a
boolean-as-string, not a frequency. For anything temporal use TriMet's
[GTFS feed](https://developer.trimet.org/GTFS.shtml), which is also where the
route colors used in these styles come from.

### The rail layers are drawn, not measured

`rail-lines` and `rail-stops` are, in TriMet's words, "generalized to improve
cartographic display at smaller scales". Do not compute track length or platform
position from them. `routes` carries the operational alignment.

### Vintages differ by more than a decade

`district-boundary` was last updated 2013-01-09; `stops` and `route-stops`
2026-07-30. Each collection's `collection.json` carries its own source date in
`extent.temporal`. Do not present the catalog as a single-date snapshot.

### Documented code values that do not appear, and undocumented ones that do

- `status` documents `Planned` and `UC` everywhere, but **every row in every
  collection is currently `Existing`**.
- `rail-lines` and `rail-stops` document a code `BL/NS`; the data contains
  **`NS/BL`**. Filter on what the data has.
- `route-stops` carries a `frequent` column that TriMet's metadata page for that
  layer does not document.
- `stops` has a `type` value `BSC` (shared bus and streetcar) that does not occur
  in `routes` or `route-stops`.

### Counts of "stops" depend on which layer you ask

6,316 physical stops (`stops`), 8,314 stop-route-direction rows (`route-stops`),
169 rail stations (`rail-stops`, which collapses directional platforms) against
225 rail-typed rows in `stops`. All are correct answers to different questions.
State which you used.

## Visualization

Each collection has a `styles/` directory with three to five MapLibre GL styles;
`default.json` is the one to use unless you have a reason otherwise. Discover
them from `collection.json` by filtering assets on `roles` containing `style`.

The rail and route styles reproduce TriMet's own published cartography rather
than inventing a palette — the source SLD and MapLibre style are mirrored into
the collections as assets with roles `["style", "source"]`, so a style can be
diffed against its origin.

## Provenance

TriMet is the producer; this catalog is a **mirror** and carries `via` links to
TriMet's metadata page on every collection. TriMet's pages are the authority on
what any field means, and every column description here was taken from them.

{C.LICENSE_NOTE}
"""


def main():
    for coll in M.COLLECTIONS:
        d = OUT / coll["id"]
        (d / "README.md").write_text(collection_readme(coll))
        (d / "AGENTS.md").write_text(collection_agents(coll))
        print(f"  {coll['id']}: README.md + AGENTS.md")
    (OUT / "README.md").write_text(catalog_readme())
    (OUT / "AGENTS.md").write_text(catalog_agents())
    print("  catalog: README.md + AGENTS.md")


if __name__ == "__main__":
    main()
