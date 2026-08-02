# TriMet Rail Stops — agent guide

Public transit rail stops. Includes existing, under construction, and planned MAX, WES, and Portland Streetcar stops. The data have been generalized to improve cartographic display at smaller scales. 169 Point features, WGS84, one
GeoParquet file of 11.3 KB in 1 row group(s).

## Access

```sql
INSTALL spatial; LOAD spatial;
INSTALL httpfs;  LOAD httpfs;
SELECT * FROM 'https://data.source.coop/cholmes/trimet/rail-stops/rail-stops.parquet' LIMIT 10;
```

Reads stream over HTTP range requests — query in place, do not download. The file
is Hilbert-ordered and carries a GeoParquet 1.1 `bbox` covering column, so a
spatial filter on `bbox.xmin` / `bbox.ymin` / `bbox.xmax` / `bbox.ymax` prunes
row groups from metadata alone:

```sql
SELECT * FROM 'https://data.source.coop/cholmes/trimet/rail-stops/rail-stops.parquet'
WHERE bbox.xmin > -122.70 AND bbox.xmax < -122.60
  AND bbox.ymin >   45.50 AND bbox.ymax <   45.55;
```

The recipes below use bare relative paths (`'rail-stops/rail-stops.parquet'`) for
readability. Prefix them with `https://data.source.coop/cholmes/trimet/` to run remotely.

Other formats: `rail-stops.pmtiles` for map display (layer name `rail-stops`), and TriMet's
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
       round(ST_Distance(
         ST_Transform(rs.geometry, 'EPSG:4326', 'EPSG:2913', always_xy := true),
         ST_Transform(s.geometry,  'EPSG:4326', 'EPSG:2913', always_xy := true)) * 0.3048, 1) AS metres
FROM 'rail-stops/rail-stops.parquet' rs
JOIN 'stops/stops.parquet' s ON s.type IN ('MAX','CR','SC','BSC')
QUALIFY row_number() OVER (PARTITION BY rs.station, rs.geometry ORDER BY metres) = 1
ORDER BY metres DESC
LIMIT 10;
```

## Related collections

- [`rail-lines`](../rail-lines/AGENTS.md) — the track these stations sit on, sharing the `line` code space and palette
- [`stops`](../stops/AGENTS.md) — the full stop list, with public `stop_id` values but no station names

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

Practically: use the data, and contact **gis@trimet.org** before redistributing
it or building a product on it. If you need transit data under clear open terms,
TriMet's [GTFS feed](https://developer.trimet.org/GTFS.shtml) is the better
starting point.

