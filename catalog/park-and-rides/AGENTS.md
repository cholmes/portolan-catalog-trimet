# TriMet Park and Rides — agent guide

TriMet park and ride locations. 46 Point features, WGS84, one
GeoParquet file of 14.7 KB in 1 row group(s).

## Access

```sql
INSTALL spatial; LOAD spatial;
INSTALL httpfs;  LOAD httpfs;
SELECT * FROM 'https://data.source.coop/cholmes/trimet/park-and-rides/park-and-rides.parquet' LIMIT 10;
```

Reads stream over HTTP range requests — query in place, do not download. The file
is Hilbert-ordered and carries a GeoParquet 1.1 `bbox` covering column, so a
spatial filter on `geometry_bbox` prunes row groups from metadata alone. Note
the column name: GDAL writes the covering as `<geometry column>_bbox`, so it is
`geometry_bbox` here, not `bbox`.

```sql
-- Coordinates are EPSG:2913 feet, not degrees. This collection spans
-- x 7,563,860–7,730,536, y 595,297–714,343.
SELECT * FROM 'https://data.source.coop/cholmes/trimet/park-and-rides/park-and-rides.parquet'
WHERE geometry_bbox.xmin > 7630000 AND geometry_bbox.xmax < 7650000
  AND geometry_bbox.ymin >  680000 AND geometry_bbox.ymax <  700000;
```

The recipes below use bare relative paths (`'park-and-rides/park-and-rides.parquet'`) for
readability. Prefix them with [`https://data.source.coop/cholmes/trimet/`](https://source.coop/cholmes/trimet/park-and-rides/) to run remotely.

Other formats: `park-and-rides.pmtiles` for map display (layer name `park-and-rides`), and TriMet's
original Shapefile and KML, linked from `collection.json` as `source_shapefile`
and `source_kml`.

## Coordinate system, and what follows from it

The GeoParquet is in **EPSG:2913** — NAD83(HARN) / Oregon North, **international
feet** — which is what TriMet surveys and publishes in. It is deliberately *not*
reprojected. Only the PMTiles are in WGS84, because vector tiles are Web Mercator
by definition.

The practical consequence is a good one: **measurements just work, in feet.**

```sql
ST_Length(geometry)              -- feet
ST_Area(geometry)                -- square feet
ST_Distance(a.geometry, b.geometry)  -- feet
ST_DWithin(a.geometry, b.geometry, 1312.34)  -- within 400 m
```

Useful conversions: × 0.3048 for metres, ÷ 5280 for miles, ÷ 43560 for acres,
÷ 27878400 for square miles. 400 m is 1312.34 ft, a quarter mile is 1320 ft.

Two things to watch:

- **Coordinates are not longitude and latitude.** An x of 7633099 is feet east
  of the projection's false origin, not a degree. Anything expecting lon/lat —
  a web map, a geocoder, most `GeoJSON` consumers — needs a transform first.
- **`always_xy := true` when you do transform.** Without it DuckDB honours
  EPSG:4326's authority-declared latitude-first axis order and every result
  comes back `Infinity`:

```sql
SELECT ST_AsText(ST_Transform(geometry, 'EPSG:2913', 'EPSG:4326',
                              always_xy := true)) AS lonlat
FROM 'stops/stops.parquet' LIMIT 5;
```

The `bbox` covering column is in the same feet, so a spatial filter written
against it uses projected coordinates, not degrees. The collection's STAC
`extent` stays in WGS84, because STAC requires that regardless of the data's own
CRS.

Nothing here carries a pre-computed length or area except the district boundary,
which has TriMet's own `area_sq_mi` and `acres`.


## Quirks and caveats

### Capacity is extremely skewed — use area, not radius, to draw it

32 TriMet lots hold 11,572 spaces and 14 shared lots hold 929. A linear radius
encoding makes the small lots invisible; `styles/by-capacity.json` scales by
`sqrt(spaces)` so circle *area* tracks capacity.

### `owner` is the strongest predictor of size

Mean TriMet-owned lot: ~362 spaces. Mean shared lot: ~66. If you are modelling
capacity, `owner` is worth carrying as a feature.

### Names overlap with transit centers

Several facilities appear in both layers with different suffixes — see the
`transit-centers` guide. Join spatially rather than by name.

### All 46 are `Existing`

`Planned` and `UC` are documented but unused here.

### `spaces` is never null in this snapshot

Every one of the 46 rows has a positive space count, so you do not need to
handle nulls — but do not assume that holds in a future vintage.

## Query recipes

### Capacity by ownership

```sql
SELECT owner, count(*) AS lots, sum(spaces) AS spaces,
       round(avg(spaces)) AS mean_lot
FROM 'park-and-rides/park-and-rides.parquet'
GROUP BY owner;
```

### The largest facilities

```sql
SELECT name, city, county, owner, spaces
FROM 'park-and-rides/park-and-rides.parquet'
ORDER BY spaces DESC
LIMIT 10;
```

### Park and ride capacity served by rail

```sql
SELECT CASE WHEN r.station IS NULL THEN 'bus only' ELSE 'rail-served' END AS access,
       count(DISTINCT p.name) AS lots, sum(DISTINCT p.spaces) AS spaces
FROM 'park-and-rides/park-and-rides.parquet' p
LEFT JOIN 'rail-stops/rail-stops.parquet' r
  ON ST_DWithin(p.geometry, r.geometry, 1312.34)
GROUP BY 1;
```

## Related collections

- [`transit-centers`](https://source.coop/cholmes/trimet/transit-centers/AGENTS.md) — many park and rides sit at a transit center
- [`rail-stops`](https://source.coop/cholmes/trimet/rail-stops/AGENTS.md) — the large lots are mostly on MAX

## Provenance

TriMet publishes this as `tm_parkride` at
[developer.trimet.org/gis](https://developer.trimet.org/gis/), last updated
June 23, 2026. Every column description in `collection.json`
comes from [TriMet's metadata page](https://developer.trimet.org/gis/meta_tm_parkride.shtml) — that
page, not this catalog, is the authority on what a field means.

Conversion: `ogr2ogr -f Parquet -t_srs EPSG:4326 -lco COMPRESSION=ZSTD -lco
SORT_BY_BBOX=YES -lco WRITE_COVERING_BBOX=YES`, then tippecanoe with `-r1
--no-feature-limit` so no feature is dropped at any zoom. See
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

