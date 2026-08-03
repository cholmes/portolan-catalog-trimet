"""Single source of truth for the TriMet Portolan catalog.

Every string in this file was mined from a TriMet source and is reproduced as
written there. Nothing here is invented. The provenance of each kind of field:

- Collection ``description`` and column ``description`` values come from the
  per-layer metadata pages at ``developer.trimet.org/gis/meta_<layer>.shtml``.
- Column code lists (``values``) come from the "Attribute Information" tables on
  those same pages.
- ``source_updated`` is the "Status / Last update" line on the metadata page.
- Feature counts, bboxes and value frequencies are measured from the data.
- Cartographic colors come from TriMet's own published styles: the GeoServer SLD
  ``ott:rail`` and the MapLibre style ``tiles.trimet.org/styles/trimet-routes``.

If a fact is not in one of those places, it does not belong in this file.
"""

# --------------------------------------------------------------------------
# Catalog-level
# --------------------------------------------------------------------------

PORTOLAN_SCHEMA = "https://schemas.portolan-sdi.org/portolan/v0.1.0/schema.json"

CATALOG_ID = "trimet"
CATALOG_TITLE = "TriMet Geospatial Data"
# STAC Browser renders descriptions as Markdown, so references are links.
CATALOG_DESCRIPTION = (
    "A cloud-native mirror of the eight geospatial datasets TriMet publishes at "
    "[developer.trimet.org/gis](https://developer.trimet.org/gis/) — the transit "
    "district boundary, fixed-route alignments, rail lines, stops, route stops, "
    "rail stops, transit centers and park and rides for the Portland, Oregon "
    "metropolitan area. TriMet distributes these as Shapefile and KML; this "
    "catalog republishes them as GeoParquet and PMTiles with the original files, "
    "KML and metadata linked from every collection. The GeoParquet keeps TriMet's "
    "native EPSG:2913 (NAD83(HARN) / Oregon North, international feet), so "
    "lengths and areas are in feet; only the PMTiles are reprojected to WGS84. "
    "Visualization styles reproduce TriMet's own published cartography.\n\n"
    "Each collection carries an "
    "[**AGENTS.md** agent guide](https://source.coop/cholmes/trimet/AGENTS.md) "
    "alongside its README — join keys, the quirks that produce silently wrong "
    "answers, and query recipes that have each been run against the published "
    "files."
)

# The base URL the published catalog will live at.
# Raw bytes. Use for data files, images, and anything a program fetches.
PUBLIC_BASE = "https://data.source.coop/cholmes/trimet"
# The rendered Source Cooperative UI. Use for links a person clicks: it shows
# READMEs and directory listings, where the data host returns raw bytes or 404s
# on a directory.
BROWSE_BASE = "https://source.coop/cholmes/trimet"
S3_BASE = "s3://us-west-2.opendata.source.coop/cholmes/trimet"

# The catalog's data browser: map preview, per-collection downloads, schema,
# license and outbound links. Not just a map, so it is not named as one.
BROWSER_URL = "https://cholmes.github.io/trimet-data-browser"
BROWSER_NAME = "data browser"

# Both halves are open source and take contributions. Named in the published
# docs so a reader who spots a problem knows where it is fixed.
CATALOG_REPO = "https://github.com/cholmes/portolan-catalog-trimet"
BROWSER_REPO = "https://github.com/cholmes/trimet-data-browser"

GIS_PAGE = "https://developer.trimet.org/gis/"
TERMS_URL = "https://developer.trimet.org/terms_of_use.shtml"
DATA_BASE = "https://developer.trimet.org/gis/data"
META_BASE = "https://developer.trimet.org/gis"

# From the TriMet GIS page, reproduced verbatim.
GIS_PAGE_NOTE = (
    "TriMet provides these datasets free of charge in shapefile and KML format. "
    "All geospatial datasets created and distributed by TriMet are in NAD83, "
    "Oregon State Plane North projection and coordinate system. Refer to the "
    "metadata for additional information regarding a specific data layer. TriMet "
    "provides data to the general public under certain terms and conditions."
)

# Contact block repeated on every TriMet GIS metadata page.
TRIMET_CONTACT = {
    "name": "TriMet GIS",
    "address": "4012 SE 17th Ave, GIS3",
    "city": "Portland, OR 97202",
    "email": "gis@trimet.org",
}

