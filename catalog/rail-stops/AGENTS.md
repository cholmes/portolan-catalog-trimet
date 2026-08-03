# TriMet Rail Stops — agent guide

Public transit rail stops. Includes existing, under construction, and planned MAX, WES, and Portland Streetcar stops. The data have been generalized to improve cartographic display at smaller scales. 169 Point features, WGS84, one
GeoParquet file of 17.1 KB in 1 row group(s).

## Access

```sql
INSTALL spatial; LOAD spatial;
INSTALL httpfs;  LOAD httpfs;
SELECT * FROM 'https://data.source.coop/cholmes/trimet/rail-stops/rail-stops.parquet' LIMIT 10;
```

Reads stream over HTTP range requests — query in place, do not download. The file
is Hilbert-ordered and carries a GeoParquet 1.1 `bbox` covering column, so a
spatial filter on `geometry_bbox` prunes row groups from metadata alone. Note
the column name: GDAL writes the covering as `<geometry column>_bbox`, so it is
`geometry_bbox` here, not `bbox`.

```sql
-- Coordinates are EPSG:2913 feet, not degrees. This collection spans
-- x 7,563,749–7,710,257, y 607,778–714,400.
SELECT * FROM 'https://data.source.coop/cholmes/trimet/rail-stops/rail-stops.parquet'
WHERE geometry_bbox.xmin > 7630000 AND geometry_bbox.xmax < 7650000
  AND geometry_bbox.ymin >  680000 AND geometry_bbox.ymax <  700000;
```

The recipes below use bare relative paths (`'rail-stops/rail-stops.parquet'`) for
readability. Prefix them with [`https://data.source.coop/cholmes/trimet/`](https://source.coop/cholmes/trimet/rail-stops/) to run remotely.

Other formats: `rail-stops.pmtiles` for map display (layer name `rail-stops`), and TriMet's
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

### No id column — this layer does not join to the rest of the catalog

`rail-stops` carries `station`, `line`, `status`, `type` and nothing else. There
is no `stop_id`. To connect a station to real-time arrivals or to route service,
do a nearest-neighbour spatial join against `stops`, and check the result: the
generalized geometry means the nearest `stops` point is usually right but not
guaranteed.

### `NS/BL` again — the metadata says `BL/NS`

Exactly as in `rail-lines`: TriMet's code list documents `BL/NS`, the data
contains `NS/BL`, and here it is the code on 12 of the 169 stops. Filter on
`NS/BL`.

### Counts here do not match the rail rows in `stops`

169 stations here against 225 rail-typed rows in `stops`. Neither is wrong: this
layer collapses directional platforms into one station point, and `stops` keeps
them separate. Pick the one that matches your question and say which you used.

### `station` is not unique

Streetcar loops in particular repeat station names at nearby points. Do not use
`station` as a key.

### All `Existing`, as with the line layer

`Planned` and `UC` are documented but unused in this snapshot.

## Query recipes

### Interchange stations, ordered by how many services meet there

```sql
SELECT station, line, type,
       length(replace(line, '/', '')) AS approx_services
FROM 'rail-stops/rail-stops.parquet'
WHERE length(line) > 1
ORDER BY approx_services DESC, station;
```

### Stations per line code

```sql
SELECT line, type, count(*) AS stations
FROM 'rail-stops/rail-stops.parquet'
GROUP BY ALL
ORDER BY stations DESC;
```

### Match rail stations to their nearest public stop id

```sql
-- No shared key exists, so this is a nearest-neighbour join. Check the distance
-- column before trusting a match; the geometry here is generalized.
SELECT rs.station, s.stop_id, s.stop_name,
       round(ST_Distance(rs.geometry, s.geometry), 1) AS feet
FROM 'rail-stops/rail-stops.parquet' rs
JOIN 'stops/stops.parquet' s ON s.type IN ('MAX','CR','SC','BSC')
QUALIFY row_number() OVER (PARTITION BY rs.station, rs.geometry ORDER BY feet) = 1
ORDER BY feet DESC
LIMIT 10;
```

## Related collections

- [`rail-lines`](https://source.coop/cholmes/trimet/rail-lines/AGENTS.md) — the track these stations sit on, sharing the `line` code space and palette
- [`stops`](https://source.coop/cholmes/trimet/stops/AGENTS.md) — the full stop list, with public `stop_id` values but no station names

## Provenance

TriMet publishes this as `tm_rail_stops` at
[developer.trimet.org/gis](https://developer.trimet.org/gis/), last updated
December 04, 2024. Every column description in `collection.json`
comes from [TriMet's metadata page](https://developer.trimet.org/gis/meta_tm_rail_stops.shtml) — that
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

