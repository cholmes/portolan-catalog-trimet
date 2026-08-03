# TriMet Stops — agent guide

Active transit stops. 6,316 Point features, WGS84, one
GeoParquet file of 268.9 KB in 1 row group(s).

## Access

```sql
INSTALL spatial; LOAD spatial;
INSTALL httpfs;  LOAD httpfs;
SELECT * FROM 'https://data.source.coop/cholmes/trimet/stops/stops.parquet' LIMIT 10;
```

Reads stream over HTTP range requests — query in place, do not download. The file
is Hilbert-ordered and carries a GeoParquet 1.1 `bbox` covering column, so a
spatial filter on `bbox.xmin` / `bbox.ymin` / `bbox.xmax` / `bbox.ymax` prunes
row groups from metadata alone:

```sql
SELECT * FROM 'https://data.source.coop/cholmes/trimet/stops/stops.parquet'
WHERE bbox.xmin > -122.70 AND bbox.xmax < -122.60
  AND bbox.ymin >   45.50 AND bbox.ymax <   45.55;
```

The recipes below use bare relative paths (`'stops/stops.parquet'`) for
readability. Prefix them with `https://data.source.coop/cholmes/trimet/` to run remotely.

Other formats: `stops.pmtiles` for map display (layer name `stops`), and TriMet's
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

### `stop_id` joins cleanly to `route-stops` — exactly

All 6,316 `stop_id` values here appear in `route-stops`, and `route-stops` has
exactly 6,316 distinct `stop_id` values. The two agree perfectly, and `stop_name`
never disagrees between them. This is the catalog's most reliable join.

### `type` has a value here that the routes layer does not

`BSC`, "Shared Bus and Streetcar", appears on 14 stops. It is documented on the
stops metadata page but not on the routes or route-stops pages, and it does not
occur in those layers. Code that maps `type` through a lookup built from
`routes` will miss it.

### `zipcode` is a string; `stop_id` is an integer

`zipcode` is text (leading zeros are not an issue in Oregon, but the column is
still typed as a string). `stop_id` is `int32` — do not quote it when joining.

### The same `stop_id` is used by TriMet's arrivals API

`stop_id` is the public stop number. It is the `locIDs` parameter of TriMet's
arrivals endpoint, which is how you get from a point in this catalog to live
data. That API needs a registered app ID and is governed by separate terms.

## Query recipes

### Stops by jurisdiction and mode

```sql
SELECT jurisdic, type, count(*) AS stops
FROM 'stops/stops.parquet'
GROUP BY ALL
HAVING count(*) > 20
ORDER BY stops DESC;
```

### Stops within 400 m of a transit center — note the reprojection

```sql
-- 400 m is 1312.34 international feet, the unit of EPSG:2913.
SELECT tc.name, count(*) AS stops_within_400m
FROM 'transit-centers/transit-centers.parquet' tc
JOIN 'stops/stops.parquet' s
  ON ST_DWithin(
       ST_Transform(tc.geometry, 'EPSG:4326', 'EPSG:2913', always_xy := true),
       ST_Transform(s.geometry,  'EPSG:4326', 'EPSG:2913', always_xy := true),
       1312.34)
GROUP BY tc.name
ORDER BY stops_within_400m DESC;
```

### How many routes serve each stop, by joining to route-stops

```sql
SELECT s.stop_id, s.stop_name, count(DISTINCT r.rte) AS routes
FROM 'stops/stops.parquet' s
JOIN 'route-stops/route-stops.parquet' r USING (stop_id)
GROUP BY 1, 2
ORDER BY routes DESC
LIMIT 10;
```

## Related collections

- [`route-stops`](https://data.source.coop/cholmes/trimet/route-stops/AGENTS.md) — the same stops exploded by route and direction; join on `stop_id`
- [`rail-stops`](https://data.source.coop/cholmes/trimet/rail-stops/AGENTS.md) — rail platforms with real station names, but a *different* id space
- [`transit-centers`](https://data.source.coop/cholmes/trimet/transit-centers/AGENTS.md) — the 15 major transfer hubs

## Provenance

TriMet publishes this as `tm_stops` at
[developer.trimet.org/gis](https://developer.trimet.org/gis/), last updated
July 30, 2026. Every column description in `collection.json`
comes from [TriMet's metadata page](https://developer.trimet.org/gis/meta_tm_stops.shtml) — that
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

