# portolan-catalog-trimet — developer guide

A Portolan/STAC catalog mirroring the eight geospatial layers TriMet publishes at
[developer.trimet.org/gis](https://developer.trimet.org/gis/). This repo is the
**source of truth for catalog metadata only**; the data files are generated and
published to Source Cooperative, never committed.

## The one rule

**Everything under `catalog/` is generated. Never hand-edit it.**

`tests/test_regen.py` copies `catalog/`, re-runs the generators, and requires
byte-identical output. A hand-edit fails that test, and the next `build.py` would
silently revert it anyway. To change what the catalog says, change the generator
or the manifest.

## Where the content lives

| To change | Edit |
|---|---|
| Any description, column definition, code list, feature count, bbox, source date | `tools/manifest.py` |
| README/AGENTS prose: quirks, limitations, suggested uses, SQL recipes | `tools/docs_content.py` |
| Colors, line widths, style layers | `tools/make_styles.py` |
| STAC structure, assets, links, providers | `tools/make_collections.py` |
| Doc structure and generated tables | `tools/make_docs.py` |

`manifest.py` is the single source of truth for everything descriptive. Its
docstring states the provenance rule and it is worth honoring: **every string in
it is either quoted from a TriMet source or measured from the data.** Nothing in
this catalog is invented. If you cannot point at where a fact came from, it does
not go in.

## Build

```bash
python3 tools/build.py            # from local sources
python3 tools/build.py --fetch    # re-download from TriMet first
python3 tests/run_all.py          # five gates
```

Step order matters and `build.py` encodes it: convert → styles → thumbnails →
webp → collections → docs. Collections embed file sizes and checksums, so they
must run after every file is final; docs read collection.json, so they run last.

### Thumbnails need Node 20, 22 or 24 — not 23

Rendered by [chiitiler](https://github.com/Kanahiro/chiitiler) (MapLibre GL
Native), which ships prebuilt binaries only for ABI **v115 / v127 / v137** =
Node 20 / 22 / 24, and sets `--fallback-to-build=false` so there is no source
build. Node 23 is ABI v131 and `npm install` dies with a 404.

`brew install node@24` is keg-only, so it sits alongside an existing Node without
relinking it. `build.py` looks for `/opt/homebrew/opt/node@{24,22,20}/bin` and
skips the step with a warning if it finds none, leaving existing thumbnails
alone rather than destroying them.

Thumbnails render as lossless PNG, then `tools/to_webp.py` converts them,
binary-searching quality per file for the highest that fits a 50 KB budget.
Converting separately means trying a different budget does not refetch every
basemap tile.

## Cartography — reproduce, don't invent

The catalog's design rule: **where TriMet publishes a style for a layer,
reproduce it.** Two sources, both mirrored into the collections they style so the
reproduction can be diffed against its origin:

- **`ott:rail`** (GeoServer SLD, via `ws.trimet.org` WMS `GetStyles`). Its rules
  filter on exactly the `line` values `rail-lines` and `rail-stops` carry — this
  is not a coincidence, it is the style written for this data. It draws shared
  trackage as a solid base stroke plus one dashed overlay per additional line;
  `make_styles.py:rail_lines()` reconstructs that from `RAIL_BASE` and
  `RAIL_OVERLAYS` in the manifest.
- **`trimet-routes`** (MapLibre, `tiles.trimet.org`). Bus is a flat `#136390`;
  MAX, streetcar and BRT resolve `route_color` from GTFS at draw time, so the
  equivalent colors come from GTFS `routes.txt`.

Parsing note, if you ever re-derive the SLD: a single SLD `Rule` can hold several
`LineSymbolizer`s, and that is where the layering lives. Collapsing CSS
parameters per rule instead of per symbolizer loses it and makes the shared-track
codes look like they render as a single dashed line.

### MapLibre gotcha that bit once

`["zoom"]` may only be the **direct input of a top-level `step`/`interpolate`**.
Nesting it — `["*", factor, ["interpolate", …, ["zoom"], …]]` — is invalid, and
MapLibre rejects the *whole style*, so the layer silently does not draw. Use
`make_styles.py:zoom_scaled()`, which multiplies the factor into each stop
instead. `tests/test_styles.py` validates every style against the real style spec
and would catch a regression.

## Data notes worth knowing before you touch anything

- Source CRS is **EPSG:2913, in international feet**. Published as EPSG:4326.
  DuckDB's `ST_Transform` needs `always_xy := true` or every coordinate comes
  back `Infinity` — EPSG:4326's authority axis order is latitude-first.
- `routes` mixes `LINESTRING` and `MULTILINESTRING`, and `ST_Length_Spheroid`
  returns `nan` on it. Project and use `ST_Length`.
- `stops` ↔ `route-stops` join on `stop_id` **exactly** (6,316 both sides).
  `rail-stops` has **no id column** and joins to nothing.
- TriMet's metadata documents a code `BL/NS`; the data contains `NS/BL`.
- `route-stops` carries a `frequent` column TriMet's metadata page for that layer
  does not document.

These and more are in each collection's AGENTS.md, which is the right place for
them — this file should not duplicate the catalog's own documentation.

## SQL recipes are tested

Every snippet in `docs_content.py:RECIPES` is executed by `tests/test_recipes.py`
against the real files. Add a recipe, run the test. A query that merely *looks*
right is not good enough — two of the original recipes returned `nan` and zero
rows respectively, and only running them surfaced it.

## Conformance

Targets **Portolan 0.1.0 + [spec#121](https://github.com/portolan-sdi/portolan-spec/pull/121)**
(WebP thumbnails). `tests/test_conformance.py` runs `rashid` and fails on
anything not in its `ACCEPTED` list. **Never grow `ACCEPTED` without adding the
reasoning to [`docs/conformance.md`](docs/conformance.md).**

## Publish

```bash
python3 tools/publish.py            # dry run
python3 tools/publish.py --confirm  # needs AWS credentials
```

Syncs `catalog/` 1:1 to `s3://us-west-2.opendata.source.coop/cholmes/trimet/`
(config in `catalog.publish.yaml`). Unchanged objects are skipped by size+MD5 vs
size+ETag. **It never deletes.**

## Licensing — read before publishing anything

TriMet's terms **do not grant redistribution rights** for these GIS downloads.
Collections declare `license: "other"` with a `rel: license` link to TriMet's
terms. Do not "upgrade" this to CC-BY or CC0; nothing in the source supports it.
The root README carries the warning for users, and it should stay prominent.

## STAC terminology

- **Catalog** — the root container
- **Collection** — a dataset (e.g. `stops/`)
- **Item** — a single spatiotemporal entity. This catalog has none; every
  collection is a single-file collection with collection-level assets.
- **Asset** — an actual file (`.parquet`, `.pmtiles`, `.webp`)

Say "collection", not "dataset".
