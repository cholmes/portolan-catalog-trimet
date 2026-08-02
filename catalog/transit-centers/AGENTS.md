# TriMet Transit Centers — agent guide

Transit Centers. 15 Point features, WGS84, one
GeoParquet file of 6.4 KB in 1 row group(s).

## Access

```sql
INSTALL spatial; LOAD spatial;
INSTALL httpfs;  LOAD httpfs;
SELECT * FROM 'https://data.source.coop/cholmes/trimet/transit-centers/transit-centers.parquet' LIMIT 10;
```

Reads stream over HTTP range requests — query in place, do not download. The file
is Hilbert-ordered and carries a GeoParquet 1.1 `bbox` covering column, so a
spatial filter on `bbox.xmin` / `bbox.ymin` / `bbox.xmax` / `bbox.ymax` prunes
row groups from metadata alone:

```sql
SELECT * FROM 'https://data.source.coop/cholmes/trimet/transit-centers/transit-centers.parquet'
WHERE bbox.xmin > -122.70 AND bbox.xmax < -122.60
  AND bbox.ymin >   45.50 AND bbox.ymax <   45.55;
```

The recipes below use bare relative paths (`'transit-centers/transit-centers.parquet'`) for
readability. Prefix them with `https://data.source.coop/cholmes/trimet/` to run remotely.

Other formats: `transit-centers.pmtiles` for map display (layer name `transit-centers`), and TriMet's
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

### Fifteen rows, and no key beyond `name`

There is no id column. `name` is unique across the 15 rows here, but it is a
display string and TriMet may reword it; do not persist it as a foreign key.

### `city` is the municipality, `jurisdic` in other layers may disagree

`transit-centers` carries `city` and `county`; `stops` carries a single
`jurisdic` field that may hold either a city or a county. They are not the same
vocabulary — do not join on them.

### Several share a name with a park and ride

"Gateway/NE 99th Ave", "Sunset", "Willow Creek/SW 185th Ave" and "Clackamas
Town Center" appear in both this layer and `park-and-rides`, with the suffix
differing ("Transit Center" versus "Park & Ride"). Matching on name needs
normalisation; matching spatially is more reliable.

## Query recipes

### Transit centers by county

```sql
SELECT county, count(*) AS centers, string_agg(name, '; ' ORDER BY name) AS names
FROM 'transit-centers/transit-centers.parquet'
GROUP BY county
ORDER BY centers DESC;
```

### How much service each hub concentrates

```sql
SELECT tc.name,
       count(DISTINCT rs.rte) AS routes,
       count(DISTINCT rs.stop_id) AS stops
FROM 'transit-centers/transit-centers.parquet' tc
JOIN 'route-stops/route-stops.parquet' rs
  ON ST_DWithin(
       ST_Transform(tc.geometry, 'EPSG:4326', 'EPSG:2913', always_xy := true),
       ST_Transform(rs.geometry, 'EPSG:4326', 'EPSG:2913', always_xy := true),
       1312.34)
GROUP BY tc.name
ORDER BY routes DESC;
```

### Which hubs have rail

```sql
SELECT tc.name, string_agg(DISTINCT rst.type, ', ') AS rail_modes
FROM 'transit-centers/transit-centers.parquet' tc
LEFT JOIN 'rail-stops/rail-stops.parquet' rst
  ON ST_DWithin(
       ST_Transform(tc.geometry,  'EPSG:4326', 'EPSG:2913', always_xy := true),
       ST_Transform(rst.geometry, 'EPSG:4326', 'EPSG:2913', always_xy := true),
       1312.34)
GROUP BY tc.name
ORDER BY rail_modes NULLS LAST;
```

## Related collections

- [`park-and-rides`](../park-and-rides/AGENTS.md) — parking at many of the same facilities
- [`route-stops`](../route-stops/AGENTS.md) — the routes that actually call at each hub

## Provenance

TriMet publishes this as `tm_tran_cen` at
[developer.trimet.org/gis](https://developer.trimet.org/gis/), last updated
July 31, 2024. Every column description in `collection.json`
comes from [TriMet's metadata page](https://developer.trimet.org/gis/meta_tm_tran_cen.shtml) — that
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

