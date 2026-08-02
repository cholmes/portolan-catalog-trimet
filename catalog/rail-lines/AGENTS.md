# TriMet Rail Lines — agent guide

Public transit rail lines. Includes existing, under construction, and planned MAX, WES, and Portland Streetcar lines. The data have been generalized to improve cartographic display at smaller scales. 171 LineString features, WGS84, one
GeoParquet file of 87.1 KB in 1 row group(s).

## Access

```sql
INSTALL spatial; LOAD spatial;
INSTALL httpfs;  LOAD httpfs;
SELECT * FROM 'https://data.source.coop/cholmes/trimet/rail-lines/rail-lines.parquet' LIMIT 10;
```

Reads stream over HTTP range requests — query in place, do not download. The file
is Hilbert-ordered and carries a GeoParquet 1.1 `bbox` covering column, so a
spatial filter on `bbox.xmin` / `bbox.ymin` / `bbox.xmax` / `bbox.ymax` prunes
row groups from metadata alone:

```sql
SELECT * FROM 'https://data.source.coop/cholmes/trimet/rail-lines/rail-lines.parquet'
WHERE bbox.xmin > -122.70 AND bbox.xmax < -122.60
  AND bbox.ymin >   45.50 AND bbox.ymax <   45.55;
```

The recipes below use bare relative paths (`'rail-lines/rail-lines.parquet'`) for
readability. Prefix them with `https://data.source.coop/cholmes/trimet/` to run remotely.

Other formats: `rail-lines.pmtiles` for map display (layer name `rail-lines`), and TriMet's
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

- [`rail-stops`](../rail-stops/AGENTS.md) — the stations on these lines, sharing the same `line` codes and colors
- [`routes`](../routes/AGENTS.md) — the operational, non-generalized alignment of the same rail service

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

Practically: use the data, and contact **gis@trimet.org** before redistributing
it or building a product on it. If you need transit data under clear open terms,
TriMet's [GTFS feed](https://developer.trimet.org/GTFS.shtml) is the better
starting point.

