# TriMet Park and Rides — agent guide

TriMet park and ride locations. 46 Point features, WGS84, one
GeoParquet file of 9.3 KB in 1 row group(s).

## Access

```sql
INSTALL spatial; LOAD spatial;
INSTALL httpfs;  LOAD httpfs;
SELECT * FROM 'https://data.source.coop/cholmes/trimet/park-and-rides/park-and-rides.parquet' LIMIT 10;
```

Reads stream over HTTP range requests — query in place, do not download. The file
is Hilbert-ordered and carries a GeoParquet 1.1 `bbox` covering column, so a
spatial filter on `bbox.xmin` / `bbox.ymin` / `bbox.xmax` / `bbox.ymax` prunes
row groups from metadata alone:

```sql
SELECT * FROM 'https://data.source.coop/cholmes/trimet/park-and-rides/park-and-rides.parquet'
WHERE bbox.xmin > -122.70 AND bbox.xmax < -122.60
  AND bbox.ymin >   45.50 AND bbox.ymax <   45.55;
```

The recipes below use bare relative paths (`'park-and-rides/park-and-rides.parquet'`) for
readability. Prefix them with `https://data.source.coop/cholmes/trimet/` to run remotely.

Other formats: `park-and-rides.pmtiles` for map display (layer name `park-and-rides`), and TriMet's
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
  ON ST_DWithin(
       ST_Transform(p.geometry, 'EPSG:4326', 'EPSG:2913', always_xy := true),
       ST_Transform(r.geometry, 'EPSG:4326', 'EPSG:2913', always_xy := true),
       1312.34)
GROUP BY 1;
```

## Related collections

- [`transit-centers`](https://data.source.coop/cholmes/trimet/transit-centers/AGENTS.md) — many park and rides sit at a transit center
- [`rail-stops`](https://data.source.coop/cholmes/trimet/rail-stops/AGENTS.md) — the large lots are mostly on MAX

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

Practically: use the data, and contact **gis@trimet.org** before redistributing
it or building a product on it. If you need transit data under clear open terms,
TriMet's [GTFS feed](https://developer.trimet.org/GTFS.shtml) is the better
starting point.

