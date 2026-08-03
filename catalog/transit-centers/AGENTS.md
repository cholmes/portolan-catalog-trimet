# TriMet Transit Centers — agent guide

Transit Centers. 15 Point features, WGS84, one
GeoParquet file of 11.7 KB in 1 row group(s).

## Access

```sql
INSTALL spatial; LOAD spatial;
INSTALL httpfs;  LOAD httpfs;
SELECT * FROM 'https://data.source.coop/cholmes/trimet/transit-centers/transit-centers.parquet' LIMIT 10;
```

Reads stream over HTTP range requests — query in place, do not download. The file
is Hilbert-ordered and carries a GeoParquet 1.1 `bbox` covering column, so a
spatial filter on `geometry_bbox` prunes row groups from metadata alone. Note
the column name: GDAL writes the covering as `<geometry column>_bbox`, so it is
`geometry_bbox` here, not `bbox`.

```sql
-- Coordinates are EPSG:2913 feet, not degrees. This collection spans
-- x 7,565,216–7,708,126, y 624,437–704,049.
SELECT * FROM 'https://data.source.coop/cholmes/trimet/transit-centers/transit-centers.parquet'
WHERE geometry_bbox.xmin > 7630000 AND geometry_bbox.xmax < 7650000
  AND geometry_bbox.ymin >  680000 AND geometry_bbox.ymax <  700000;
```

The recipes below use bare relative paths (`'transit-centers/transit-centers.parquet'`) for
readability. Prefix them with [`https://data.source.coop/cholmes/trimet/`](https://source.coop/cholmes/trimet/transit-centers/) to run remotely.

Other formats: `transit-centers.pmtiles` for map display (layer name `transit-centers`), and TriMet's
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
  ON ST_DWithin(tc.geometry, rs.geometry, 1312.34)
GROUP BY tc.name
ORDER BY routes DESC;
```

### Which hubs have rail

```sql
SELECT tc.name, string_agg(DISTINCT rst.type, ', ') AS rail_modes
FROM 'transit-centers/transit-centers.parquet' tc
LEFT JOIN 'rail-stops/rail-stops.parquet' rst
  ON ST_DWithin(tc.geometry, rst.geometry, 1312.34)
GROUP BY tc.name
ORDER BY rail_modes NULLS LAST;
```

## Related collections

- [`park-and-rides`](https://source.coop/cholmes/trimet/park-and-rides/AGENTS.md) — parking at many of the same facilities
- [`route-stops`](https://source.coop/cholmes/trimet/route-stops/AGENTS.md) — the routes that actually call at each hub

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

Practically: use the data, and contact **[gis@trimet.org](mailto:gis@trimet.org)** before redistributing
it or building a product on it. If you need transit data under clear open terms,
TriMet's [GTFS feed](https://developer.trimet.org/GTFS.shtml) is the better
starting point.

