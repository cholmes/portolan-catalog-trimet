# TriMet Stops

Active transit stops. **6,316 Point features** covering the TriMet
service district in the Portland, Oregon metropolitan area, published by TriMet
as `tm_stops` and last updated at the source on
**July 30, 2026**.

Every active TriMet stop, deduplicated — one row per physical stop, 6,316 of
them. 6,075 are bus stops; the rest are 161 MAX platforms, 58 streetcar stops, 14
shared bus/streetcar stops, 6 WES platforms and 2 aerial tram terminals.

`stop_id` is TriMet's public stop number, the one printed on the pole and used by
the arrivals API, which makes this collection the natural bridge between this
catalog and TriMet's real-time services.

> **Agents:** see [AGENTS.md](https://source.coop/cholmes/trimet/stops/AGENTS.md) for join keys, verified query recipes
> and the caveats that will otherwise cost you a wrong answer.

[![TriMet Stops](https://data.source.coop/cholmes/trimet/stops/thumbnail.webp)](https://cholmes.github.io/trimet-data-browser)

### 🗺️ [Open this collection in the data browser →](https://cholmes.github.io/trimet-data-browser)

Preview it on a map, inspect the schema and license, and download the
GeoParquet or PMTiles directly.

## Quick start

Read it straight from object storage — DuckDB fetches only the byte ranges it
needs, so there is nothing to download first:

```sql
INSTALL spatial; LOAD spatial;
INSTALL httpfs;  LOAD httpfs;

SELECT * FROM 'https://data.source.coop/cholmes/trimet/stops/stops.parquet' LIMIT 10;
```

Or with GeoPandas:

```python
import geopandas as gpd
gdf = gpd.read_parquet("https://data.source.coop/cholmes/trimet/stops/stops.parquet")
```

## Suggested uses

- Transit-access analysis: how many people, jobs or addresses lie within a walk
  of a stop.
- Joining spatial data to TriMet's real-time arrivals, which is keyed on the same
  `stop_id`.
- Stop-density and coverage mapping — `styles/density.json` is built for this.

## Limitations and inappropriate uses

- **Active stops only.** Discontinued stops are absent, so this is a snapshot and
  not a history. `stop_id` values are not re-issued, but a stop that vanishes
  between vintages simply disappears.
- **No service information.** Which routes serve a stop is not in this file; that
  is what `route-stops` is for. Nor is there any frequency, shelter, accessibility
  or boarding-count attribute.
- **`stop_name` is a location, not a name.** Values are intersections or street
  addresses ("SE Hawthorne & 39th"), so they are not unique and not suitable as
  display names for rail stations — use `rail-stops.station` for those.
- **Position is the pole, not the boarding area.** Stops on opposite sides of a
  street are separate features a few metres apart; do not treat a stop as a
  single bidirectional node without checking.

## Schema

| Column | Type | Description |
|---|---|---|
| `stop_id` | int32 | Unique identifier. |
| `stop_name` | string | Intersection or street address of stop. |
| `jurisdic` | string | Jurisdiction (City or County) in which stop is located. |
| `zipcode` | string | Zipcode in which stop is located. |
| `type` | string | Type of service.<br>Values: `AT` Aerial Tram; `BUS` Bus; `CR` Commuter rail; `MAX` Light rail; `SC` Streetcar; `BSC` Shared Bus and Streetcar. |
| `geometry` | binary | Feature geometry, WGS84 lon/lat. |
| `geometry_bbox` | struct<xmin: float not null, ymin: float not null, xmax: float not null, ymax: float not null> | GeoParquet 1.1 covering column, for row-group pruning. Same projected feet as the geometry. |

Column descriptions are TriMet's own, taken verbatim from
[meta_tm_stops.shtml](https://developer.trimet.org/gis/meta_tm_stops.shtml). The same text is carried in
`table:columns` in [collection.json](https://source.coop/cholmes/trimet/stops/collection.json).

## Visualization

| Style | What it shows |
|---|---|
| [`default.json`](https://source.coop/cholmes/trimet/stops/styles/default.json) | TriMet's own stop symbol, taken from the GeoServer style `ott:stops`: a white circle with a dark stroke. Radius grows with zoom so all 6,316 stops stay separable in dense corridors. |
| [`by-type.json`](https://source.coop/cholmes/trimet/stops/styles/by-type.json) | The same mark filled by TYPE, so the 6,075 bus stops read apart from the 161 MAX platforms, 58 streetcar stops, 14 shared bus/streetcar stops, 6 WES platforms and 2 aerial tram terminals. Colors are TriMet's GTFS route_color values for each mode. |
| [`density.json`](https://source.coop/cholmes/trimet/stops/styles/density.json) | A heatmap of stop density that fades into individual marks past zoom 13. Useful for seeing where the network is dense without drawing thousands of overlapping circles at metro-wide zooms. |
| [`labeled.json`](https://source.coop/cholmes/trimet/stops/styles/labeled.json) | Stops colored by mode with STOP_NAME shown from zoom 14. Stop names are intersections or street addresses, so they read as cross-streets rather than as station names. |

The PMTiles layer is named `stops`. Styles reference it as `../stops.pmtiles`,
so they load unmodified against this directory.

## Files

| File | Size | What it is |
|---|---|---|
| [`stops.parquet`](https://data.source.coop/cholmes/trimet/stops/stops.parquet) | 287.9 KB | GeoParquet 1.1, 6,316 rows in 1 row group(s), zstd, Hilbert-ordered, bbox covering column |
| [`stops.pmtiles`](https://data.source.coop/cholmes/trimet/stops/stops.pmtiles) | 1.5 MB | Vector tiles for display, every feature kept at every zoom |
| [`thumbnail.webp`](https://data.source.coop/cholmes/trimet/stops/thumbnail.webp) | 48.4 KB | Rendered from `styles/default.json` over a light basemap |
| [`collection.json`](https://source.coop/cholmes/trimet/stops/collection.json) | — | STAC Collection metadata |

## Provenance

[![TriMet](https://data.source.coop/cholmes/trimet/_assets/trimet-logo.png)](https://developer.trimet.org/gis/)

Produced by **TriMet GIS** (4012 SE 17th Ave, GIS3,
Portland, OR 97202,
[gis@trimet.org](mailto:gis@trimet.org)) and distributed at
[developer.trimet.org/gis](https://developer.trimet.org/gis/) as `tm_stops`.

The originals are linked as assets and are the authoritative copy:
[Shapefile](https://developer.trimet.org/gis/data/tm_stops.zip) · [KML](https://developer.trimet.org/gis/data/tm_stops.kml) · [Metadata](https://developer.trimet.org/gis/meta_tm_stops.shtml)

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