HOST = {
    "name": "Chris Holmes",
    "email": "cholmes@9eo.org",
}

# TriMet's terms of use do not grant redistribution rights for the GIS
# downloads, so the SPDX value is `other` and a license link is required.
LICENSE = "other"

# The GeoParquet keeps this, TriMet's native CRS. Only the PMTiles are
# reprojected, because tiles are WGS84 by definition.
SOURCE_CRS = "EPSG:2913"
SOURCE_CRS_NAME = "NAD83(HARN) / Oregon North (ft)"
# Reproduced from the "Spatial Reference Information" block on every page.
SOURCE_CRS_TRIMET = "NAD_1983_HARN_StatePlane_Oregon_North_FIPS_3601"

# --------------------------------------------------------------------------
# TriMet's published cartographic palette
# --------------------------------------------------------------------------
# Rail colors as used in TriMet's GeoServer SLD `ott:rail`, whose filters key on
# exactly the `line` values carried by the rail-lines and rail-stops layers.
SLD_RAIL = {
    "B": "#084C8D",   # MAX Blue Line
    "G": "#008852",   # MAX Green Line
    "R": "#D81526",   # MAX Red Line
    "Y": "#F8C213",   # MAX Yellow Line
    "O": "#F58220",   # MAX Orange Line
    "NS": "#84BD00",  # Portland Streetcar North/South Line
    "AL": "#CE0F69",  # Portland Streetcar A Loop
    "BL": "#0093B2",  # Portland Streetcar B Loop
    "WES": "#000000",  # WES; the SLD sets no stroke color, so SLD default black
}

# Base stroke color per `line` value, read off the first LineSymbolizer of each
# SLD rule. Shared trackage takes the base color of its trunk line.
RAIL_BASE = {
    "BGRY": "#084C8D", "BGR": "#084C8D", "BRY": "#084C8D", "BR": "#084C8D",
    "BG": "#084C8D", "B": "#084C8D",
    "GY": "#008852", "G": "#008852",
    "GO": "#F58220", "O": "#F58220", "O/AL/BL": "#F58220",
    "R": "#D81526", "Y": "#F8C213",
    "NS": "#84BD00", "NS/AL": "#84BD00", "NS/BL": "#84BD00", "NS/AL/BL": "#84BD00",
    "AL": "#CE0F69", "AL/BL": "#CE0F69",
    "BL": "#0093B2",
    "WES": "#000000",
}

# Dashed overlays, in SLD document order after the base stroke. Each entry is
# (color, dasharray-in-SLD-pixels). MapLibre dasharrays are in line-widths, so
# the generator divides by the line width.
RAIL_OVERLAYS = {
    "BGRY": [("#D81526", [12.0, 4.0]), ("#008852", [8.0, 8.0]), ("#F8C213", [4.0, 12.0])],
    "BGR": [("#008852", [16.0, 8.0]), ("#D81526", [8.0, 16.0])],
    "BRY": [("#D81526", [8.0, 4.0]), ("#F8C213", [4.0, 8.0])],
    "BR": [("#D81526", [8.0, 8.0])],
    "BG": [("#008852", [8.0, 8.0])],
    "GY": [("#F8C213", [8.0, 8.0])],
    "GO": [("#008852", [8.0, 8.0])],
    "NS/AL": [("#CE0F69", [8.0, 8.0])],
    "NS/BL": [("#0093B2", [8.0, 8.0])],
    "NS/AL/BL": [("#CE0F69", [16.0, 8.0]), ("#0093B2", [8.0, 16.0])],
    "AL/BL": [("#0093B2", [8.0, 8.0])],
    "O/AL/BL": [("#CE0F69", [16.0, 8.0]), ("#0093B2", [8.0, 8.0])],
}

# `AUX` is documented in TriMet's metadata as "Auxiliary track. No revenue
# service" and appears in the data, but TriMet's SLD has no rule for it. This
# catalog renders it in a neutral gray so the segments are not silently dropped.
RAIL_AUX_COLOR = "#9AA0A6"

