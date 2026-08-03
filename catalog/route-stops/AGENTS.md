# TriMet Route Stops — agent guide

Public transit stops for all bus and rail lines. For stops served by multiple lines there are multiple records in this dataset. 8,314 Point features, WGS84, one
GeoParquet file of 343.6 KB in 1 row group(s).

## Access

```sql
INSTALL spatial; LOAD spatial;
INSTALL httpfs;  LOAD httpfs;
SELECT * FROM 'https://data.source.coop/cholmes/trimet/route-stops/route-stops.parquet' LIMIT 10;
```

Reads stream over HTTP range requests — query in place, do not download. The file
is Hilbert-ordered and carries a GeoParquet 1.1 `bbox` covering column, so a
spatial filter on `geometry_bbox` prunes row groups from metadata alone. Note
the column name: GDAL writes the covering as `<geometry column>_bbox`, so it is
`geometry_bbox` here, not `bbox`.

```sql
-- Coordinates are EPSG:2913 feet, not degrees. This collection spans
-- x 7,531,831–7,730,368, y 595,429–726,731.
SELECT * FROM 'https://data.source.coop/cholmes/trimet/route-stops/route-stops.parquet'
WHERE geometry_bbox.xmin > 7630000 AND geometry_bbox.xmax < 7650000
  AND geometry_bbox.ymin >  680000 AND geometry_bbox.ymax <  700000;
```

The recipes below use bare relative paths (`'route-stops/route-stops.parquet'`) for
readability. Prefix them with [`https://data.source.coop/cholmes/trimet/`](https://source.coop/cholmes/trimet/route-stops/) to run remotely.

Other formats: `route-stops.pmtiles` for map display (layer name `route-stops`), and TriMet's
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

### `frequent` is here but is *not* in TriMet's metadata for this layer

The shapefile carries a `FREQUENT` column. TriMet's metadata page for
`tm_route_stops` does not document it — the page lists ten attributes and this is
not one of them. The definition carried in this catalog's `table:columns` is
borrowed from `tm_routes`, where `FREQUENT` *is* documented, and the column
description says so. Treat it as reliable but formally undocumented upstream.

### The key is `(rte, dir, stop_id)`

No single column is unique. `stop_id` repeats across routes, `(rte, dir)` repeats
across stops, and `stop_seq` repeats across route-directions.

### Average 1.27 routes per stop, but the tail is long

Most stops are served by a single route. The busiest, Clackamas Town Center, is
served by 11. Analyses that assume one route per stop will be right most of the
time and badly wrong at exactly the places that matter.

### `stop_name` agrees with `stops` on every row

Verified: zero disagreements across all 8,314 rows. You can join on `stop_id`
alone without worrying about reconciling names.

### No `public_rte` here

Unlike `routes`, this layer carries only the integer `rte`. To show riders the
public name (FX2 rather than 2), join to `routes` on `(rte, dir)`.

## Query recipes

### The ordered stop list for one route-direction

```sql
SELECT stop_seq, stop_id, stop_name, jurisdic
FROM 'route-stops/route-stops.parquet'
WHERE rte = 9 AND dir = 0
ORDER BY stop_seq;
```

### Transfer points: stops where the most routes meet

```sql
SELECT stop_id, any_value(stop_name) AS stop_name,
       count(DISTINCT rte) AS routes,
       string_agg(DISTINCT type, ', ') AS modes
FROM 'route-stops/route-stops.parquet'
GROUP BY stop_id
ORDER BY routes DESC
LIMIT 15;
```

### Attach public route names by joining back to routes

```sql
SELECT DISTINCT rs.stop_id, rs.stop_name, r.public_rte, r.rte_desc, r.dir_desc
FROM 'route-stops/route-stops.parquet' rs
JOIN 'routes/routes.parquet' r USING (rte, dir)
WHERE rs.stop_id = 13248
ORDER BY r.public_rte;
```

### Stops reachable without a timetable — the Frequent Service stop set

```sql
SELECT count(DISTINCT stop_id) AS frequent_service_stops
FROM 'route-stops/route-stops.parquet'
WHERE frequent = 'True';
```

## Related collections

- [`stops`](https://source.coop/cholmes/trimet/stops/AGENTS.md) — the deduplicated stop list; join on `stop_id`
- [`routes`](https://source.coop/cholmes/trimet/routes/AGENTS.md) — route attributes including `public_rte`; join on `(rte, dir)`

## Provenance

TriMet publishes this as `tm_route_stops` at
[developer.trimet.org/gis](https://developer.trimet.org/gis/), last updated
July 30, 2026. Every column description in `collection.json`
comes from [TriMet's metadata page](https://developer.trimet.org/gis/meta_tm_route_stops.shtml) — that
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

