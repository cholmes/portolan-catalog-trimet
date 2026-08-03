"""Hand-authored prose for the catalog's README and AGENTS files.

Everything here is either quoted from a TriMet source or is a fact measured from
the data and verified by running the query shown. The generator in
``make_docs.py`` supplies the numbers, tables and boilerplate; this file supplies
the judgement — what the data is for, where it will mislead you, and which
queries are worth stealing.

Every SQL snippet in RECIPES has been run against the published files. If you
change one, run it before committing; a broken example costs more trust than no
example.
"""

# Facts that hold across the whole catalog and belong in every agent guide.
CRS_NOTE = """\
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
"""

LICENSE_NOTE = """\
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
"""

CATALOG_INTRO = """\
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
"""

# ---------------------------------------------------------------------------
# Per-collection prose.
#   summary      — the opening paragraph of the README, past the generated line
#   uses         — what the data has actually supported
#   limitations  — when not to use it. The highest-value section.
#   quirks       — list of (heading, body) for AGENTS.md
#   recipes      — list of (title, sql) — every one verified by running it
#   related      — list of (collection-id, why)
# ---------------------------------------------------------------------------

COLLECTIONS = {

"district-boundary": dict(
summary="""\
A single polygon: the legal service district TriMet is chartered to serve. It
carries TriMet's own area figures — 533 square miles, 341,554 acres — as
attributes, so you do not need to compute area from the geometry.

The district covers most of the urbanized parts of Multnomah, Washington and
Clackamas counties. Its edge is not a county boundary and not the Metro urban
growth boundary; it is the taxing and service district, and it excludes parts of
all three counties.""",
uses="""\
- Clipping other datasets to TriMet's actual service area rather than to county lines.
- As the denominator in transit-access analyses: what share of district population,
  jobs or parcels lies within a given walk of a stop.
- As a base layer for maps of the other seven collections — every thumbnail in
  this catalog draws it underneath for exactly that reason.""",
limitations="""\
- **This is a service district, not a jurisdiction.** It does not align with city
  limits, county boundaries, or Metro's urban growth boundary. Do not use it as a
  proxy for "Portland" or for any administrative geography.
- **It is the oldest layer here by more than a decade.** TriMet's metadata page
  gives its last update as January 09, 2013. The district has been essentially
  stable, but treat the edge as approximate for anything legal or financial.
- **Being inside the boundary does not mean being served.** Large parts of the
  district have no stop within walking distance. Join to `stops` to answer
  service questions.""",
quirks=[
("The area columns are integers, not floats",
 """TriMet's metadata page documents `AREA_SQ_MI` and `ACRES` as *Float*, length 13.
In the actual DBF they are integers, and this catalog carries them through as
`int64`: 533 and 341554 exactly. If you need sub-square-mile precision, compute
it from the geometry — see the CRS section — rather than trusting these to be
rounded floats."""),
("One feature, so no spatial index will help you",
 """The file holds a single polygon with a few thousand vertices. Row-group pruning
does nothing here. For repeated point-in-polygon tests, read the geometry once
into a variable rather than re-scanning the file per query."""),
("It is a plain polygon, not a multipolygon",
 """`ST_GeometryType` returns `POLYGON`. There are no islands or detached parts, so
you can use it directly in `ST_Contains` / `ST_Within` without dumping parts."""),
],
recipes=[
("Which stops fall inside the district — and how many do not", """\
SELECT ST_Within(s.geometry, b.geometry) AS inside, count(*)
FROM 'stops/stops.parquet' s
CROSS JOIN 'district-boundary/district-boundary.parquet' b
GROUP BY 1;"""),
("Confirm TriMet's stated area against the geometry", """\
-- The geometry is already in feet, so no transform is needed.
SELECT area_sq_mi AS trimet_says,
       round(ST_Area(geometry) / 27878400.0, 1) AS computed_sq_mi,
       round(ST_Area(geometry) / 43560.0)       AS computed_acres,
       acres AS trimet_acres
FROM 'district-boundary/district-boundary.parquet';"""),
],
related=[("stops", "the service the district exists to deliver"),
         ("routes", "alignments, a few of which run beyond the district edge")],
),

# ---------------------------------------------------------------------------
"routes": dict(
summary="""\
Every fixed-route alignment TriMet operates, bus and rail together, as one
line per route *and direction*. 200 features covering 179 bus, 13 MAX, 4
streetcar, 2 commuter rail and 2 aerial tram segments.

The `frequent` flag marks TriMet's Frequent Service network — 51 of the 200
route-directions — which is the set of lines scheduled often enough that riders
are told not to consult a timetable.""",
uses="""\
- Drawing the network. This is the layer behind TriMet's own system maps, and
  `styles/default.json` reproduces the line weights and colors from TriMet's
  published `trimet-routes` MapLibre style.
- Measuring route-miles by mode or by jurisdiction.
- Corridor analysis: buffering alignments to find what lies within a given
  distance of transit.""",
limitations="""\
- **`rte` is not a primary key.** 87 route numbers appear twice, once per
  direction. The key is `(rte, dir)`. A `GROUP BY rte` that forgets this
  double-counts every two-way route.
- **These are alignments, not schedules.** Nothing here says how often a bus
  runs, when it runs, or whether it runs today. `frequent` is the only
  service-level hint, and it is a flag rather than a frequency. Use the
  [GTFS feed](https://developer.trimet.org/GTFS.shtml) for anything time-based.
- **Geometry type is mixed.** 91 features are `LINESTRING` and 109 are
  `MULTILINESTRING`, so a route can be several disconnected pieces. Functions
  that assume a single linestring will silently misbehave — see the quirks.
- **Not a rail cartography layer.** For drawing rail specifically, `rail-lines`
  is generalized for display and carries per-line colors; the MAX geometry here
  is the operational alignment.""",
quirks=[
("`(rte, dir)` is the key, not `rte`",
 """200 rows, 113 distinct `rte` values, 87 of which appear twice. `dir` is 0 or 1
and TriMet documents it only as "Direction 0" and "Direction 1" — the human
meaning lives in `dir_desc` (e.g. "To Portland"). Always group or join on the
pair."""),
("Use `public_rte` for display, `rte` for joining",
 """`rte` is an integer and `public_rte` is a string. They differ where a service has
a lettered public name: route 2 is displayed as **FX2**. Show `public_rte` to
humans; join on `rte`, which is what `route-stops` carries."""),
("Mixed LINESTRING / MULTILINESTRING breaks naive length code",
 """`ST_Length_Spheroid` returns `nan` on this layer for both geometry types, so do
not reach for it. Project and use `ST_Length` instead (see the recipes). If you
need per-segment work, `ST_Dump` the multilinestrings first."""),
("`frequent` is a string, not a boolean",
 """Values are the literal strings `'True'` and `'False'`, not SQL booleans. Compare
with `frequent = 'True'`; a bare `WHERE frequent` will not parse."""),
("Some alignments leave the district",
 """A handful of routes run past the district boundary — service to Estacada and
Sherwood, for example. Do not assume `routes` is contained by
`district-boundary`."""),
],
recipes=[
("Longest routes in kilometres, one direction only", """\
-- ST_Length returns feet directly; 5280 ft to the mile.
SELECT rte, any_value(rte_desc) AS name,
       round(sum(ST_Length(geometry)) / 5280.0, 1) AS miles
FROM 'routes/routes.parquet'
WHERE dir = 0
GROUP BY rte
ORDER BY miles DESC
LIMIT 10;"""),
("Route-kilometres by mode", """\
SELECT type,
       round(sum(ST_Length(geometry)) / 5280.0, 1) AS miles,
       count(*) AS segments
FROM 'routes/routes.parquet'
GROUP BY type
ORDER BY miles DESC;"""),
("The Frequent Service network, as displayed to riders", """\
SELECT DISTINCT public_rte, rte_desc, type
FROM 'routes/routes.parquet'
WHERE frequent = 'True'
ORDER BY rte;"""),
],
related=[("route-stops", "the stops along each of these route-directions, joined on `(rte, dir)`"),
         ("rail-lines", "rail drawn for cartography, with per-line colors"),
         ("stops", "the deduplicated stop list")],
),

# ---------------------------------------------------------------------------
"rail-lines": dict(
summary="""\
TriMet's rail network — MAX light rail, WES commuter rail and Portland Streetcar
— as 171 segments generalized for cartographic display. Each segment records
which line or lines run over it (`line`), whether it is at surface level, on a
bridge or in a tunnel (`passage`), its operational status, and its service type.

The `line` codes are what make this layer unusual: a value like `BGR` means the
Blue, Green and Red lines all share that track. That is why TriMet draws it with
a solid base stroke plus one dashed overlay per additional line, and why
`styles/default.json` here does the same.""",
uses="""\
- Drawing the rail network at metro scale. This is what the layer is *for* —
  TriMet says so — and this collection ships a direct reproduction of TriMet's
  own GeoServer style for it.
- Showing which services share trackage, which the `line` codes encode directly
  and no other layer in this catalog does.
- Distinguishing at-grade from grade-separated running via `passage`.""",
limitations="""\
- **Generalized geometry. Do not measure it.** TriMet states the data "have been
  generalized to improve cartographic display at smaller scales". Track lengths
  computed here will be short, and the alignment will not sit on the real
  right-of-way at large scale. Use `routes` for the operational alignment.
- **`passage` is a drawing hint, not an inventory.** TriMet's own note: this
  attribute "is intended for use in cartographic display rather than analysis".
  It does not identify specific bridges or tunnels.
- **Not a track or signalling model.** Segments are cartographic units. There is
  no notion of track count, direction of running, junctions or switches.""",
quirks=[
("The metadata documents `BL/NS`; the data contains `NS/BL`",
 """TriMet's metadata page lists a code `BL/NS` ("Portland Streetcar B Loop and
North/South Line"). That string does not occur in the data. What the data
actually carries is **`NS/BL`**, on 2 segments here and 12 stops in `rail-stops`.
Filter on `NS/BL`. A query written from the published code list alone returns
nothing."""),
("`AUX` is in the data and in TriMet's code list, but has no style rule",
 """7 segments are `AUX` — "Auxiliary track. No revenue service", i.e. yard leads and
connecting track. TriMet's own SLD has no rule for `AUX`, so on TriMet's maps
these segments are invisible. This catalog draws them in neutral gray rather than
dropping them, so be aware they will appear where TriMet's maps show nothing.
**Exclude `AUX` when counting revenue track.**"""),
("Everything is `Existing` right now",
 """`status` documents `Existing`, `Planned` and `UC` (under construction), but all
171 current segments are `Existing`. Code that branches on status is not wrong,
it is just untested against this snapshot — and the values will reappear as
TriMet adds projects."""),
("`line` is a set, encoded as a string",
 """There is no join table. To ask "which segments does the Blue Line touch", you
must match any code containing `B` as a *component*, which is not a substring
test — `B` appears in `BL` (B Loop, a streetcar) and `BGR`. The reliable approach
is an explicit list of the codes that include the line you want; see the
recipes."""),
("Colors here differ slightly from the GTFS colors",
 """TriMet's SLD uses `#084C8D` for the Blue Line; its GTFS `route_color` is
`#1359AE`. Both are authentic TriMet values from different systems. This
collection's `default.json` follows the SLD, because the SLD is the style written
for *this layer*; `by-type.json` follows GTFS."""),
],
recipes=[
("Segments carrying the MAX Blue Line, handling shared track correctly", """\
-- 'B' as a component, not as a substring: BL is the streetcar B Loop.
SELECT line, type, passage, count(*) AS segments
FROM 'rail-lines/rail-lines.parquet'
WHERE line IN ('B','BR','BG','BGR','BGRY','BRY')
GROUP BY ALL
ORDER BY segments DESC;"""),
("How much track is shared, and by how many lines", """\
SELECT line,
       CASE WHEN line IN ('AUX','WES') THEN 0
            ELSE length(replace(replace(line,'/',''),'AUX','')) END AS lines_sharing,
       count(*) AS segments
FROM 'rail-lines/rail-lines.parquet'
WHERE type <> 'CR' AND line <> 'AUX'
GROUP BY ALL
ORDER BY lines_sharing DESC, segments DESC;"""),
("Grade separation by mode, excluding non-revenue track", """\
SELECT type, passage, count(*) AS segments
FROM 'rail-lines/rail-lines.parquet'
WHERE line <> 'AUX'
GROUP BY ALL
ORDER BY type, segments DESC;"""),
],
related=[("rail-stops", "the stations on these lines, sharing the same `line` codes and colors"),
         ("routes", "the operational, non-generalized alignment of the same rail service")],
),

# ---------------------------------------------------------------------------
"stops": dict(
summary="""\
Every active TriMet stop, deduplicated — one row per physical stop, 6,316 of
them. 6,075 are bus stops; the rest are 161 MAX platforms, 58 streetcar stops, 14
shared bus/streetcar stops, 6 WES platforms and 2 aerial tram terminals.

`stop_id` is TriMet's public stop number, the one printed on the pole and used by
the arrivals API, which makes this collection the natural bridge between this
catalog and TriMet's real-time services.""",
uses="""\
- Transit-access analysis: how many people, jobs or addresses lie within a walk
  of a stop.
- Joining spatial data to TriMet's real-time arrivals, which is keyed on the same
  `stop_id`.
- Stop-density and coverage mapping — `styles/density.json` is built for this.""",
limitations="""\
- **Active stops only.** Discontinued stops are absent, so this is a snapshot and
  not a history. `stop_id` values are not re-issued, but a stop that vanishes
  between vintages simply disappears.
- **No service information.** Which routes serve a stop is not in this file; that
  is what `route-stops` is for. Nor is there any frequency, shelter, accessibility
  or boarding-count attribute.
- **`stop_name` is a location, not a name.** Values are intersections or street
  addresses ("SE Hawthorne & 39th"), so they are not unique and not suitable as
  display names for rail stations — use `rail-stops.station` for those.
- **Position is the pole, not the boarding area.** Stops on opposite sides of a
  street are separate features a few metres apart; do not treat a stop as a
  single bidirectional node without checking.""",
quirks=[
("`stop_id` joins cleanly to `route-stops` — exactly",
 """All 6,316 `stop_id` values here appear in `route-stops`, and `route-stops` has
exactly 6,316 distinct `stop_id` values. The two agree perfectly, and `stop_name`
never disagrees between them. This is the catalog's most reliable join."""),
("`type` has a value here that the routes layer does not",
 """`BSC`, "Shared Bus and Streetcar", appears on 14 stops. It is documented on the
stops metadata page but not on the routes or route-stops pages, and it does not
occur in those layers. Code that maps `type` through a lookup built from
`routes` will miss it."""),
("`zipcode` is a string; `stop_id` is an integer",
 """`zipcode` is text (leading zeros are not an issue in Oregon, but the column is
still typed as a string). `stop_id` is `int32` — do not quote it when joining."""),
("The same `stop_id` is used by TriMet's arrivals API",
 """`stop_id` is the public stop number. It is the `locIDs` parameter of TriMet's
arrivals endpoint, which is how you get from a point in this catalog to live
data. That API needs a registered app ID and is governed by separate terms."""),
],
recipes=[
("Stops by jurisdiction and mode", """\
SELECT jurisdic, type, count(*) AS stops
FROM 'stops/stops.parquet'
GROUP BY ALL
HAVING count(*) > 20
ORDER BY stops DESC;"""),
("Stops within 400 m of a transit center — note the reprojection", """\
-- Both layers are in feet, so the radius is just a number of feet.
-- 1312.34 ft = 400 m. Use 1320 for a quarter mile.
SELECT tc.name, count(*) AS stops_within_400m
FROM 'transit-centers/transit-centers.parquet' tc
JOIN 'stops/stops.parquet' s
  ON ST_DWithin(tc.geometry, s.geometry, 1312.34)
GROUP BY tc.name
ORDER BY stops_within_400m DESC;"""),
("How many routes serve each stop, by joining to route-stops", """\
SELECT s.stop_id, s.stop_name, count(DISTINCT r.rte) AS routes
FROM 'stops/stops.parquet' s
JOIN 'route-stops/route-stops.parquet' r USING (stop_id)
GROUP BY 1, 2
ORDER BY routes DESC
LIMIT 10;"""),
],
related=[("route-stops", "the same stops exploded by route and direction; join on `stop_id`"),
         ("rail-stops", "rail platforms with real station names, but a *different* id space"),
         ("transit-centers", "the 15 major transfer hubs")],
),

# ---------------------------------------------------------------------------
"route-stops": dict(
summary="""\
The same stops as `stops`, but exploded by the service that calls at them: one
row per stop per route-direction, 8,314 rows over 6,316 distinct stops. A stop
served by four routes appears four times.

This is the only layer in the catalog that connects a stop to a route, and it
carries `stop_seq`, the position of the stop along its route-direction, which is
what lets you reconstruct the order of stops along a line.""",
uses="""\
- Building the stop sequence for a route — the ordered list a timetable or a
  routing engine needs.
- Finding transfer points: stops where many distinct `rte` values meet.
- Answering "which routes serve this stop" and "which stops does this route
  serve", neither of which any other layer here can do.""",
limitations="""\
- **Every count is inflated unless you deduplicate.** `count(*)` is 8,314, which
  is not a number of stops. Use `count(DISTINCT stop_id)` for stops, or work from
  the `stops` collection.
- **`stop_seq` restarts at every route-direction.** It is meaningful only within
  a `(rte, dir)` group. Ordering the whole table by `stop_seq` is meaningless.
- **No times, no frequencies.** Sequence is order, not schedule. Nothing says how
  long it takes to get from stop 4 to stop 5.
- **Directions are not mirror images.** The stop list for `dir = 0` and `dir = 1`
  of the same route often differs in length, because of one-way streets and
  stops served in one direction only.""",
quirks=[
("`frequent` is here but is *not* in TriMet's metadata for this layer",
 """The shapefile carries a `FREQUENT` column. TriMet's metadata page for
`tm_route_stops` does not document it — the page lists ten attributes and this is
not one of them. The definition carried in this catalog's `table:columns` is
borrowed from `tm_routes`, where `FREQUENT` *is* documented, and the column
description says so. Treat it as reliable but formally undocumented upstream."""),
("The key is `(rte, dir, stop_id)`",
 """No single column is unique. `stop_id` repeats across routes, `(rte, dir)` repeats
across stops, and `stop_seq` repeats across route-directions."""),
("Average 1.27 routes per stop, but the tail is long",
 """Most stops are served by a single route. The busiest, Clackamas Town Center, is
served by 11. Analyses that assume one route per stop will be right most of the
time and badly wrong at exactly the places that matter."""),
("`stop_name` agrees with `stops` on every row",
 """Verified: zero disagreements across all 8,314 rows. You can join on `stop_id`
alone without worrying about reconciling names."""),
("No `public_rte` here",
 """Unlike `routes`, this layer carries only the integer `rte`. To show riders the
public name (FX2 rather than 2), join to `routes` on `(rte, dir)`."""),
],
recipes=[
("The ordered stop list for one route-direction", """\
SELECT stop_seq, stop_id, stop_name, jurisdic
FROM 'route-stops/route-stops.parquet'
WHERE rte = 9 AND dir = 0
ORDER BY stop_seq;"""),
("Transfer points: stops where the most routes meet", """\
SELECT stop_id, any_value(stop_name) AS stop_name,
       count(DISTINCT rte) AS routes,
       string_agg(DISTINCT type, ', ') AS modes
FROM 'route-stops/route-stops.parquet'
GROUP BY stop_id
ORDER BY routes DESC
LIMIT 15;"""),
("Attach public route names by joining back to routes", """\
SELECT DISTINCT rs.stop_id, rs.stop_name, r.public_rte, r.rte_desc, r.dir_desc
FROM 'route-stops/route-stops.parquet' rs
JOIN 'routes/routes.parquet' r USING (rte, dir)
WHERE rs.stop_id = 13248
ORDER BY r.public_rte;"""),
("Stops reachable without a timetable — the Frequent Service stop set", """\
SELECT count(DISTINCT stop_id) AS frequent_service_stops
FROM 'route-stops/route-stops.parquet'
WHERE frequent = 'True';"""),
],
related=[("stops", "the deduplicated stop list; join on `stop_id`"),
         ("routes", "route attributes including `public_rte`; join on `(rte, dir)`")],
),

# ---------------------------------------------------------------------------
"rail-stops": dict(
summary="""\
The 169 MAX, WES and Portland Streetcar stops, generalized for cartographic
display and carrying real **station names** rather than intersections. Each stop
records the line or lines that serve it in the same `line` code space as
`rail-lines`, so the two layers style consistently.""",
uses="""\
- Labelling rail maps. `styles/labeled.json` is the reason this collection exists
  in a mirror — `station` gives you the names riders actually use.
- Identifying interchange stations, which are the stops whose `line` code lists
  several services.
- Pairing with `rail-lines` to draw a complete, correctly-colored rail diagram.""",
limitations="""\
- **Generalized positions.** As with `rail-lines`, TriMet states this data has
  been generalized for display at smaller scales. Platform positions are
  approximate; do not use them for pedestrian routing or precise accessibility
  work.
- **There is no `stop_id` here.** This layer does not carry TriMet's public stop
  number, so it does not join to `stops` or `route-stops` on an id. Matching must
  be spatial or by name, and neither is exact.
- **A station is one point, not one per platform.** Directional platforms are
  collapsed, so counts here are lower than the rail stop counts in `stops`
  (169 versus 161 MAX plus 58 streetcar plus 6 WES rows there).""",
quirks=[
("No id column — this layer does not join to the rest of the catalog",
 """`rail-stops` carries `station`, `line`, `status`, `type` and nothing else. There
is no `stop_id`. To connect a station to real-time arrivals or to route service,
do a nearest-neighbour spatial join against `stops`, and check the result: the
generalized geometry means the nearest `stops` point is usually right but not
guaranteed."""),
("`NS/BL` again — the metadata says `BL/NS`",
 """Exactly as in `rail-lines`: TriMet's code list documents `BL/NS`, the data
contains `NS/BL`, and here it is the code on 12 of the 169 stops. Filter on
`NS/BL`."""),
("Counts here do not match the rail rows in `stops`",
 """169 stations here against 225 rail-typed rows in `stops`. Neither is wrong: this
layer collapses directional platforms into one station point, and `stops` keeps
them separate. Pick the one that matches your question and say which you used."""),
("`station` is not unique",
 """Streetcar loops in particular repeat station names at nearby points. Do not use
`station` as a key."""),
("All `Existing`, as with the line layer",
 """`Planned` and `UC` are documented but unused in this snapshot."""),
],
recipes=[
("Interchange stations, ordered by how many services meet there", """\
SELECT station, line, type,
       length(replace(line, '/', '')) AS approx_services
FROM 'rail-stops/rail-stops.parquet'
WHERE length(line) > 1
ORDER BY approx_services DESC, station;"""),
("Stations per line code", """\
SELECT line, type, count(*) AS stations
FROM 'rail-stops/rail-stops.parquet'
GROUP BY ALL
ORDER BY stations DESC;"""),
("Match rail stations to their nearest public stop id", """\
-- No shared key exists, so this is a nearest-neighbour join. Check the distance
-- column before trusting a match; the geometry here is generalized.
SELECT rs.station, s.stop_id, s.stop_name,
       round(ST_Distance(rs.geometry, s.geometry), 1) AS feet
FROM 'rail-stops/rail-stops.parquet' rs
JOIN 'stops/stops.parquet' s ON s.type IN ('MAX','CR','SC','BSC')
QUALIFY row_number() OVER (PARTITION BY rs.station, rs.geometry ORDER BY feet) = 1
ORDER BY feet DESC
LIMIT 10;"""),
],
related=[("rail-lines", "the track these stations sit on, sharing the `line` code space and palette"),
         ("stops", "the full stop list, with public `stop_id` values but no station names")],
),

# ---------------------------------------------------------------------------
"transit-centers": dict(
summary="""\
The 15 transit centers — the timed-transfer hubs where many routes meet and where
riders are expected to change. Each carries a name, street address, city, county
and ZIP code.

They span all three counties of the district: 7 in Multnomah, 5 in Washington and
3 in Clackamas.""",
uses="""\
- Anchoring network maps: 15 labelled points give a reader the shape of the
  system in one screen, which is what `styles/labeled.json` is for.
- Defining hub catchments for access analysis.
- As the join target for "how much service is concentrated here" questions,
  answered spatially against `stops` or `route-stops`.""",
limitations="""\
- **A transit center is not a rail station.** Some are, some are bus-only. The
  layer carries no mode attribute; determine mode by joining spatially to
  `rail-stops` or `stops`.
- **The point is the facility, not each platform.** A transit center may have a
  dozen bus bays; there is one point for all of them.
- **No capacity, amenity or accessibility data.** Only location and address.
- **`status` exists but every row is `Existing`.** No planned hubs appear in this
  snapshot.""",
quirks=[
("Fifteen rows, and no key beyond `name`",
 """There is no id column. `name` is unique across the 15 rows here, but it is a
display string and TriMet may reword it; do not persist it as a foreign key."""),
("`city` is the municipality, `jurisdic` in other layers may disagree",
 """`transit-centers` carries `city` and `county`; `stops` carries a single
`jurisdic` field that may hold either a city or a county. They are not the same
vocabulary — do not join on them."""),
("Several share a name with a park and ride",
 """"Gateway/NE 99th Ave", "Sunset", "Willow Creek/SW 185th Ave" and "Clackamas
Town Center" appear in both this layer and `park-and-rides`, with the suffix
differing ("Transit Center" versus "Park & Ride"). Matching on name needs
normalisation; matching spatially is more reliable."""),
],
recipes=[
("Transit centers by county", """\
SELECT county, count(*) AS centers, string_agg(name, '; ' ORDER BY name) AS names
FROM 'transit-centers/transit-centers.parquet'
GROUP BY county
ORDER BY centers DESC;"""),
("How much service each hub concentrates", """\
SELECT tc.name,
       count(DISTINCT rs.rte) AS routes,
       count(DISTINCT rs.stop_id) AS stops
FROM 'transit-centers/transit-centers.parquet' tc
JOIN 'route-stops/route-stops.parquet' rs
  ON ST_DWithin(tc.geometry, rs.geometry, 1312.34)
GROUP BY tc.name
ORDER BY routes DESC;"""),
("Which hubs have rail", """\
SELECT tc.name, string_agg(DISTINCT rst.type, ', ') AS rail_modes
FROM 'transit-centers/transit-centers.parquet' tc
LEFT JOIN 'rail-stops/rail-stops.parquet' rst
  ON ST_DWithin(tc.geometry, rst.geometry, 1312.34)
GROUP BY tc.name
ORDER BY rail_modes NULLS LAST;"""),
],
related=[("park-and-rides", "parking at many of the same facilities"),
         ("route-stops", "the routes that actually call at each hub")],
),

# ---------------------------------------------------------------------------
"park-and-rides": dict(
summary="""\
The 46 park and ride facilities in the TriMet system, with a parking-space count
for each — 12,501 spaces in total. 32 are TriMet-owned and hold 11,572 spaces
between them; the other 14 are shared-use arrangements with other property
owners and hold 929.

The largest is the 750-space Clackamas Town Center garage; the median lot is far
smaller, so capacity is heavily concentrated in a handful of facilities.""",
uses="""\
- Park-and-ride capacity analysis, which the `spaces` column supports directly.
- Locating the drive-to-transit entry points of the network.
- Pairing capacity with rail access — most of the large lots sit on MAX.""",
limitations="""\
- **`spaces` is nominal capacity, not availability.** Nothing here says whether a
  lot is full, and TriMet's own real-time occupancy is a separate service.
- **Shared-use lots are conditional.** The 14 `Shared` facilities are used under
  agreement with another owner; spaces may be restricted by time of day or
  removed if the agreement changes. Do not treat them as equivalent to
  TriMet-owned capacity.
- **The point is the facility, not the entrance.** For drive-access routing you
  need the actual driveway, which is not in this data.
- **No fees, no restrictions, no permit information.**""",
quirks=[
("Capacity is extremely skewed — use area, not radius, to draw it",
 """32 TriMet lots hold 11,572 spaces and 14 shared lots hold 929. A linear radius
encoding makes the small lots invisible; `styles/by-capacity.json` scales by
`sqrt(spaces)` so circle *area* tracks capacity."""),
("`owner` is the strongest predictor of size",
 """Mean TriMet-owned lot: ~362 spaces. Mean shared lot: ~66. If you are modelling
capacity, `owner` is worth carrying as a feature."""),
("Names overlap with transit centers",
 """Several facilities appear in both layers with different suffixes — see the
`transit-centers` guide. Join spatially rather than by name."""),
("All 46 are `Existing`",
 """`Planned` and `UC` are documented but unused here."""),
("`spaces` is never null in this snapshot",
 """Every one of the 46 rows has a positive space count, so you do not need to
handle nulls — but do not assume that holds in a future vintage."""),
],
recipes=[
("Capacity by ownership", """\
SELECT owner, count(*) AS lots, sum(spaces) AS spaces,
       round(avg(spaces)) AS mean_lot
FROM 'park-and-rides/park-and-rides.parquet'
GROUP BY owner;"""),
("The largest facilities", """\
SELECT name, city, county, owner, spaces
FROM 'park-and-rides/park-and-rides.parquet'
ORDER BY spaces DESC
LIMIT 10;"""),
("Park and ride capacity served by rail", """\
SELECT CASE WHEN r.station IS NULL THEN 'bus only' ELSE 'rail-served' END AS access,
       count(DISTINCT p.name) AS lots, sum(DISTINCT p.spaces) AS spaces
FROM 'park-and-rides/park-and-rides.parquet' p
LEFT JOIN 'rail-stops/rail-stops.parquet' r
  ON ST_DWithin(p.geometry, r.geometry, 1312.34)
GROUP BY 1;"""),
],
related=[("transit-centers", "many park and rides sit at a transit center"),
         ("rail-stops", "the large lots are mostly on MAX")],
),
}
