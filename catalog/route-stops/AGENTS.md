# TriMet Route Stops — agent guide

Public transit stops for all bus and rail lines. For stops served by multiple lines there are multiple records in this dataset. 8,314 Point features, WGS84, one
GeoParquet file of 323.4 KB in 1 row group(s).

## Access

```sql
INSTALL spatial; LOAD spatial;
INSTALL httpfs;  LOAD httpfs;
SELECT * FROM 'https://data.source.coop/cholmes/trimet/route-stops/route-stops.parquet' LIMIT 10;
```

Reads stream over HTTP range requests — query in place, do not download. The file
is Hilbert-ordered and carries a GeoParquet 1.1 `bbox` covering column, so a
spatial filter on `bbox.xmin` / `bbox.ymin` / `bbox.xmax` / `bbox.ymax` prunes
row groups from metadata alone:

```sql
SELECT * FROM 'https://data.source.coop/cholmes/trimet/route-stops/route-stops.parquet'
WHERE bbox.xmin > -122.70 AND bbox.xmax < -122.60
  AND bbox.ymin >   45.50 AND bbox.ymax <   45.55;
```

The recipes below use bare relative paths (`'route-stops/route-stops.parquet'`) for
readability. Prefix them with `https://data.source.coop/cholmes/trimet/` to run remotely.

Other formats: `route-stops.pmtiles` for map display (layer name `route-stops`), and TriMet's
original Shapefile and KML, linked from `collection.json` as `source_shapefile`
and `source_kml`.

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

- [`stops`](https://data.source.coop/cholmes/trimet/stops/AGENTS.md) — the deduplicated stop list; join on `stop_id`
- [`routes`](https://data.source.coop/cholmes/trimet/routes/AGENTS.md) — route attributes including `public_rte`; join on `(rte, dir)`

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

Practically: use the data, and contact **gis@trimet.org** before redistributing
it or building a product on it. If you need transit data under clear open terms,
TriMet's [GTFS feed](https://developer.trimet.org/GTFS.shtml) is the better
starting point.

