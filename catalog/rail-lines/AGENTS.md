# TriMet Rail Lines — agent guide

Public transit rail lines. Includes existing, under construction, and planned MAX, WES, and Portland Streetcar lines. The data have been generalized to improve cartographic display at smaller scales. 171 LineString features, WGS84, one
GeoParquet file of 89.6 KB in 1 row group(s).

## Access

```sql
INSTALL spatial; LOAD spatial;
INSTALL httpfs;  LOAD httpfs;
SELECT * FROM 'https://data.source.coop/cholmes/trimet/rail-lines/rail-lines.parquet' LIMIT 10;
```

Reads stream over HTTP range requests — query in place, do not download. The file
is Hilbert-ordered and carries a GeoParquet 1.1 `bbox` covering column, so a
spatial filter on `geometry_bbox` prunes row groups from metadata alone. Note
the column name: GDAL writes the covering as `<geometry column>_bbox`, so it is
`geometry_bbox` here, not `bbox`.

```sql
-- Coordinates are EPSG:2913 feet, not degrees. This collection spans
-- x 7,563,740–7,710,257, y 607,778–714,400.
SELECT * FROM 'https://data.source.coop/cholmes/trimet/rail-lines/rail-lines.parquet'
WHERE geometry_bbox.xmin > 7630000 AND geometry_bbox.xmax < 7650000
  AND geometry_bbox.ymin >  680000 AND geometry_bbox.ymax <  700000;
```

The recipes below use bare relative paths (`'rail-lines/rail-lines.parquet'`) for
readability. Prefix them with [`https://data.source.coop/cholmes/trimet/`](https://source.coop/cholmes/trimet/rail-lines/) to run remotely.

Other formats: `rail-lines.pmtiles` for map display (layer name `rail-lines`), and TriMet's
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

### The metadata documents `BL/NS`; the data contains `NS/BL`

TriMet's metadata page lists a code `BL/NS` ("Portland Streetcar B Loop and
North/South Line"). That string does not occur in the data. What the data
actually carries is **`NS/BL`**, on 2 segments here and 12 stops in `rail-stops`.
Filter on `NS/BL`. A query written from the published code list alone returns
nothing.

### `AUX` is in the data and in TriMet's code list, but has no style rule

7 segments are `AUX` — "Auxiliary track. No revenue service", i.e. yard leads and
connecting track. TriMet's own SLD has no rule for `AUX`, so on TriMet's maps
these segments are invisible. This catalog draws them in neutral gray rather than
dropping them, so be aware they will appear where TriMet's maps show nothing.
**Exclude `AUX` when counting revenue track.**

### Everything is `Existing` right now

`status` documents `Existing`, `Planned` and `UC` (under construction), but all
171 current segments are `Existing`. Code that branches on status is not wrong,
it is just untested against this snapshot — and the values will reappear as
TriMet adds projects.

### `line` is a set, encoded as a string

There is no join table. To ask "which segments does the Blue Line touch", you
must match any code containing `B` as a *component*, which is not a substring
test — `B` appears in `BL` (B Loop, a streetcar) and `BGR`. The reliable approach
is an explicit list of the codes that include the line you want; see the
recipes.

### Colors here differ slightly from the GTFS colors

TriMet's SLD uses `#084C8D` for the Blue Line; its GTFS `route_color` is
`#1359AE`. Both are authentic TriMet values from different systems. This
collection's `default.json` follows the SLD, because the SLD is the style written
for *this layer*; `by-type.json` follows GTFS.

## Query recipes

### Segments carrying the MAX Blue Line, handling shared track correctly

```sql
-- 'B' as a component, not as a substring: BL is the streetcar B Loop.
SELECT line, type, passage, count(*) AS segments
FROM 'rail-lines/rail-lines.parquet'
WHERE line IN ('B','BR','BG','BGR','BGRY','BRY')
GROUP BY ALL
ORDER BY segments DESC;
```

### How much track is shared, and by how many lines

```sql
SELECT line,
       CASE WHEN line IN ('AUX','WES') THEN 0
            ELSE length(replace(replace(line,'/',''),'AUX','')) END AS lines_sharing,
       count(*) AS segments
FROM 'rail-lines/rail-lines.parquet'
WHERE type <> 'CR' AND line <> 'AUX'
GROUP BY ALL
ORDER BY lines_sharing DESC, segments DESC;
```

### Grade separation by mode, excluding non-revenue track

```sql
SELECT type, passage, count(*) AS segments
FROM 'rail-lines/rail-lines.parquet'
WHERE line <> 'AUX'
GROUP BY ALL
ORDER BY type, segments DESC;
```

## Related collections

- [`rail-stops`](https://source.coop/cholmes/trimet/rail-stops/AGENTS.md) — the stations on these lines, sharing the same `line` codes and colors
- [`routes`](https://source.coop/cholmes/trimet/routes/AGENTS.md) — the operational, non-generalized alignment of the same rail service

## Provenance

TriMet publishes this as `tm_rail_lines` at
[developer.trimet.org/gis](https://developer.trimet.org/gis/), last updated
September 26, 2024. Every column description in `collection.json`
comes from [TriMet's metadata page](https://developer.trimet.org/gis/meta_tm_rail_lines.shtml) — that
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