# From the MapLibre style `tiles.trimet.org/styles/trimet-routes`, which draws
# the whole TriMet network. `transit_bus` is a flat color; MAX, streetcar and
# BRT read `route_color` out of the GTFS feed.
BUS_LINE_COLOR = "rgba(19, 99, 144, 1)"   # #136390
RAIL_TMS_COLOR = "rgba(0,0,0, 1)"         # `transit_rail`, i.e. WES

# Official route colors from TriMet's GTFS `routes.txt` (`route_color`). These
# are what `transit_max`, `transit_sc` and `transit_brt` resolve to.
GTFS_ROUTE_COLORS = {
    "MAX Blue Line": "#1359AE",
    "MAX Green Line": "#008342",
    "MAX Red Line": "#C41F3E",
    "MAX Yellow Line": "#FFC52F",
    "MAX Orange Line": "#D05F27",
    "WES Commuter Rail": "#6E6E6E",
    "Portland Streetcar - NS Line": "#72A130",
    "Portland Streetcar - A Loop": "#D91965",
    "Portland Streetcar - B Loop": "#4650BE",
    "Portland Aerial Tram": "#898E91",
    "FX2 Division": "#61A60E",
    "Bus": "#4679AA",
}

# Service-type palette, assembled from the GTFS colors above so that a `type`
# styled map agrees with TriMet's own maps.
TYPE_COLORS = {
    "BUS": "#4679AA",
    "MAX": "#1359AE",
    "SC": "#72A130",
    "CR": "#6E6E6E",
    "AT": "#898E91",
    "BSC": "#0093B2",
    "MAX/SC": "#D05F27",
}

# TriMet basemap palette, from `tiles.trimet.org/styles/trimet`.
BASEMAP = {
    "background": "#FFFFFF",
    "water": "#D5EEF8",
    "building": "#EEEEEE",
    "park": "#E1EBB0",
}

# Shared code list for the `TYPE` attribute, reproduced from TriMet's metadata
# pages. Not every layer documents every value; per-layer subsets are set below.
TYPE_VALUES_ALL = {
    "AT": "Aerial Tram.",
    "BUS": "Bus.",
    "CR": "Commuter rail.",
    "MAX": "Light rail.",
    "SC": "Streetcar.",
    "BSC": "Shared Bus and Streetcar.",
    "MAX/SC": "Shared light rail and streetcar",
}

STATUS_VALUES = {
    "Existing": "Service currently provided.",
    "Planned": "In advanced planning stages.",
    "UC": "Under construction.",
}

# --------------------------------------------------------------------------
# Collections
# --------------------------------------------------------------------------
# `title` and the one-line `blurb` come from the TriMet GIS index page.
# `description` comes from the layer's own metadata page.
# `columns[*].description` are the metadata page's "Definition:" lines.

