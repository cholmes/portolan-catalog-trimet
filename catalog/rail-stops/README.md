# TriMet Rail Stops

Public transit rail stops. Includes existing, under construction, and planned MAX, WES, and Portland Streetcar stops. The data have been generalized to improve cartographic display at smaller scales. **169 Point features** covering the TriMet
service district in the Portland, Oregon metropolitan area, published by TriMet
as `tm_rail_stops` and last updated at the source on
**December 04, 2024**.

The 169 MAX, WES and Portland Streetcar stops, generalized for cartographic
display and carrying real **station names** rather than intersections. Each stop
records the line or lines that serve it in the same `line` code space as
`rail-lines`, so the two layers style consistently.

> **Agents:** see [AGENTS.md](https://source.coop/cholmes/trimet/rail-stops/AGENTS.md) for join keys, verified query recipes
> and the caveats that will otherwise cost you a wrong answer.

[![TriMet Rail Stops](https://data.source.coop/cholmes/trimet/rail-stops/thumbnail.webp)](https://cholmes.github.io/trimet-data-browser)

### 🗺️ [Explore this collection on an interactive map →](https://cholmes.github.io/trimet-data-browser)

## Quick start

Read it straight from object storage — DuckDB fetches only the byte ranges it
needs, so there is nothing to download first:

```sql
INSTALL spatial; LOAD spatial;
INSTALL httpfs;  LOAD httpfs;

SELECT * FROM 'https://data.source.coop/cholmes/trimet/rail-stops/rail-stops.parquet' LIMIT 10;
```

Or with GeoPandas:

```python
import geopandas as gpd
gdf = gpd.read_parquet("https://data.source.coop/cholmes/trimet/rail-stops/rail-stops.parquet")
```

## Suggested uses

- Labelling rail maps. `styles/labeled.json` is the reason this collection exists
  in a mirror — `station` gives you the names riders actually use.
- Identifying interchange stations, which are the stops whose `line` code lists
  several services.
- Pairing with `rail-lines` to draw a complete, correctly-colored rail diagram.

## Limitations and inappropriate uses

- **Generalized positions.** As with `rail-lines`, TriMet states this data has
  been generalized for display at smaller scales. Platform positions are
  approximate; do not use them for pedestrian routing or precise accessibility
  work.
- **There is no `stop_id` here.** This layer does not carry TriMet's public stop
  number, so it does not join to `stops` or `route-stops` on an id. Matching must
  be spatial or by name, and neither is exact.
- **A station is one point, not one per platform.** Directional platforms are
  collapsed, so counts here are lower than the rail stop counts in `stops`
  (169 versus 161 MAX plus 58 streetcar plus 6 WES rows there).

## Schema

| Column | Type | Description |
|---|---|---|
| `station` | string | Name of station. |
| `line` | string | Line(s) serving a particular stop.<br>Values: `AL` Portland Streetcar A Loop; `AL/BL` Portland Streetcar A & B Loops; `B` MAX Blue Line; `BGR` MAX Blue, Green, and Red Lines; `BGRY` MAX Blue, Green, Red, and Yellow Lines; `BL` Portland Streetcar B Loop; `BL/NS` Portland Streetcar B Loop and North/South Line; `BR` MAX Blue and Red Lines; `G` MAX Green Line; `GO` MAX Green and Orange Lines; `GY` MAX Green and Yellow Lines; `NS` Portland Streetcar North/South Line; `NS/AL` Portland Streetcar A Loop and North/South Line; `NS/AL/BL` Portland Streetcar A & B Loops and North/South Line; `O` MAX Orange Line; `R` MAX Red Line; `WES` WES (Westside Express Service); `Y` MAX Yellow Line. |
| `status` | string | Operational status of the stop.<br>Values: `Existing` Service currently provided at rail stop; `Planned` Rail stop in advanced planning stages; `UC` Rail stop is under construction. |
| `type` | string | Type of service.<br>Values: `CR` Commuter rail; `MAX` Light rail; `SC` Streetcar. |
| `geometry` | binary | Feature geometry, WGS84 lon/lat. |
| `geometry_bbox` | struct<xmin: float not null, ymin: float not null, xmax: float not null, ymax: float not null> | GeoParquet 1.1 covering column, for row-group pruning. Same projected feet as the geometry. |

Column descriptions are TriMet's own, taken verbatim from
[meta_tm_rail_stops.shtml](https://developer.trimet.org/gis/meta_tm_rail_stops.shtml). The same text is carried in
`table:columns` in [collection.json](https://source.coop/cholmes/trimet/rail-stops/collection.json).

## Visualization

| Style | What it shows |
|---|---|
| [`default.json`](https://source.coop/cholmes/trimet/rail-stops/styles/default.json) | Station marks filled with the color of the line that serves them, using the same palette as TriMet's `ott:rail` style so this layer sits correctly on top of the rail-lines default style. Stations on shared track take the trunk line's color; the LINE code itself records the full set of services. |
| [`by-type.json`](https://source.coop/cholmes/trimet/rail-stops/styles/by-type.json) | Three marks instead of eighteen: light rail, streetcar and commuter rail. MAX platforms are drawn largest and WES smallest, matching the relative prominence TriMet gives each mode in its own line styling. |
| [`labeled.json`](https://source.coop/cholmes/trimet/rail-stops/styles/labeled.json) | Line-colored station marks with STATION names. Unlike the bus stop names, these are real station names, which makes this the most useful style for orienting a reader on the rail network. |

The PMTiles layer is named `rail-stops`. Styles reference it as `../rail-stops.pmtiles`,
so they load unmodified against this directory.

## Files

| File | Size | What it is |
|---|---|---|
| [`rail-stops.parquet`](https://data.source.coop/cholmes/trimet/rail-stops/rail-stops.parquet) | 17.1 KB | GeoParquet 1.1, 169 rows in 1 row group(s), zstd, Hilbert-ordered, bbox covering column |
| [`rail-stops.pmtiles`](https://data.source.coop/cholmes/trimet/rail-stops/rail-stops.pmtiles) | 60.7 KB | Vector tiles for display, every feature kept at every zoom |
| [`thumbnail.webp`](https://data.source.coop/cholmes/trimet/rail-stops/thumbnail.webp) | 48.7 KB | Rendered from `styles/default.json` over a light basemap |
| [`collection.json`](https://source.coop/cholmes/trimet/rail-stops/collection.json) | — | STAC Collection metadata |

## Provenance

[![TriMet](https://data.source.coop/cholmes/trimet/_assets/trimet-logo.png)](https://developer.trimet.org/gis/)

Produced by **TriMet GIS** (4012 SE 17th Ave, GIS3,
Portland, OR 97202,
[gis@trimet.org](mailto:gis@trimet.org)) and distributed at
[developer.trimet.org/gis](https://developer.trimet.org/gis/) as `tm_rail_stops`.

The originals are linked as assets and are the authoritative copy:
[Shapefile](https://developer.trimet.org/gis/data/tm_rail_stops.zip) · [KML](https://developer.trimet.org/gis/data/tm_rail_stops.kml) · [Metadata](https://developer.trimet.org/gis/meta_tm_rail_stops.shtml)

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

