# TriMet Routes

All existing bus and rail lines. **200 LineString features** covering the TriMet
service district in the Portland, Oregon metropolitan area, published by TriMet
as `tm_routes` and last updated at the source on
**July 13, 2026**.

Every fixed-route alignment TriMet operates, bus and rail together, as one
line per route *and direction*. 200 features covering 179 bus, 13 MAX, 4
streetcar, 2 commuter rail and 2 aerial tram segments.

The `frequent` flag marks TriMet's Frequent Service network — 51 of the 200
route-directions — which is the set of lines scheduled often enough that riders
are told not to consult a timetable.

> **Agents:** see [AGENTS.md](https://source.coop/cholmes/trimet/routes/AGENTS.md) for join keys, verified query recipes
> and the caveats that will otherwise cost you a wrong answer.

[![TriMet Routes](https://data.source.coop/cholmes/trimet/routes/thumbnail.webp)](https://cholmes.github.io/trimet-data-browser)

### 🗺️ [Open this collection in the data browser →](https://cholmes.github.io/trimet-data-browser)

Preview it on a map, inspect the schema and license, and download the
GeoParquet or PMTiles directly.

## Quick start

Read it straight from object storage — DuckDB fetches only the byte ranges it
needs, so there is nothing to download first:

```sql
INSTALL spatial; LOAD spatial;
INSTALL httpfs;  LOAD httpfs;

SELECT * FROM 'https://data.source.coop/cholmes/trimet/routes/routes.parquet' LIMIT 10;
```

Or with GeoPandas:

```python
import geopandas as gpd
gdf = gpd.read_parquet("https://data.source.coop/cholmes/trimet/routes/routes.parquet")
```

## Suggested uses

- Drawing the network. This is the layer behind TriMet's own system maps, and
  `styles/default.json` reproduces the line weights and colors from TriMet's
  published `trimet-routes` MapLibre style.
- Measuring route-miles by mode or by jurisdiction.
- Corridor analysis: buffering alignments to find what lies within a given
  distance of transit.

## Limitations and inappropriate uses

- **`rte` is not a primary key.** 87 route numbers appear twice, once per
  direction. The key is `(rte, dir)`. A `GROUP BY rte` that forgets this
  double-counts every two-way route.
- **These are alignments, not schedules.** Nothing here says how often a bus
  runs, when it runs, or whether it runs today. `frequent` is the only
  service-level hint, and it is a flag rather than a frequency. Use the
  [GTFS feed](https://developer.trimet.org/GTFS.shtml) for anything time-based.
- **Geometry type is mixed.** 91 features are `LINESTRING` and 109 are
  `MULTILINESTRING`, so a route can be several disconnected pieces. Functions
  that assume a single linestring will silently misbehave — see the quirks.
- **Not a rail cartography layer.** For drawing rail specifically, `rail-lines`
  is generalized for display and carries per-line colors; the MAX geometry here
  is the operational alignment.

## Schema

| Column | Type | Description |
|---|---|---|
| `rte` | int32 | Route number. |
| `dir` | int32 | Direction of route.<br>Values: `0` Direction 0; `1` Direction 1. |
| `rte_desc` | string | Route name. |
| `public_rte` | string | Public route number. |
| `dir_desc` | string | Description of route direction. |
| `frequent` | string | Indicates whether a route or route segment has frequent service.<br>Values: `True` Route segment has frequent service; `False` Route segment does not have frequent service. |
| `type` | string | Type of service.<br>Values: `AT` Aerial Tram; `BUS` Bus; `CR` Commuter rail; `MAX` Light rail; `SC` Streetcar. |
| `geometry` | binary | Feature geometry, WGS84 lon/lat. |
| `geometry_bbox` | struct<xmin: float not null, ymin: float not null, xmax: float not null, ymax: float not null> | GeoParquet 1.1 covering column, for row-group pruning. Same projected feet as the geometry. |

Column descriptions are TriMet's own, taken verbatim from
[meta_tm_routes.shtml](https://developer.trimet.org/gis/meta_tm_routes.shtml). The same text is carried in
`table:columns` in [collection.json](https://source.coop/cholmes/trimet/routes/collection.json).

## Visualization

| Style | What it shows |
|---|---|
| [`default.json`](https://source.coop/cholmes/trimet/routes/styles/default.json) | Every fixed-route alignment colored by TYPE, following TriMet's own `trimet-routes` MapLibre style: bus lines thin and blue, MAX heaviest, streetcar thin, commuter rail gray. Colors are TriMet's GTFS route_color values, which is what that style resolves at draw time. |
| [`by-direction.json`](https://source.coop/cholmes/trimet/routes/styles/by-direction.json) | Colors the two DIR values apart. Each route appears twice in this layer, once per direction, and the two alignments are rarely identical because of one-way streets — this style makes those divergences visible. Offsetting the two directions by a couple of pixels keeps coincident segments from hiding each other. |
| [`frequent-service.json`](https://source.coop/cholmes/trimet/routes/styles/frequent-service.json) | Splits the network on the FREQUENT flag. The 51 route-direction segments flagged True are drawn heavy in TriMet's FX green; the remaining 149 recede to a thin gray, so the frequent-service spine stands out against the rest of the system. |
| [`labeled.json`](https://source.coop/cholmes/trimet/routes/styles/labeled.json) | The service-type styling with PUBLIC_RTE drawn along each alignment. Use PUBLIC_RTE rather than RTE for display: it is the number riders see, and it is where lettered services such as FX2 appear. |

The PMTiles layer is named `routes`. Styles reference it as `../routes.pmtiles`,
so they load unmodified against this directory.

## Files

| File | Size | What it is |
|---|---|---|
| [`routes.parquet`](https://data.source.coop/cholmes/trimet/routes/routes.parquet) | 794.0 KB | GeoParquet 1.1, 200 rows in 1 row group(s), zstd, Hilbert-ordered, bbox covering column |
| [`routes.pmtiles`](https://data.source.coop/cholmes/trimet/routes/routes.pmtiles) | 830.3 KB | Vector tiles for display, every feature kept at every zoom |
| [`thumbnail.webp`](https://data.source.coop/cholmes/trimet/routes/thumbnail.webp) | 48.4 KB | Rendered from `styles/default.json` over a light basemap |
| [`collection.json`](https://source.coop/cholmes/trimet/routes/collection.json) | — | STAC Collection metadata |

## Provenance

[![TriMet](https://data.source.coop/cholmes/trimet/_assets/trimet-logo.png)](https://developer.trimet.org/gis/)

Produced by **TriMet GIS** (4012 SE 17th Ave, GIS3,
Portland, OR 97202,
[gis@trimet.org](mailto:gis@trimet.org)) and distributed at
[developer.trimet.org/gis](https://developer.trimet.org/gis/) as `tm_routes`.

The originals are linked as assets and are the authoritative copy:
[Shapefile](https://developer.trimet.org/gis/data/tm_routes.zip) · [KML](https://developer.trimet.org/gis/data/tm_routes.kml) · [Metadata](https://developer.trimet.org/gis/meta_tm_routes.shtml)

This collection was produced by converting TriMet's Shapefile to GeoParquet,
keeping its native EPSG:2913 (NAD83(HARN) / Oregon North (ft)), and to PMTiles in
WGS84 for display. No features were added, removed or edited. The exact commands
are in [`tools/convert.py`](https://github.com/cholmes/portolan-catalog-trimet/blob/main/tools/convert.py).

## Contributing

This catalog is generated, and both halves are open source: the catalog at
[`cholmes/portolan-catalog-trimet`](https://github.com/cholmes/portolan-catalog-trimet) and the
[data browser](https://cholmes.github.io/trimet-data-browser) at
[`cholmes/trimet-data-browser`](https://github.com/cholmes/trimet-data-browser). If something here is wrong or
could be better — a description, a column definition, a query, a style —
[open an issue](https://github.com/cholmes/portolan-catalog-trimet/issues) or send a pull request. Corrections to
the underlying data go to TriMet at [gis@trimet.org](mailto:gis@trimet.org).

## License, and a warning

TriMet distributes these datasets free of charge, but **the terms of use do not
grant redistribution rights**. Section 4 of TriMet's
[Terms of Use](https://developer.trimet.org/terms_of_use.shtml) reserves
reproduction, modification, distribution and republication of site Content
without written consent; the redistribution license in section 5 covers the Web
Services API, not these GIS downloads. The collections therefore declare
`"license": "other"` with a link to those terms, rather than claiming an open
license the source does not offer.

Practically: use the data, and contact **[gis@trimet.org](mailto:gis@trimet.org)** before redistributing
it or building a product on it. If you need transit data under clear open terms,
TriMet's [GTFS feed](https://developer.trimet.org/GTFS.shtml) is the better
starting point.

