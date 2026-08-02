# TriMet Geospatial Data — agent guide

A cloud-native mirror of the eight geospatial layers TriMet publishes at
[developer.trimet.org/gis](https://developer.trimet.org/gis/). Every collection is a single
GeoParquet file plus PMTiles, in WGS84. Total 15,232
features; the whole catalog is under 5 MB, so nothing here needs partitioning or
a query engine beyond DuckDB.

## The collections, and how they connect

| Collection | Rows | Geometry | Key | Notes |
|---|---|---|---|---|
| [`district-boundary`](./district-boundary/AGENTS.md) | 1 | Polygon | — | single polygon; the service district |
| [`routes`](./routes/AGENTS.md) | 200 | LineString | `(rte, dir)` | alignments; `rte` alone is **not** unique |
| [`rail-lines`](./rail-lines/AGENTS.md) | 171 | LineString | — | generalized for display; `line` encodes shared track |
| [`stops`](./stops/AGENTS.md) | 6,316 | Point | `stop_id` | deduplicated stops; `stop_id` is the public stop number |
| [`route-stops`](./route-stops/AGENTS.md) | 8,314 | Point | `(rte, dir, stop_id)` | stops exploded by service; the only stop↔route link |
| [`rail-stops`](./rail-stops/AGENTS.md) | 169 | Point | — | **no id column**; does not join to `stops` |
| [`transit-centers`](./transit-centers/AGENTS.md) | 15 | Point | `name` | 15 hubs |
| [`park-and-rides`](./park-and-rides/AGENTS.md) | 46 | Point | `name` | 46 lots, `spaces` = nominal capacity |

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
SELECT * FROM 'https://data.source.coop/cholmes/trimet/stops/stops.parquet' LIMIT 10;
```

Every file streams over HTTP range requests. All are Hilbert-ordered with a
GeoParquet 1.1 `bbox` covering column, so filtering on `bbox.*` prunes row groups
before any geometry is read. S3 URIs are in each `collection.json` under
`assets.data.alternate.s3`.

## Coordinate system, and what follows from it

TriMet publishes all eight layers in **EPSG:2913**, NAD83(HARN) / Oregon North,
**in international feet**. This catalog republishes them in **EPSG:4326**, so
coordinates are degrees.

That matters the moment you measure anything. `ST_Length` and `ST_Area` on the
published geometry return *degrees*, which is not a unit of distance. Project
back to the source CRS first, and note the `always_xy := true` argument — without
it DuckDB applies EPSG:4326's authority-declared latitude-first axis order and
every transformed coordinate comes back `Infinity`:

```sql
ST_Transform(geometry, 'EPSG:4326', 'EPSG:2913', always_xy := true)
```

The result is in feet. Multiply by 0.3048 for metres. Nothing in this catalog
carries a pre-computed length or area column except the district boundary, which
carries TriMet's own `area_sq_mi` and `acres`.


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

## License, and a warning

TriMet distributes these datasets free of charge, but **the terms of use do not
grant redistribution rights**. Section 4 of TriMet's
[Terms of Use](https://developer.trimet.org/terms_of_use.shtml) reserves
reproduction, modification, distribution and republication of site Content
without written consent; the redistribution license in section 5 covers the Web
Services API, not these GIS downloads. The collections therefore declare
`"license": "other"` with a link to those terms, rather than claiming an open
license the source does not offer.

Practically: use the data, and contact **gis@trimet.org** before redistributing
it or building a product on it. If you need transit data under clear open terms,
TriMet's [GTFS feed](https://developer.trimet.org/GTFS.shtml) is the better
starting point.

