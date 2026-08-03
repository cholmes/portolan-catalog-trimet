# TriMet Park and Rides

TriMet park and ride locations. **46 Point features** covering the TriMet
service district in the Portland, Oregon metropolitan area, published by TriMet
as `tm_parkride` and last updated at the source on
**June 23, 2026**.

The 46 park and ride facilities in the TriMet system, with a parking-space count
for each — 12,501 spaces in total. 32 are TriMet-owned and hold 11,572 spaces
between them; the other 14 are shared-use arrangements with other property
owners and hold 929.

The largest is the 750-space Clackamas Town Center garage; the median lot is far
smaller, so capacity is heavily concentrated in a handful of facilities.

> **Agents:** see [AGENTS.md](https://source.coop/cholmes/trimet/park-and-rides/AGENTS.md) for join keys, verified query recipes
> and the caveats that will otherwise cost you a wrong answer.

[![TriMet Park and Rides](https://data.source.coop/cholmes/trimet/park-and-rides/thumbnail.webp)](https://cholmes.github.io/trimet-data-browser)

### 🗺️ [Open this collection in the data browser →](https://cholmes.github.io/trimet-data-browser)

Preview it on a map, inspect the schema and license, and download the
GeoParquet or PMTiles directly.

## Quick start

Read it straight from object storage — DuckDB fetches only the byte ranges it
needs, so there is nothing to download first:

```sql
INSTALL spatial; LOAD spatial;
INSTALL httpfs;  LOAD httpfs;

SELECT * FROM 'https://data.source.coop/cholmes/trimet/park-and-rides/park-and-rides.parquet' LIMIT 10;
```

Or with GeoPandas:

```python
import geopandas as gpd
gdf = gpd.read_parquet("https://data.source.coop/cholmes/trimet/park-and-rides/park-and-rides.parquet")
```

## Suggested uses

- Park-and-ride capacity analysis, which the `spaces` column supports directly.
- Locating the drive-to-transit entry points of the network.
- Pairing capacity with rail access — most of the large lots sit on MAX.

## Limitations and inappropriate uses

- **`spaces` is nominal capacity, not availability.** Nothing here says whether a
  lot is full, and TriMet's own real-time occupancy is a separate service.
- **Shared-use lots are conditional.** The 14 `Shared` facilities are used under
  agreement with another owner; spaces may be restricted by time of day or
  removed if the agreement changes. Do not treat them as equivalent to
  TriMet-owned capacity.
- **The point is the facility, not the entrance.** For drive-access routing you
  need the actual driveway, which is not in this data.
- **No fees, no restrictions, no permit information.**

## Schema

| Column | Type | Description |
|---|---|---|
| `name` | string | Name of park and ride. |
| `address` | string | Park and ride street address or major intersection. |
| `city` | string | City in which park and ride is located. |
| `county` | string | County in which park and ride is located. |
| `zipcode` | string | Zipcode in which park and ride is located. |
| `owner` | string | Indicates whether a park and ride is TriMet owned or a shared use facility.<br>Values: `TriMet` TriMet owned; `Shared` Shared use. |
| `spaces` | int32 | Indicates number of parking spaces available at park and ride. |
| `status` | string | Operational status of park and ride.<br>Values: `Existing` Park and ride is operational; `Planned` Park and ride is in advanced planning stages; `UC` Park and ride is under construction. |
| `geometry` | binary | Feature geometry, WGS84 lon/lat. |
| `geometry_bbox` | struct<xmin: float not null, ymin: float not null, xmax: float not null, ymax: float not null> | GeoParquet 1.1 covering column, for row-group pruning. Same projected feet as the geometry. |

Column descriptions are TriMet's own, taken verbatim from
[meta_tm_parkride.shtml](https://developer.trimet.org/gis/meta_tm_parkride.shtml). The same text is carried in
`table:columns` in [collection.json](https://source.coop/cholmes/trimet/park-and-rides/collection.json).

## Visualization

| Style | What it shows |
|---|---|
| [`default.json`](https://source.coop/cholmes/trimet/park-and-rides/styles/default.json) | The 46 park and ride facilities in TriMet blue. A steady mark size makes this the right style when the question is where the lots are rather than how big they are. |
| [`by-capacity.json`](https://source.coop/cholmes/trimet/park-and-rides/styles/by-capacity.json) | Scales each mark by SPACES and ramps its color with it, over a range that runs from small lots up to the 750-space Clackamas Town Center garage. Area, not radius, tracks capacity, so a lot that looks twice as big holds roughly twice as many cars. The whole system holds 12,501 spaces. |
| [`by-owner.json`](https://source.coop/cholmes/trimet/park-and-rides/styles/by-owner.json) | Separates the 32 TriMet-owned lots from the 14 shared-use facilities. The distinction matters in practice: shared lots are much smaller, 929 spaces between them against 11,572 in the TriMet-owned lots, and their availability depends on an agreement with the property owner. |
| [`labeled.json`](https://source.coop/cholmes/trimet/park-and-rides/styles/labeled.json) | Capacity-scaled marks labeled with the facility name and its space count, so a reader can identify a specific lot without clicking it. |

The PMTiles layer is named `park-and-rides`. Styles reference it as `../park-and-rides.pmtiles`,
so they load unmodified against this directory.

## Files

| File | Size | What it is |
|---|---|---|
| [`park-and-rides.parquet`](https://data.source.coop/cholmes/trimet/park-and-rides/park-and-rides.parquet) | 14.7 KB | GeoParquet 1.1, 46 rows in 1 row group(s), zstd, Hilbert-ordered, bbox covering column |
| [`park-and-rides.pmtiles`](https://data.source.coop/cholmes/trimet/park-and-rides/park-and-rides.pmtiles) | 61.1 KB | Vector tiles for display, every feature kept at every zoom |
| [`thumbnail.webp`](https://data.source.coop/cholmes/trimet/park-and-rides/thumbnail.webp) | 46.8 KB | Rendered from `styles/default.json` over a light basemap |
| [`collection.json`](https://source.coop/cholmes/trimet/park-and-rides/collection.json) | — | STAC Collection metadata |

## Provenance

[![TriMet](https://data.source.coop/cholmes/trimet/_assets/trimet-logo.png)](https://developer.trimet.org/gis/)

Produced by **TriMet GIS** (4012 SE 17th Ave, GIS3,
Portland, OR 97202,
[gis@trimet.org](mailto:gis@trimet.org)) and distributed at
[developer.trimet.org/gis](https://developer.trimet.org/gis/) as `tm_parkride`.

The originals are linked as assets and are the authoritative copy:
[Shapefile](https://developer.trimet.org/gis/data/tm_parkride.zip) · [KML](https://developer.trimet.org/gis/data/tm_parkride.kml) · [Metadata](https://developer.trimet.org/gis/meta_tm_parkride.shtml)

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

