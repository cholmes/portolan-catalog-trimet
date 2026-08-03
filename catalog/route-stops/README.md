# TriMet Route Stops

Public transit stops for all bus and rail lines. For stops served by multiple lines there are multiple records in this dataset. **8,314 Point features** covering the TriMet
service district in the Portland, Oregon metropolitan area, published by TriMet
as `tm_route_stops` and last updated at the source on
**July 30, 2026**.

The same stops as `stops`, but exploded by the service that calls at them: one
row per stop per route-direction, 8,314 rows over 6,316 distinct stops. A stop
served by four routes appears four times.

This is the only layer in the catalog that connects a stop to a route, and it
carries `stop_seq`, the position of the stop along its route-direction, which is
what lets you reconstruct the order of stops along a line.

> **Agents:** see [AGENTS.md](https://source.coop/cholmes/trimet/route-stops/AGENTS.md) for join keys, verified query recipes
> and the caveats that will otherwise cost you a wrong answer.

[![TriMet Route Stops](https://data.source.coop/cholmes/trimet/route-stops/thumbnail.webp)](https://cholmes.github.io/trimet-data-browser)

### 🗺️ [Open this collection in the data browser →](https://cholmes.github.io/trimet-data-browser)

Preview it on a map, inspect the schema and license, and download the
GeoParquet or PMTiles directly.

## Quick start

Read it straight from object storage — DuckDB fetches only the byte ranges it
needs, so there is nothing to download first:

```sql
INSTALL spatial; LOAD spatial;
INSTALL httpfs;  LOAD httpfs;

SELECT * FROM 'https://data.source.coop/cholmes/trimet/route-stops/route-stops.parquet' LIMIT 10;
```

Or with GeoPandas:

```python
import geopandas as gpd
gdf = gpd.read_parquet("https://data.source.coop/cholmes/trimet/route-stops/route-stops.parquet")
```

## Suggested uses

- Building the stop sequence for a route — the ordered list a timetable or a
  routing engine needs.
- Finding transfer points: stops where many distinct `rte` values meet.
- Answering "which routes serve this stop" and "which stops does this route
  serve", neither of which any other layer here can do.

## Limitations and inappropriate uses

- **Every count is inflated unless you deduplicate.** `count(*)` is 8,314, which
  is not a number of stops. Use `count(DISTINCT stop_id)` for stops, or work from
  the `stops` collection.
- **`stop_seq` restarts at every route-direction.** It is meaningful only within
  a `(rte, dir)` group. Ordering the whole table by `stop_seq` is meaningless.
- **No times, no frequencies.** Sequence is order, not schedule. Nothing says how
  long it takes to get from stop 4 to stop 5.
- **Directions are not mirror images.** The stop list for `dir = 0` and `dir = 1`
  of the same route often differs in length, because of one-way streets and
  stops served in one direction only.

## Schema

| Column | Type | Description |
|---|---|---|
| `rte` | int32 | Route number. |
| `dir` | int32 | Direction of line serving this stop.<br>Values: `0` Direction 0; `1` Direction 1. |
| `rte_desc` | string | Route name. |
| `dir_desc` | string | Description of route direction. |
| `type` | string | Type of service.<br>Values: `AT` Aerial Tram; `BUS` Bus; `CR` Commuter rail; `MAX` Light rail; `SC` Streetcar. |
| `stop_seq` | int32 | Stop sequence number. |
| `stop_id` | int32 | Unique identifier. |
| `stop_name` | string | Intersection or street address of stop. |
| `jurisdic` | string | Jurisdiction (City or County) in which stop is located. |
| `zipcode` | string | Zipcode in which stop is located. |
| `frequent` | string | Indicates whether a route or route segment has frequent service.<br>Values: `True` Route segment has frequent service; `False` Route segment does not have frequent service. |
| `geometry` | binary | Feature geometry, WGS84 lon/lat. |
| `geometry_bbox` | struct<xmin: float not null, ymin: float not null, xmax: float not null, ymax: float not null> | GeoParquet 1.1 covering column, for row-group pruning. Same projected feet as the geometry. |

Column descriptions are TriMet's own, taken verbatim from
[meta_tm_route_stops.shtml](https://developer.trimet.org/gis/meta_tm_route_stops.shtml). The same text is carried in
`table:columns` in [collection.json](https://source.coop/cholmes/trimet/route-stops/collection.json).

## Visualization

| Style | What it shows |
|---|---|
| [`default.json`](https://source.coop/cholmes/trimet/route-stops/styles/default.json) | One mark per stop per route-direction, colored by TYPE. Because a stop served by several routes appears several times, marks are drawn semi-transparent — the busiest transfer points show up as the darkest spots on the map. |
| [`by-direction.json`](https://source.coop/cholmes/trimet/route-stops/styles/by-direction.json) | Splits stops on DIR. Along a two-way corridor the inbound and outbound stops sit on opposite sides of the street, so this style shows the paired-stop structure of the network directly. |
| [`by-sequence.json`](https://source.coop/cholmes/trimet/route-stops/styles/by-sequence.json) | Ramps color across STOP_SEQ, the position of a stop along its route-direction. Following the ramp traces the direction of travel, and the gradient makes route ends easy to pick out. Sequence numbers restart at every route-direction, so the ramp is only meaningful when the view is filtered to one route. |
| [`frequent-service.json`](https://source.coop/cholmes/trimet/route-stops/styles/frequent-service.json) | Stops on route-directions flagged FREQUENT, drawn over the rest. This is the stop-level companion to the routes Frequent Service style, and it answers a question the routes layer cannot: which stops a rider can use without consulting a timetable. |

The PMTiles layer is named `route-stops`. Styles reference it as `../route-stops.pmtiles`,
so they load unmodified against this directory.

## Files

| File | Size | What it is |
|---|---|---|
| [`route-stops.parquet`](https://data.source.coop/cholmes/trimet/route-stops/route-stops.parquet) | 343.6 KB | GeoParquet 1.1, 8,314 rows in 1 row group(s), zstd, Hilbert-ordered, bbox covering column |
| [`route-stops.pmtiles`](https://data.source.coop/cholmes/trimet/route-stops/route-stops.pmtiles) | 2.3 MB | Vector tiles for display, every feature kept at every zoom |
| [`thumbnail.webp`](https://data.source.coop/cholmes/trimet/route-stops/thumbnail.webp) | 48.5 KB | Rendered from `styles/default.json` over a light basemap |
| [`collection.json`](https://source.coop/cholmes/trimet/route-stops/collection.json) | — | STAC Collection metadata |

## Provenance

[![TriMet](https://data.source.coop/cholmes/trimet/_assets/trimet-logo.png)](https://developer.trimet.org/gis/)

Produced by **TriMet GIS** (4012 SE 17th Ave, GIS3,
Portland, OR 97202,
[gis@trimet.org](mailto:gis@trimet.org)) and distributed at
[developer.trimet.org/gis](https://developer.trimet.org/gis/) as `tm_route_stops`.

The originals are linked as assets and are the authoritative copy:
[Shapefile](https://developer.trimet.org/gis/data/tm_route_stops.zip) · [KML](https://developer.trimet.org/gis/data/tm_route_stops.kml) · [Metadata](https://developer.trimet.org/gis/meta_tm_route_stops.shtml)

This collection was produced by reprojecting TriMet's Shapefile from
EPSG:2913 (NAD83(HARN) / Oregon North (ft)) to EPSG:4326 and writing GeoParquet and
PMTiles. No features were added, removed or edited. The exact commands are in
[`tools/convert.py`](https://github.com/cholmes/portolan-catalog-trimet/blob/main/tools/convert.py).

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

