# TriMet Geospatial Data

[![TriMet](https://data.source.coop/cholmes/trimet/_assets/trimet-logo.png)](https://developer.trimet.org/gis/)

TriMet — the Tri-County Metropolitan Transportation District of Oregon — runs
bus, light rail (MAX), commuter rail (WES) and streetcar service across the
Portland metropolitan area. It publishes eight geospatial layers at
[developer.trimet.org/gis](https://developer.trimet.org/gis/) as Shapefile and
KML, each with a metadata page carrying full attribute definitions and code
lists.

This catalog is a cloud-native mirror of all eight: the same features as
GeoParquet and PMTiles, with TriMet's original Shapefile, KML and metadata page
linked from every collection. Nothing has been added to the data and no features
were dropped.

The GeoParquet keeps TriMet's native **EPSG:2913** (NAD83(HARN) / Oregon North,
international feet), so lengths and areas come out in feet without a projection
step. The PMTiles are WGS84, because vector tiles are.


### 🗺️ [Explore the catalog on an interactive map →](https://cholmes.github.io/trimet-data-browser)

All eight collections, drawn with TriMet's own cartography, with no setup.

> **Agents:** start at [AGENTS.md](https://source.coop/cholmes/trimet/AGENTS.md) for join keys, the
> quirks that produce silently wrong answers, and verified query recipes.

## Collections

| Collection | Features | Geometry | Description |
|---|---|---|---|
| [TriMet District Boundary](https://source.coop/cholmes/trimet/district-boundary/) | 1 | Polygon | TriMet service district boundary. |
| [TriMet Routes](https://source.coop/cholmes/trimet/routes/) | 200 | LineString | TriMet fixed route alignments (includes bus and rail.) |
| [TriMet Rail Lines](https://source.coop/cholmes/trimet/rail-lines/) | 171 | LineString | TriMet rail service optimized for cartographic display. |
| [TriMet Stops](https://source.coop/cholmes/trimet/stops/) | 6,316 | Point | Active TriMet stops (includes bus and rail.) |
| [TriMet Route Stops](https://source.coop/cholmes/trimet/route-stops/) | 8,314 | Point | Active TriMet stops (includes bus and rail) by route and direction. |
| [TriMet Rail Stops](https://source.coop/cholmes/trimet/rail-stops/) | 169 | Point | TriMet rail stops optimized for cartographic display. |
| [TriMet Transit Centers](https://source.coop/cholmes/trimet/transit-centers/) | 15 | Point | TriMet transit center locations. |
| [TriMet Park and Rides](https://source.coop/cholmes/trimet/park-and-rides/) | 46 | Point | TriMet park and ride locations. |

## Quick start

```sql
INSTALL spatial; LOAD spatial;
INSTALL httpfs;  LOAD httpfs;

-- The 15 transit centers, by county
SELECT county, count(*) FROM 'https://data.source.coop/cholmes/trimet/transit-centers/transit-centers.parquet'
GROUP BY county;
```

Past the first query, the interesting pattern is joining across collections.
`stops` and `route-stops` share `stop_id` exactly — all 6,316 of them — which
turns a stop location into the set of routes that serve it:

```sql
SELECT s.stop_name, count(DISTINCT r.rte) AS routes
FROM 'https://data.source.coop/cholmes/trimet/stops/stops.parquet' s
JOIN 'https://data.source.coop/cholmes/trimet/route-stops/route-stops.parquet' r USING (stop_id)
GROUP BY 1 ORDER BY routes DESC LIMIT 10;
```

## Cartography

Where TriMet publishes a style for a layer, this catalog reproduces it rather
than inventing one. Two TriMet sources are used, and both are mirrored into the
collections they style so the reproduction can be checked against its origin:

- **`ott:rail`**, the GeoServer SLD behind TriMet's rail maps, fetched from
  [`ws.trimet.org`](https://ws.trimet.org/geoserver/ows?service=WMS&version=1.1.1&request=GetStyles&layers=ott:current_rail)
  via WMS `GetStyles`. Its rules key on exactly the `line` values
  the rail layers carry, so `rail-lines/styles/default.json` reproduces it
  segment for segment — including the layered dashed overlays that show which
  services share a track.
- **[`trimet-routes`](https://tiles.trimet.org/styles/trimet-routes/style.json)**,
  TriMet's MapLibre style at [tiles.trimet.org](https://tiles.trimet.org/styles.json), which gives
  the line weights and the flat bus color `#136390`. Where it resolves
  `route_color` from GTFS, the equivalent colors are taken from TriMet's GTFS
  `routes.txt`.

Every collection ships three to five styles; see each collection's README.

## Where the data comes from

| Collection | TriMet source | Last updated at source |
|---|---|---|
| TriMet District Boundary | `tm_boundary` — [Shapefile](https://developer.trimet.org/gis/data/tm_boundary.zip) · [KML](https://developer.trimet.org/gis/data/tm_boundary.kml) · [Metadata](https://developer.trimet.org/gis/meta_tm_boundary.shtml) | January 09, 2013 |
| TriMet Routes | `tm_routes` — [Shapefile](https://developer.trimet.org/gis/data/tm_routes.zip) · [KML](https://developer.trimet.org/gis/data/tm_routes.kml) · [Metadata](https://developer.trimet.org/gis/meta_tm_routes.shtml) | July 13, 2026 |
| TriMet Rail Lines | `tm_rail_lines` — [Shapefile](https://developer.trimet.org/gis/data/tm_rail_lines.zip) · [KML](https://developer.trimet.org/gis/data/tm_rail_lines.kml) · [Metadata](https://developer.trimet.org/gis/meta_tm_rail_lines.shtml) | September 26, 2024 |
| TriMet Stops | `tm_stops` — [Shapefile](https://developer.trimet.org/gis/data/tm_stops.zip) · [KML](https://developer.trimet.org/gis/data/tm_stops.kml) · [Metadata](https://developer.trimet.org/gis/meta_tm_stops.shtml) | July 30, 2026 |
| TriMet Route Stops | `tm_route_stops` — [Shapefile](https://developer.trimet.org/gis/data/tm_route_stops.zip) · [KML](https://developer.trimet.org/gis/data/tm_route_stops.kml) · [Metadata](https://developer.trimet.org/gis/meta_tm_route_stops.shtml) | July 30, 2026 |
| TriMet Rail Stops | `tm_rail_stops` — [Shapefile](https://developer.trimet.org/gis/data/tm_rail_stops.zip) · [KML](https://developer.trimet.org/gis/data/tm_rail_stops.kml) · [Metadata](https://developer.trimet.org/gis/meta_tm_rail_stops.shtml) | December 04, 2024 |
| TriMet Transit Centers | `tm_tran_cen` — [Shapefile](https://developer.trimet.org/gis/data/tm_tran_cen.zip) · [KML](https://developer.trimet.org/gis/data/tm_tran_cen.kml) · [Metadata](https://developer.trimet.org/gis/meta_tm_tran_cen.shtml) | July 31, 2024 |
| TriMet Park and Rides | `tm_parkride` — [Shapefile](https://developer.trimet.org/gis/data/tm_parkride.zip) · [KML](https://developer.trimet.org/gis/data/tm_parkride.kml) · [Metadata](https://developer.trimet.org/gis/meta_tm_parkride.shtml) | June 23, 2026 |

All eight are published in EPSG:2913 (NAD83(HARN) / Oregon North (ft)) and reprojected
here to EPSG:4326. TriMet's note on the GIS page:

> TriMet provides these datasets free of charge in shapefile and KML format. All geospatial datasets created and distributed by TriMet are in NAD83, Oregon State Plane North projection and coordinate system. Refer to the metadata for additional information regarding a specific data layer. TriMet provides data to the general public under certain terms and conditions.

Contact for the source data: **TriMet GIS**, 4012 SE 17th Ave, GIS3,
Portland, OR 97202 —
[gis@trimet.org](mailto:gis@trimet.org).

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


## About this mirror

Maintained by Chris Holmes
([cholmes@9eo.org](mailto:cholmes@9eo.org)), **not affiliated with
TriMet**. Built and regenerated with the scripts in
[`tools/`](https://github.com/cholmes/portolan-catalog-trimet/tree/main/tools).
Conforms to the [Portolan](https://www.portolan-sdi.org/) specification v0.1.0.

The TriMet name and logo are trademarks of TriMet, used here solely as a link
back to [trimet.org](https://trimet.org/), which section 6 of TriMet's
[Terms of Use](https://developer.trimet.org/terms_of_use.shtml) permits.
