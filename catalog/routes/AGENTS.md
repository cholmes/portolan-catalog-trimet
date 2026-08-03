# TriMet Routes — agent guide

All existing bus and rail lines. 200 LineString features, WGS84, one
GeoParquet file of 794.0 KB in 1 row group(s).

## Access

```sql
INSTALL spatial; LOAD spatial;
INSTALL httpfs;  LOAD httpfs;
SELECT * FROM 'https://data.source.coop/cholmes/trimet/routes/routes.parquet' LIMIT 10;
```

Reads stream over HTTP range requests — query in place, do not download. The file
is Hilbert-ordered and carries a GeoParquet 1.1 `bbox` covering column, so a
spatial filter on `geometry_bbox` prunes row groups from metadata alone. Note
the column name: GDAL writes the covering as `<geometry column>_bbox`, so it is
`geometry_bbox` here, not `bbox`.

```sql
-- Coordinates are EPSG:2913 feet, not degrees. This collection spans
-- x 7,531,765–7,730,400, y 595,331–727,211.
SELECT * FROM 'https://data.source.coop/cholmes/trimet/routes/routes.parquet'
WHERE geometry_bbox.xmin > 7630000 AND geometry_bbox.xmax < 7650000
  AND geometry_bbox.ymin >  680000 AND geometry_bbox.ymax <  700000;
```

The recipes below use bare relative paths (`'routes/routes.parquet'`) for
readability. Prefix them with [`https://data.source.coop/cholmes/trimet/`](https://source.coop/cholmes/trimet/routes/) to run remotely.

Other formats: `routes.pmtiles` for map display (layer name `routes`), and TriMet's
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

### `(rte, dir)` is the key, not `rte`

200 rows, 113 distinct `rte` values, 87 of which appear twice. `dir` is 0 or 1
and TriMet documents it only as "Direction 0" and "Direction 1" — the human
meaning lives in `dir_desc` (e.g. "To Portland"). Always group or join on the
pair.

### Use `public_rte` for display, `rte` for joining

`rte` is an integer and `public_rte` is a string. They differ where a service has
a lettered public name: route 2 is displayed as **FX2**. Show `public_rte` to
humans; join on `rte`, which is what `route-stops` carries.

### Mixed LINESTRING / MULTILINESTRING breaks naive length code

`ST_Length_Spheroid` returns `nan` on this layer for both geometry types, so do
not reach for it. Project and use `ST_Length` instead (see the recipes). If you
need per-segment work, `ST_Dump` the multilinestrings first.

### `frequent` is a string, not a boolean

Values are the literal strings `'True'` and `'False'`, not SQL booleans. Compare
with `frequent = 'True'`; a bare `WHERE frequent` will not parse.

### Some alignments leave the district

A handful of routes run past the district boundary — service to Estacada and
Sherwood, for example. Do not assume `routes` is contained by
`district-boundary`.

## Query recipes

### Longest routes in kilometres, one direction only

```sql
-- ST_Length returns feet directly; 5280 ft to the mile.
SELECT rte, any_value(rte_desc) AS name,
       round(sum(ST_Length(geometry)) / 5280.0, 1) AS miles
FROM 'routes/routes.parquet'
WHERE dir = 0
GROUP BY rte
ORDER BY miles DESC
LIMIT 10;
```

### Route-kilometres by mode

```sql
SELECT type,
       round(sum(ST_Length(geometry)) / 5280.0, 1) AS miles,
       count(*) AS segments
FROM 'routes/routes.parquet'
GROUP BY type
ORDER BY miles DESC;
```

### The Frequent Service network, as displayed to riders

```sql
SELECT DISTINCT public_rte, rte_desc, type
FROM 'routes/routes.parquet'
WHERE frequent = 'True'
ORDER BY rte;
```

## Related collections

- [`route-stops`](https://source.coop/cholmes/trimet/route-stops/AGENTS.md) — the stops along each of these route-directions, joined on `(rte, dir)`
- [`rail-lines`](https://source.coop/cholmes/trimet/rail-lines/AGENTS.md) — rail drawn for cartography, with per-line colors
- [`stops`](https://source.coop/cholmes/trimet/stops/AGENTS.md) — the deduplicated stop list

## Provenance

TriMet publishes this as `tm_routes` at
[developer.trimet.org/gis](https://developer.trimet.org/gis/), last updated
July 13, 2026. Every column description in `collection.json`
comes from [TriMet's metadata page](https://developer.trimet.org/gis/meta_tm_routes.shtml) — that
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