COLLECTIONS = [
    {
        "id": "district-boundary",
        "source": "tm_boundary",
        "title": "TriMet District Boundary",
        "meta_title": "TriMet District Boundary (tm_boundary)",
        "blurb": "TriMet service district boundary.",
        "description": "TriMet district boundary.",
        "geometry": "Polygon",
        "source_updated": "2013-01-09",
        "source_updated_text": "January 09, 2013",
        "count": 1,
        "bbox": [-123.153536, 45.255802, -122.277052, 45.657213],
        "native_bbox": [7522268.6, 584745.1, 7744957.3, 733815.2],
        "columns": [
            {"name": "area_sq_mi", "type": "int64", "description": "Area in square miles"},
            {"name": "acres", "type": "int64", "description": "Area in acres."},
        ],
    },
    {
        "id": "routes",
        "source": "tm_routes",
        "title": "TriMet Routes",
        "meta_title": "Routes (tm_routes)",
        "blurb": "TriMet fixed route alignments (includes bus and rail.)",
        "description": "All existing bus and rail lines.",
        "geometry": "LineString",
        "source_updated": "2026-07-13",
        "source_updated_text": "July 13, 2026",
        "count": 200,
        "bbox": [-123.11573, 45.28495, -122.332951, 45.639118],
        "native_bbox": [7531764.7, 595330.7, 7730400.1, 727210.8],
        "columns": [
            {"name": "rte", "type": "int32", "description": "Route number."},
            {"name": "dir", "type": "int32", "description": "Direction of route.",
             "values": {"0": "Direction 0.", "1": "Direction 1."}},
            {"name": "rte_desc", "type": "string", "description": "Route name."},
            {"name": "public_rte", "type": "string", "description": "Public route number."},
            {"name": "dir_desc", "type": "string", "description": "Description of route direction."},
            {"name": "frequent", "type": "string",
             "description": "Indicates whether a route or route segment has frequent service.",
             "values": {"True": "Route segment has frequent service.",
                        "False": "Route segment does not have frequent service."}},
            {"name": "type", "type": "string", "description": "Type of service.",
             "values": {k: TYPE_VALUES_ALL[k] for k in ("AT", "BUS", "CR", "MAX", "SC")}},
        ],
    },
    {
        "id": "rail-lines",
        "source": "tm_rail_lines",
        "title": "TriMet Rail Lines",
        "meta_title": "Rail Lines (tm_rail_lines)",
        "blurb": "TriMet rail service optimized for cartographic display.",
        "description": (
            "Public transit rail lines. Includes existing, under construction, and "
            "planned MAX, WES, and Portland Streetcar lines. The data have been "
            "generalized to improve cartographic display at smaller scales."
        ),
        "geometry": "LineString",
        "source_updated": "2024-09-26",
        "source_updated_text": "September 26, 2024",
        "count": 171,
        "bbox": [-122.991049, 45.311167, -122.418509, 45.605455],
        "native_bbox": [7563740.0, 607778.2, 7710256.6, 714400.3],
        "columns": [
            {"name": "line", "type": "string", "description": "Line(s) serving a particular segment.",
             "values": {
                 "AL": "Portland Streetcar A Loop",
                 "AL/BL": "Portland Streetcar A & B Loops",
                 "AUX": "Auxiliary track. No revenue service",
                 "B": "MAX Blue Line",
                 "BG": "MAX Blue, and Green Lines",
                 "BGR": "MAX Blue, Green, and Red Lines",
                 "BGRY": "MAX Blue, Green, Red, and Yellow Lines",
                 "BL": "Portland Streetcar B Loop",
                 "BL/NS": "Portland Streetcar B Loop and North/South Line",
                 "BR": "MAX Blue and Red Lines",
                 "G": "MAX Green Line",
                 "GO": "MAX Green and Orange Lines",
                 "GY": "MAX Green and Yellow Lines",
                 "NS": "Portland Streetcar North/South Line",
                 "NS/AL": "Portland Streetcar A Loop and North/South Line",
                 "NS/AL/BL": "Portland Streetcar A & B Loops and North/South Line",
                 "O": "MAX Orange Line",
                 "O/AL/BL": "MAX Orange Line and Portland Streetcar A & B Loops",
                 "R": "MAX Red Line",
                 "WES": "WES (Westside Express Service)",
                 "Y": "MAX Yellow Line",
             }},
            {"name": "passage", "type": "string",
             "description": ("Indicates the infrastructure (if any) over/through which a rail "
                             "segment travels.  This data is intended for use in cartographic "
                             "display rather than analysis"),
             "values": {"bridge": "Rail segment travels over bridge",
                        "surface": "Rail segment travels over ground/surface level",
                        "tunnel": "Rail segment passes through tunnel"}},
            {"name": "status", "type": "string", "description": "Operational status of the segment.",
             "values": {"Existing": "Service currently provided on rail segment",
                        "Planned": "Rail segment in advanced planning stages",
                        "UC": "Rail segment is under construction"}},
            {"name": "type", "type": "string", "description": "Type of service.",
             "values": {"CR": "Commuter rail", "MAX": "Light rail",
                        "MAX/SC": "Shared light rail and streetcar", "SC": "Streetcar"}},
        ],
    },
    {
        "id": "stops",
        "source": "tm_stops",
        "title": "TriMet Stops",
        "meta_title": "Stops (tm_stops)",
        "blurb": "Active TriMet stops (includes bus and rail.)",
        "description": "Active transit stops.",
        "geometry": "Point",
        "source_updated": "2026-07-30",
        "source_updated_text": "July 30, 2026",
        "count": 6316,
        "bbox": [-123.115462, 45.285222, -122.333062, 45.637731],
        "native_bbox": [7531831.2, 595429.4, 7730367.6, 726731.3],
        "columns": [
            {"name": "stop_id", "type": "int32", "description": "Unique identifier."},
            {"name": "stop_name", "type": "string", "description": "Intersection or street address of stop."},
            {"name": "jurisdic", "type": "string", "description": "Jurisdiction (City or County) in which stop is located."},
            {"name": "zipcode", "type": "string", "description": "Zipcode in which stop is located."},
            {"name": "type", "type": "string", "description": "Type of service.",
             "values": {k: TYPE_VALUES_ALL[k] for k in ("AT", "BUS", "CR", "MAX", "SC", "BSC")}},
        ],
    },
    {
        "id": "route-stops",
        "source": "tm_route_stops",
        "title": "TriMet Route Stops",
        "meta_title": "Route Stops (tm_route_stops)",
        "blurb": "Active TriMet stops (includes bus and rail) by route and direction.",
        "description": (
            "Public transit stops for all bus and rail lines. For stops served by "
            "multiple lines there are multiple records in this dataset."
        ),
        "geometry": "Point",
        "source_updated": "2026-07-30",
        "source_updated_text": "July 30, 2026",
        "count": 8314,
        "bbox": [-123.115462, 45.285222, -122.333062, 45.637731],
        "native_bbox": [7531831.2, 595429.4, 7730367.6, 726731.3],
        "columns": [
            {"name": "rte", "type": "int32", "description": "Route number."},
            {"name": "dir", "type": "int32", "description": "Direction of line serving this stop.",
             "values": {"0": "Direction 0.", "1": "Direction 1."}},
            {"name": "rte_desc", "type": "string", "description": "Route name."},
            {"name": "dir_desc", "type": "string", "description": "Description of route direction."},
            {"name": "type", "type": "string", "description": "Type of service.",
             "values": {k: TYPE_VALUES_ALL[k] for k in ("AT", "BUS", "CR", "MAX", "SC")}},
            {"name": "stop_seq", "type": "int32", "description": "Stop sequence number."},
            {"name": "stop_id", "type": "int32", "description": "Unique identifier."},
            {"name": "stop_name", "type": "string", "description": "Intersection or street address of stop."},
            {"name": "jurisdic", "type": "string", "description": "Jurisdiction (City or County) in which stop is located."},
            {"name": "zipcode", "type": "string", "description": "Zipcode in which stop is located."},
            {"name": "frequent", "type": "string",
             "description": "Indicates whether a route or route segment has frequent service.",
             "values": {"True": "Route segment has frequent service.",
                        "False": "Route segment does not have frequent service."},
             "note": ("Present in the shapefile but not listed in TriMet's metadata "
                      "page for this layer; the definition is carried over from "
                      "tm_routes, where FREQUENT is documented.")},
        ],
    },
    {
        "id": "rail-stops",
        "source": "tm_rail_stops",
        "title": "TriMet Rail Stops",
        "meta_title": "Rail Stops (tm_rail_stops)",
        "blurb": "TriMet rail stops optimized for cartographic display.",
        "description": (
            "Public transit rail stops. Includes existing, under construction, and "
            "planned MAX, WES, and Portland Streetcar stops. The data have been "
            "generalized to improve cartographic display at smaller scales."
        ),
        "geometry": "Point",
        "source_updated": "2024-12-04",
        "source_updated_text": "December 04, 2024",
        "count": 169,
        "bbox": [-122.991035, 45.311167, -122.418509, 45.605455],
        "native_bbox": [7563749.3, 607778.2, 7710256.6, 714400.3],
        "columns": [
            {"name": "station", "type": "string", "description": "Name of station."},
            {"name": "line", "type": "string", "description": "Line(s) serving a particular stop.",
             "values": {
                 "AL": "Portland Streetcar A Loop",
                 "AL/BL": "Portland Streetcar A & B Loops",
                 "B": "MAX Blue Line",
                 "BGR": "MAX Blue, Green, and Red Lines",
                 "BGRY": "MAX Blue, Green, Red, and Yellow Lines",
                 "BL": "Portland Streetcar B Loop",
                 "BL/NS": "Portland Streetcar B Loop and North/South Line",
                 "BR": "MAX Blue and Red Lines",
                 "G": "MAX Green Line",
                 "GO": "MAX Green and Orange Lines",
                 "GY": "MAX Green and Yellow Lines",
                 "NS": "Portland Streetcar North/South Line",
                 "NS/AL": "Portland Streetcar A Loop and North/South Line",
                 "NS/AL/BL": "Portland Streetcar A & B Loops and North/South Line",
                 "O": "MAX Orange Line",
                 "R": "MAX Red Line",
                 "WES": "WES (Westside Express Service)",
                 "Y": "MAX Yellow Line",
             }},
            {"name": "status", "type": "string", "description": "Operational status of the stop.",
             "values": {"Existing": "Service currently provided at rail stop",
                        "Planned": "Rail stop in advanced planning stages",
                        "UC": "Rail stop is under construction"}},
            {"name": "type", "type": "string", "description": "Type of service.",
             "values": {"CR": "Commuter rail", "MAX": "Light rail", "SC": "Streetcar"}},
        ],
    },
    {
        "id": "transit-centers",
        "source": "tm_tran_cen",
        "title": "TriMet Transit Centers",
        "meta_title": "Transit Centers (tm_tran_cen)",
        "blurb": "TriMet transit center locations.",
        "description": "Transit Centers.",
        "geometry": "Point",
        "source_updated": "2024-07-31",
        "source_updated_text": "July 31, 2024",
        "count": 15,
        "bbox": [-122.985278, 45.360144, -122.426856, 45.577122],
        "native_bbox": [7565216.0, 624437.2, 7708126.4, 704049.3],
        "columns": [
            {"name": "name", "type": "string", "description": "Name of Transit Center."},
            {"name": "address", "type": "string", "description": "Transit Center street address or major intersection."},
            {"name": "city", "type": "string", "description": "City in which Transit Center is located."},
            {"name": "county", "type": "string", "description": "County in which Transit Center is located."},
            {"name": "zipcode", "type": "string", "description": "Zipcode in which Transit Center is located."},
            {"name": "status", "type": "string", "description": "Operational status of segment.",
             "values": {"Existing": "Transit Center is operational.",
                        "Planned": "Transit Center is in advanced planning stages.",
                        "UC": "Transit Center is under construction."}},
        ],
    },
    {
        "id": "park-and-rides",
        "source": "tm_parkride",
        "title": "TriMet Park and Rides",
        "meta_title": "Park and Rides (tm_parkride)",
        "blurb": "TriMet park and ride locations.",
        "description": "TriMet park and ride locations.",
        "geometry": "Point",
        "source_updated": "2026-06-23",
        "source_updated_text": "June 23, 2026",
        "count": 46,
        "bbox": [-122.990552, 45.284869, -122.332396, 45.605293],
        "native_bbox": [7563860.3, 595297.0, 7730536.0, 714343.3],
        "columns": [
            {"name": "name", "type": "string", "description": "Name of park and ride."},
            {"name": "address", "type": "string", "description": "Park and ride street address or major intersection."},
            {"name": "city", "type": "string", "description": "City in which park and ride is located."},
            {"name": "county", "type": "string", "description": "County in which park and ride is located."},
            {"name": "zipcode", "type": "string", "description": "Zipcode in which park and ride is located."},
            {"name": "owner", "type": "string",
             "description": "Indicates whether a park and ride is TriMet owned or a shared use facility.",
             "values": {"TriMet": "TriMet owned.", "Shared": "Shared use."}},
            {"name": "spaces", "type": "int32",
             "description": "Indicates number of parking spaces available at park and ride."},
            {"name": "status", "type": "string", "description": "Operational status of park and ride.",
             "values": {"Existing": "Park and ride is operational.",
                        "Planned": "Park and ride is in advanced planning stages.",
                        "UC": "Park and ride is under construction."}},
        ],
    },
]

BY_ID = {c["id"]: c for c in COLLECTIONS}

# Catalog extent is the union of the collection extents, which is the district
# boundary since every other layer sits inside it.
# STAC requires the collection and catalog extent in WGS84 regardless of the
# data's own CRS, so these stay in degrees while the data stays in feet.
CATALOG_BBOX = [-123.153536, 45.255802, -122.277052, 45.657213]


def source_links(coll):
    """The three original TriMet artifacts for a collection."""
    s = coll["source"]
    return {
        "shapefile": f"{DATA_BASE}/{s}.zip",
        "kml": f"{DATA_BASE}/{s}.kml",
        "metadata": f"{META_BASE}/meta_{s}.shtml",
    }
