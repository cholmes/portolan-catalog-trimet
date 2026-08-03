# TriMet Rail Lines

Public transit rail lines. Includes existing, under construction, and planned MAX, WES, and Portland Streetcar lines. The data have been generalized to improve cartographic display at smaller scales. **171 LineString features** covering the TriMet
service district in the Portland, Oregon metropolitan area, published by TriMet
as `tm_rail_lines` and last updated at the source on
**September 26, 2024**.

TriMet's rail network — MAX light rail, WES commuter rail and Portland Streetcar
— as 171 segments generalized for cartographic display. Each segment records
which line or lines run over it (`line`), whether it is at surface level, on a
bridge or in a tunnel (`passage`), its operational status, and its service type.

The `line` codes are what make this layer unusual: a value like `BGR` means the
Blue, Green and Red lines all share that track. That is why TriMet draws it with
a solid base stroke plus one dashed overlay per additional line, and why
`styles/default.json` here does the same.

> **Agents:** see [AGENTS.md](https://source.coop/cholmes/trimet/rail-lines/AGENTS.md) for join keys, verified query recipes
> and the caveats that will otherwise cost you a wrong answer.

[![TriMet Rail Lines](https://data.source.coop/cholmes/trimet/rail-lines/thumbnail.webp)](https://cholmes.github.io/trimet-data-browser)

### 🗺️ [Explore this collection on an interactive map →](https://cholmes.github.io/trimet-data-browser)

## Quick start

Read it straight from object storage — DuckDB fetches only the byte ranges it
needs, so there is nothing to download first:

```sql
INSTALL spatial; LOAD spatial;
INSTALL httpfs;  LOAD httpfs;

SELECT * FROM 'https://data.source.coop/cholmes/trimet/rail-lines/rail-lines.parquet' LIMIT 10;
```

Or with GeoPandas:

```python
import geopandas as gpd
gdf = gpd.read_parquet("https://data.source.coop/cholmes/trimet/rail-lines/rail-lines.parquet")
```

## Suggested uses

- Drawing the rail network at metro scale. This is what the layer is *for* —
  TriMet says so — and this collection ships a direct reproduction of TriMet's
  own GeoServer style for it.
- Showing which services share trackage, which the `line` codes encode directly
  and no other layer in this catalog does.
- Distinguishing at-grade from grade-separated running via `passage`.

## Limitations and inappropriate uses

- **Generalized geometry. Do not measure it.** TriMet states the data "have been
  generalized to improve cartographic display at smaller scales". Track lengths
  computed here will be short, and the alignment will not sit on the real
  right-of-way at large scale. Use `routes` for the operational alignment.
- **`passage` is a drawing hint, not an inventory.** TriMet's own note: this
  attribute "is intended for use in cartographic display rather than analysis".
  It does not identify specific bridges or tunnels.
- **Not a track or signalling model.** Segments are cartographic units. There is
  no notion of track count, direction of running, junctions or switches.

## Schema

| Column | Type | Description |
|---|---|---|
| `line` | string | Line(s) serving a particular segment.<br>Values: `AL` Portland Streetcar A Loop; `AL/BL` Portland Streetcar A & B Loops; `AUX` Auxiliary track. No revenue service; `B` MAX Blue Line; `BG` MAX Blue, and Green Lines; `BGR` MAX Blue, Green, and Red Lines; `BGRY` MAX Blue, Green, Red, and Yellow Lines; `BL` Portland Streetcar B Loop; `BL/NS` Portland Streetcar B Loop and North/South Line; `BR` MAX Blue and Red Lines; `G` MAX Green Line; `GO` MAX Green and Orange Lines; `GY` MAX Green and Yellow Lines; `NS` Portland Streetcar North/South Line; `NS/AL` Portland Streetcar A Loop and North/South Line; `NS/AL/BL` Portland Streetcar A & B Loops and North/South Line; `O` MAX Orange Line; `O/AL/BL` MAX Orange Line and Portland Streetcar A & B Loops; `R` MAX Red Line; `WES` WES (Westside Express Service); `Y` MAX Yellow Line. |
| `passage` | string | Indicates the infrastructure (if any) over/through which a rail segment travels.  This data is intended for use in cartographic display rather than analysis<br>Values: `bridge` Rail segment travels over bridge; `surface` Rail segment travels over ground/surface level; `tunnel` Rail segment passes through tunnel. |
| `status` | string | Operational status of the segment.<br>Values: `Existing` Service currently provided on rail segment; `Planned` Rail segment in advanced planning stages; `UC` Rail segment is under construction. |
| `type` | string | Type of service.<br>Values: `CR` Commuter rail; `MAX` Light rail; `MAX/SC` Shared light rail and streetcar; `SC` Streetcar. |
| `geometry` | binary | Feature geometry, WGS84 lon/lat. |
| `geometry_bbox` | struct<xmin: float not null, ymin: float not null, xmax: float not null, ymax: float not null> | GeoParquet 1.1 covering column, for row-group pruning. Same projected feet as the geometry. |

Column descriptions are TriMet's own, taken verbatim from
[meta_tm_rail_lines.shtml](https://developer.trimet.org/gis/meta_tm_rail_lines.shtml). The same text is carried in
`table:columns` in [collection.json](https://source.coop/cholmes/trimet/rail-lines/collection.json).

## Visualization

| Style | What it shows |
|---|---|
| [`default.json`](https://source.coop/cholmes/trimet/rail-lines/styles/default.json) | A direct reproduction of TriMet's published GeoServer style `ott:rail`, whose rules key on exactly the LINE values this layer carries. Each segment gets a solid base stroke in its trunk line's color, then one dashed overlay per additional line sharing the track — so the four-line trunk through downtown Portland reads as blue under red, green and yellow dashes, the way it does on TriMet's own maps. Widths step at zoom 12, standing in for the SLD's scale break at denominator 151181. Dash lengths are converted from SLD pixels into MapLibre line-widths using the low-zoom width, so they match exactly below zoom 12 and run proportionally shorter above it. AUX segments carry no SLD rule and are drawn neutral gray rather than dropped. |
| [`by-passage.json`](https://source.coop/cholmes/trimet/rail-lines/styles/by-passage.json) | Encodes the PASSAGE attribute — whether a segment runs at surface level, over a bridge, or through a tunnel. Bridges are drawn heavy and dark, tunnels dashed, surface track light. TriMet notes that PASSAGE is intended for cartographic display rather than analysis, so read this as a drawing hint and not an infrastructure inventory. |
| [`by-type.json`](https://source.coop/cholmes/trimet/rail-lines/styles/by-type.json) | Collapses the twenty LINE values into the four TYPE values: light rail, streetcar, commuter rail, and the shared MAX/streetcar segment. Colors come from TriMet's GTFS route_color. Simpler than the default style and easier to read at metro-wide zooms. |
| [`labeled.json`](https://source.coop/cholmes/trimet/rail-lines/styles/labeled.json) | TriMet's rail cartography with the LINE code drawn along each segment. Because a code such as BGR means three lines share that track, the labels are the fastest way to read which services run where. |

The PMTiles layer is named `rail-lines`. Styles reference it as `../rail-lines.pmtiles`,
so they load unmodified against this directory.

## Files

| File | Size | What it is |
|---|---|---|
| [`rail-lines.parquet`](https://data.source.coop/cholmes/trimet/rail-lines/rail-lines.parquet) | 89.6 KB | GeoParquet 1.1, 171 rows in 1 row group(s), zstd, Hilbert-ordered, bbox covering column |
| [`rail-lines.pmtiles`](https://data.source.coop/cholmes/trimet/rail-lines/rail-lines.pmtiles) | 60.8 KB | Vector tiles for display, every feature kept at every zoom |
| [`thumbnail.webp`](https://data.source.coop/cholmes/trimet/rail-lines/thumbnail.webp) | 47.7 KB | Rendered from `styles/default.json` over a light basemap |
| [`collection.json`](https://source.coop/cholmes/trimet/rail-lines/collection.json) | — | STAC Collection metadata |

## Provenance

[![TriMet](https://data.source.coop/cholmes/trimet/_assets/trimet-logo.png)](https://developer.trimet.org/gis/)

Produced by **TriMet GIS** (4012 SE 17th Ave, GIS3,
Portland, OR 97202,
[gis@trimet.org](mailto:gis@trimet.org)) and distributed at
[developer.trimet.org/gis](https://developer.trimet.org/gis/) as `tm_rail_lines`.

The originals are linked as assets and are the authoritative copy:
[Shapefile](https://developer.trimet.org/gis/data/tm_rail_lines.zip) · [KML](https://developer.trimet.org/gis/data/tm_rail_lines.kml) · [Metadata](https://developer.trimet.org/gis/meta_tm_rail_lines.shtml)

This collection was produced by reprojecting TriMet's Shapefile from
EPSG:2913 (NAD83(HARN) / Oregon North (ft)) to EPSG:4326 and writing GeoParquet and
PMTiles. No features were added, removed or edited. The exact commands are in
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

