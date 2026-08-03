# TriMet District Boundary — agent guide

TriMet district boundary. 1 Polygon features, WGS84, one
GeoParquet file of 88.5 KB in 1 row group(s).

## Access

```sql
INSTALL spatial; LOAD spatial;
INSTALL httpfs;  LOAD httpfs;
SELECT * FROM 'https://data.source.coop/cholmes/trimet/district-boundary/district-boundary.parquet' LIMIT 10;
```

Reads stream over HTTP range requests — query in place, do not download. The file
is Hilbert-ordered and carries a GeoParquet 1.1 `bbox` covering column, so a
spatial filter on `geometry_bbox` prunes row groups from metadata alone. Note
the column name: GDAL writes the covering as `<geometry column>_bbox`, so it is
`geometry_bbox` here, not `bbox`.

```sql
-- Coordinates are EPSG:2913 feet, not degrees. This collection spans
-- x 7,522,269–7,744,957, y 584,745–733,815.
SELECT * FROM 'https://data.source.coop/cholmes/trimet/district-boundary/district-boundary.parquet'
WHERE geometry_bbox.xmin > 7630000 AND geometry_bbox.xmax < 7650000
  AND geometry_bbox.ymin >  680000 AND geometry_bbox.ymax <  700000;
```

The recipes below use bare relative paths (`'district-boundary/district-boundary.parquet'`) for
readability. Prefix them with [`https://data.source.coop/cholmes/trimet/`](https://source.coop/cholmes/trimet/district-boundary/) to run remotely.

Other formats: `district-boundary.pmtiles` for map display (layer name `district-boundary`), and TriMet's
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

### The area columns are integers, not floats

TriMet's metadata page documents `AREA_SQ_MI` and `ACRES` as *Float*, length 13.
In the actual DBF they are integers, and this catalog carries them through as
`int64`: 533 and 341554 exactly. If you need sub-square-mile precision, compute
it from the geometry — see the CRS section — rather than trusting these to be
rounded floats.

### One feature, so no spatial index will help you

The file holds a single polygon with a few thousand vertices. Row-group pruning
does nothing here. For repeated point-in-polygon tests, read the geometry once
into a variable rather than re-scanning the file per query.

### It is a plain polygon, not a multipolygon

`ST_GeometryType` returns `POLYGON`. There are no islands or detached parts, so
you can use it directly in `ST_Contains` / `ST_Within` without dumping parts.

## Query recipes

### Which stops fall inside the district — and how many do not

```sql
SELECT ST_Within(s.geometry, b.geometry) AS inside, count(*)
FROM 'stops/stops.parquet' s
CROSS JOIN 'district-boundary/district-boundary.parquet' b
GROUP BY 1;
```

### Confirm TriMet's stated area against the geometry

```sql
-- The geometry is already in feet, so no transform is needed.
SELECT area_sq_mi AS trimet_says,
       round(ST_Area(geometry) / 27878400.0, 1) AS computed_sq_mi,
       round(ST_Area(geometry) / 43560.0)       AS computed_acres,
       acres AS trimet_acres
FROM 'district-boundary/district-boundary.parquet';
```

## Related collections

- [`stops`](https://source.coop/cholmes/trimet/stops/AGENTS.md) — the service the district exists to deliver
- [`routes`](https://source.coop/cholmes/trimet/routes/AGENTS.md) — alignments, a few of which run beyond the district edge

## Provenance

TriMet publishes this as `tm_boundary` at
[developer.trimet.org/gis](https://developer.trimet.org/gis/), last updated
January 09, 2013. Every column description in `collection.json`
comes from [TriMet's metadata page](https://developer.trimet.org/gis/meta_tm_boundary.shtml) — that
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

