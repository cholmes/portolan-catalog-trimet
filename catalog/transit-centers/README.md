# TriMet Transit Centers

Transit Centers. **15 Point features** covering the TriMet
service district in the Portland, Oregon metropolitan area, published by TriMet
as `tm_tran_cen` and last updated at the source on
**July 31, 2024**.

The 15 transit centers — the timed-transfer hubs where many routes meet and where
riders are expected to change. Each carries a name, street address, city, county
and ZIP code.

They span all three counties of the district: 7 in Multnomah, 5 in Washington and
3 in Clackamas.

> **Agents:** see [AGENTS.md](https://source.coop/cholmes/trimet/transit-centers/AGENTS.md) for join keys, verified query recipes
> and the caveats that will otherwise cost you a wrong answer.

[![TriMet Transit Centers](https://data.source.coop/cholmes/trimet/transit-centers/thumbnail.webp)](https://cholmes.github.io/trimet-data-browser)

### 🗺️ [Explore this collection on an interactive map →](https://cholmes.github.io/trimet-data-browser)

## Quick start

Read it straight from object storage — DuckDB fetches only the byte ranges it
needs, so there is nothing to download first:

```sql
INSTALL spatial; LOAD spatial;
INSTALL httpfs;  LOAD httpfs;

SELECT * FROM 'https://data.source.coop/cholmes/trimet/transit-centers/transit-centers.parquet' LIMIT 10;
```

Or with GeoPandas:

```python
import geopandas as gpd
gdf = gpd.read_parquet("https://data.source.coop/cholmes/trimet/transit-centers/transit-centers.parquet")
```

## Suggested uses

- Anchoring network maps: 15 labelled points give a reader the shape of the
  system in one screen, which is what `styles/labeled.json` is for.
- Defining hub catchments for access analysis.
- As the join target for "how much service is concentrated here" questions,
  answered spatially against `stops` or `route-stops`.

## Limitations and inappropriate uses

- **A transit center is not a rail station.** Some are, some are bus-only. The
  layer carries no mode attribute; determine mode by joining spatially to
  `rail-stops` or `stops`.
- **The point is the facility, not each platform.** A transit center may have a
  dozen bus bays; there is one point for all of them.
- **No capacity, amenity or accessibility data.** Only location and address.
- **`status` exists but every row is `Existing`.** No planned hubs appear in this
  snapshot.

## Schema

| Column | Type | Description |
|---|---|---|
| `name` | string | Name of Transit Center. |
| `address` | string | Transit Center street address or major intersection. |
| `city` | string | City in which Transit Center is located. |
| `county` | string | County in which Transit Center is located. |
| `zipcode` | string | Zipcode in which Transit Center is located. |
| `status` | string | Operational status of segment.<br>Values: `Existing` Transit Center is operational; `Planned` Transit Center is in advanced planning stages; `UC` Transit Center is under construction. |
| `geometry` | binary | Feature geometry, WGS84 lon/lat. |
| `geometry_bbox` | struct<xmin: float not null, ymin: float not null, xmax: float not null, ymax: float not null> | GeoParquet 1.1 covering column, for row-group pruning. Same projected feet as the geometry. |

Column descriptions are TriMet's own, taken verbatim from
[meta_tm_tran_cen.shtml](https://developer.trimet.org/gis/meta_tm_tran_cen.shtml). The same text is carried in
`table:columns` in [collection.json](https://source.coop/cholmes/trimet/transit-centers/collection.json).

## Visualization

| Style | What it shows |
|---|---|
| [`default.json`](https://source.coop/cholmes/trimet/transit-centers/styles/default.json) | The fifteen transit centers as prominent marks in TriMet brand orange. These are the network's timed-transfer hubs, so they are drawn larger than ordinary stops and stay visible at low zoom. |
| [`by-county.json`](https://source.coop/cholmes/trimet/transit-centers/styles/by-county.json) | Colors the hubs by COUNTY. TriMet's district spans Multnomah, Washington and Clackamas counties, and this style shows how the transfer hubs are distributed across the three. |
| [`labeled.json`](https://source.coop/cholmes/trimet/transit-centers/styles/labeled.json) | Transit center marks with NAME shown from zoom 9. Fifteen labels never collide, so this style works as a standalone overview of the network's hub structure. |

The PMTiles layer is named `transit-centers`. Styles reference it as `../transit-centers.pmtiles`,
so they load unmodified against this directory.

## Files

| File | Size | What it is |
|---|---|---|
| [`transit-centers.parquet`](https://data.source.coop/cholmes/trimet/transit-centers/transit-centers.parquet) | 11.7 KB | GeoParquet 1.1, 15 rows in 1 row group(s), zstd, Hilbert-ordered, bbox covering column |
| [`transit-centers.pmtiles`](https://data.source.coop/cholmes/trimet/transit-centers/transit-centers.pmtiles) | 21.8 KB | Vector tiles for display, every feature kept at every zoom |
| [`thumbnail.webp`](https://data.source.coop/cholmes/trimet/transit-centers/thumbnail.webp) | 47.3 KB | Rendered from `styles/default.json` over a light basemap |
| [`collection.json`](https://source.coop/cholmes/trimet/transit-centers/collection.json) | — | STAC Collection metadata |

## Provenance

[![TriMet](https://data.source.coop/cholmes/trimet/_assets/trimet-logo.png)](https://developer.trimet.org/gis/)

Produced by **TriMet GIS** (4012 SE 17th Ave, GIS3,
Portland, OR 97202,
[gis@trimet.org](mailto:gis@trimet.org)) and distributed at
[developer.trimet.org/gis](https://developer.trimet.org/gis/) as `tm_tran_cen`.

The originals are linked as assets and are the authoritative copy:
[Shapefile](https://developer.trimet.org/gis/data/tm_tran_cen.zip) · [KML](https://developer.trimet.org/gis/data/tm_tran_cen.kml) · [Metadata](https://developer.trimet.org/gis/meta_tm_tran_cen.shtml)

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

