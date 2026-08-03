#!/usr/bin/env python3
"""Generate the MapLibre GL styles for every collection.

Design rule for this catalog: where TriMet publishes cartography for a layer,
reproduce it rather than invent something. Two TriMet sources are used.

1. The GeoServer SLD ``ott:rail`` (mirrored at ``sources/sld/current_rail.xml``).
   Its rules filter on exactly the ``line`` values the rail-lines and rail-stops
   layers carry, so it maps onto this data one-to-one. It draws shared trackage
   as a solid base stroke in the trunk line's color plus one dashed overlay per
   additional line, which is what ``styles/default.json`` for rail-lines does.

2. The MapLibre style ``tiles.trimet.org/styles/trimet-routes`` (mirrored at
   ``sources/trimet-routes-style.json``), which draws the whole network. Bus is
   a flat ``rgba(19, 99, 144, 1)``; MAX, streetcar and BRT read ``route_color``
   from GTFS. Since these Shapefiles carry no ``route_color``, the equivalent
   colors are taken from TriMet's GTFS ``routes.txt`` and keyed on ``type``.

Two deliberate approximations, both noted in each style's ``description``:

- SLD dash arrays are in pixels; MapLibre's are in multiples of line width. The
  generator divides by the low-zoom width, so dashes match TriMet's exactly
  below zoom 12 and run proportionally shorter above it.
- The SLD's scale break at denominator 151181 is rendered as zoom 12.

    python3 tools/make_styles.py [--check]
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import manifest as M  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "catalog"

# The SLD's MaxScaleDenominator, as a MapLibre zoom.
SCALE_BREAK_ZOOM = 12

WHITE = "#FFFFFF"
INK = "#1A1A1A"
HALO = "#FFFFFF"

# TriMet brand orange, sampled from the TriMet roundel in catalog/_assets.
TRIMET_ORANGE = "#D4451F"


def style(coll_id, name, description, layers, legend=None):
    """Wrap layers in a complete, self-contained MapLibre GL style.

    `legend` is a data-driven color expression describing what the style
    encodes. When given, it is emitted as an inert `fill` layer ahead of the
    visible ones.

    That indirection is not decoration. portolan-browser derives a legend by
    reading the first `fill` layer's `fill-color` — it does not look at
    `line-color` or `circle-color`, so a line or point style otherwise shows no
    legend at all, which is nearly every style in this catalog. A `fill` layer
    draws nothing on line or point geometry, and `fill-opacity` is 0 besides, so
    the layer is invisible on the map and exists only to be read. The same
    workaround is used in the portolan-nl catalog; see
    portolan-sdi/portolan-browser#13.

    Styles whose color carries no meaning — a single constant, or a heatmap
    ramp that has no per-feature expression — pass no legend, because inventing
    one would describe a classification that does not exist.
    """
    if legend is not None:
        layers = [{
            "id": f"{coll_id}-legend",
            "type": "fill",
            "source": "data",
            "source-layer": coll_id,
            "paint": {"fill-color": legend, "fill-opacity": 0},
        }] + layers
    return {
        "version": 8,
        "name": name,
        "metadata": {"description": description},
        "sources": {"data": {"type": "vector", "url": f"pmtiles://../{coll_id}.pmtiles"}},
        "layers": layers,
    }


def match(prop, mapping, fallback):
    """A MapLibre `match` expression from a dict, in insertion order."""
    expr = ["match", ["get", prop]]
    for k, v in mapping.items():
        expr += [k, v]
    expr.append(fallback)
    return expr


def zoom_scaled(factor, stops):
    """A zoom ramp with a data-driven multiplier applied at each stop.

    MapLibre only accepts `["zoom"]` as the direct input of a top-level `step` or
    `interpolate` — it may not appear nested inside another expression. So
    `["*", factor, ["interpolate", ..., ["zoom"], ...]]` is invalid style JSON and
    is rejected outright by both MapLibre GL JS and GL Native. Multiplying the
    factor into each output stop instead is mathematically identical and valid.

    `stops` is a flat [zoom, value, zoom, value, ...] list.
    """
    expr = ["interpolate", ["linear"], ["zoom"]]
    for i in range(0, len(stops), 2):
        expr += [stops[i], ["*", factor, stops[i + 1]]]
    return expr


def write(coll_id, filename, obj):
    d = OUT / coll_id / "styles"
    d.mkdir(parents=True, exist_ok=True)
    (d / filename).write_text(json.dumps(obj, indent=2) + "\n")


# ---------------------------------------------------------------------------
# Shared pieces
# ---------------------------------------------------------------------------

def label_layer(coll_id, prop, size=11, minzoom=11, color=INK, offset=None):
    layout = {
        "text-field": ["get", prop],
        "text-font": ["Noto Sans Regular"],
        "text-size": size,
        "text-anchor": "top" if offset else "center",
        "text-max-width": 9,
        "text-padding": 4,
    }
    if offset:
        layout["text-offset"] = offset
    return {
        "id": f"{coll_id}-labels",
        "type": "symbol",
        "source": "data",
        "source-layer": coll_id,
        "minzoom": minzoom,
        "layout": layout,
        "paint": {"text-color": color, "text-halo-color": HALO, "text-halo-width": 1.4},
    }


def stop_marker(coll_id, color, radius=None, stroke=1.6):
    """TriMet's SLD `ott:stops` draws a white circle with a dark 2px stroke at
    size 6. This is that mark, with the fill swapped when a style encodes a
    category in color."""
    return {
        "id": coll_id,
        "type": "circle",
        "source": "data",
        "source-layer": coll_id,
        "paint": {
            "circle-radius": radius or ["interpolate", ["linear"], ["zoom"], 9, 1.6, 13, 3.4, 16, 6],
            "circle-color": color,
            "circle-stroke-color": INK,
            "circle-stroke-width": stroke,
        },
    }


# ---------------------------------------------------------------------------
# district-boundary
# ---------------------------------------------------------------------------

def district_boundary():
    cid = "district-boundary"

    write(cid, "default.json", style(
        cid, "TriMet District Boundary",
        "The TriMet service district as a tinted fill with a TriMet-orange edge. "
        "The fill uses TriMet's own basemap water tint at low opacity so the "
        "district reads as an area without hiding a basemap underneath.",
        [
            {"id": cid, "type": "fill", "source": "data", "source-layer": cid,
             "paint": {"fill-color": TRIMET_ORANGE, "fill-opacity": 0.08}},
            {"id": f"{cid}-edge", "type": "line", "source": "data", "source-layer": cid,
             "layout": {"line-join": "round", "line-cap": "round"},
             "paint": {"line-color": TRIMET_ORANGE,
                       "line-width": ["interpolate", ["linear"], ["zoom"], 7, 1.2, 12, 3]}},
        ]))

    write(cid, "outline.json", style(
        cid, "TriMet District Boundary — outline only",
        "The district edge with no fill, for overlaying on top of other layers "
        "without tinting what is underneath.",
        [
            {"id": f"{cid}-edge", "type": "line", "source": "data", "source-layer": cid,
             "layout": {"line-join": "round", "line-cap": "round"},
             "paint": {"line-color": TRIMET_ORANGE,
                       "line-width": ["interpolate", ["linear"], ["zoom"], 7, 1.5, 12, 3.5],
                       "line-dasharray": [3, 2]}},
        ]))

    write(cid, "context.json", style(
        cid, "TriMet District Boundary — solid context",
        "A solid, opaque fill in TriMet's basemap building gray. Use this as a "
        "backdrop underneath the stop and route layers when no basemap is "
        "available, so the network has a visible service area behind it.",
        [
            {"id": cid, "type": "fill", "source": "data", "source-layer": cid,
             "paint": {"fill-color": M.BASEMAP["building"], "fill-opacity": 1,
                       "fill-outline-color": "#C8CCD0"}},
        ]))


# ---------------------------------------------------------------------------
# routes
# ---------------------------------------------------------------------------

def routes():
    cid = "routes"
    # From `trimet-routes`: bus is flat, MAX 3.5px at 0.8 opacity, streetcar
    # 1.5px, commuter rail 3px black. Scaled up here because this style is
    # drawn on its own rather than over a dense basemap.
    type_color = {
        "BUS": M.TYPE_COLORS["BUS"],
        "MAX": M.TYPE_COLORS["MAX"],
        "SC": M.TYPE_COLORS["SC"],
        "CR": M.TYPE_COLORS["CR"],
        "AT": M.TYPE_COLORS["AT"],
    }
    type_width = {"BUS": 1.0, "MAX": 3.5, "SC": 1.5, "CR": 3.0, "AT": 1.5}

    write(cid, "default.json", style(
        cid, "TriMet Routes by service type",
        "Every fixed-route alignment colored by TYPE, following TriMet's own "
        "`trimet-routes` MapLibre style: bus lines thin and blue, MAX heaviest, "
        "streetcar thin, commuter rail gray. Colors are TriMet's GTFS "
        "route_color values, which is what that style resolves at draw time.",
        [
            {"id": cid, "type": "line", "source": "data", "source-layer": cid,
             "layout": {"line-cap": "round", "line-join": "round"},
             "paint": {
                 "line-color": match("type", type_color, "#999999"),
                 "line-width": zoom_scaled(match("type", type_width, 1.0),
                                          [8, 0.6, 12, 1.0, 16, 1.8]),
                 "line-opacity": 0.9,
             }},
        ],
        legend=match("type", type_color, "#999999")))

    write(cid, "frequent-service.json", style(
        cid, "TriMet Routes — Frequent Service",
        "Splits the network on the FREQUENT flag. The 51 route-direction "
        "segments flagged True are drawn heavy in TriMet's FX green; the "
        "remaining 149 recede to a thin gray, so the frequent-service spine "
        "stands out against the rest of the system.",
        [
            {"id": f"{cid}-other", "type": "line", "source": "data", "source-layer": cid,
             "filter": ["!=", ["get", "frequent"], "True"],
             "layout": {"line-cap": "round", "line-join": "round"},
             "paint": {"line-color": "#B8C2CC",
                       "line-width": ["interpolate", ["linear"], ["zoom"], 8, 0.5, 14, 1.2]}},
            {"id": f"{cid}-frequent", "type": "line", "source": "data", "source-layer": cid,
             "filter": ["==", ["get", "frequent"], "True"],
             "layout": {"line-cap": "round", "line-join": "round"},
             "paint": {"line-color": M.GTFS_ROUTE_COLORS["FX2 Division"],
                       "line-width": ["interpolate", ["linear"], ["zoom"], 8, 1.4, 14, 3.6]}},
        ],
        # The visible layers are filtered rather than data-driven, so the
        # classification is restated here for the legend.
        legend=match("frequent", {"True": M.GTFS_ROUTE_COLORS["FX2 Division"],
                                  "False": "#B8C2CC"}, "#B8C2CC")))

    write(cid, "by-direction.json", style(
        cid, "TriMet Routes by direction",
        "Colors the two DIR values apart. Each route appears twice in this "
        "layer, once per direction, and the two alignments are rarely identical "
        "because of one-way streets — this style makes those divergences "
        "visible. Offsetting the two directions by a couple of pixels keeps "
        "coincident segments from hiding each other.",
        [
            {"id": f"{cid}-dir0", "type": "line", "source": "data", "source-layer": cid,
             "filter": ["==", ["get", "dir"], 0],
             "layout": {"line-cap": "round", "line-join": "round"},
             "paint": {"line-color": "#1359AE", "line-offset": 1.5,
                       "line-width": ["interpolate", ["linear"], ["zoom"], 8, 0.6, 14, 2]}},
            {"id": f"{cid}-dir1", "type": "line", "source": "data", "source-layer": cid,
             "filter": ["==", ["get", "dir"], 1],
             "layout": {"line-cap": "round", "line-join": "round"},
             "paint": {"line-color": "#D05F27", "line-offset": -1.5,
                       "line-width": ["interpolate", ["linear"], ["zoom"], 8, 0.6, 14, 2]}},
        ],
        legend=["match", ["get", "dir"], 0, "#1359AE", 1, "#D05F27", "#999999"]))

    write(cid, "labeled.json", style(
        cid, "TriMet Routes with route numbers",
        "The service-type styling with PUBLIC_RTE drawn along each alignment. "
        "Use PUBLIC_RTE rather than RTE for display: it is the number riders "
        "see, and it is where lettered services such as FX2 appear.",
        [
            {"id": cid, "type": "line", "source": "data", "source-layer": cid,
             "layout": {"line-cap": "round", "line-join": "round"},
             "paint": {
                 "line-color": match("type", type_color, "#999999"),
                 "line-width": zoom_scaled(match("type", type_width, 1.0),
                                          [8, 0.6, 12, 1.0, 16, 1.8]),
                 "line-opacity": 0.9,
             }},
            {"id": f"{cid}-labels", "type": "symbol", "source": "data", "source-layer": cid,
             "minzoom": 11,
             "layout": {"symbol-placement": "line", "text-field": ["get", "public_rte"],
                        "text-font": ["Noto Sans Regular"], "text-size": 11,
                        "symbol-spacing": 220, "text-rotation-alignment": "map"},
             "paint": {"text-color": INK, "text-halo-color": HALO, "text-halo-width": 1.6}},
        ],
        legend=match("type", type_color, "#999999")))


# ---------------------------------------------------------------------------
# rail-lines — the faithful SLD reproduction
# ---------------------------------------------------------------------------

def _rail_width_expr():
    """SLD widths: 2.0 below the scale break and 3.0 above it for MAX and
    commuter rail; the streetcar rules omit stroke-width below the break, which
    is an SLD default of 1.0, and set 2.0 above it."""
    return ["step", ["zoom"],
            ["match", ["get", "type"], "SC", 1.0, 2.0],
            SCALE_BREAK_ZOOM,
            ["match", ["get", "type"], "SC", 2.0, 3.0]]


def _base_width_px(line_value):
    """Low-zoom SLD stroke width for a `line` value, used to convert its dash
    array from pixels into MapLibre's multiples-of-line-width."""
    streetcar = {"AL", "BL", "NS", "NS/AL", "NS/BL", "NS/AL/BL", "AL/BL"}
    return 1.0 if line_value in streetcar else 2.0


def rail_lines():
    cid = "rail-lines"

    base_colors = dict(M.RAIL_BASE)
    base_colors["AUX"] = M.RAIL_AUX_COLOR

    layers = [{
        "id": f"{cid}-base",
        "type": "line", "source": "data", "source-layer": cid,
        "layout": {"line-join": "round", "line-cap": "butt"},
        "paint": {
            "line-color": match("line", base_colors, "#666666"),
            "line-width": _rail_width_expr(),
        },
    }]

    # Group the SLD's dashed overlays by (position, dash pattern, width class)
    # so each becomes one MapLibre layer. Position matters: overlay 1 is drawn
    # over overlay 0, exactly as the symbolizers stack inside an SLD rule.
    groups = {}
    for line_value, overlays in M.RAIL_OVERLAYS.items():
        w = _base_width_px(line_value)
        for idx, (color, dash_px) in enumerate(overlays):
            dash = tuple(round(d / w, 3) for d in dash_px)
            groups.setdefault((idx, dash, w), {})[line_value] = color

    for (idx, dash, w), members in sorted(groups.items(), key=lambda kv: (kv[0][0], kv[0][2])):
        tag = f"{idx}-{'x'.join(str(d) for d in dash)}".replace(".", "_")
        layers.append({
            "id": f"{cid}-overlay-{tag}",
            "type": "line", "source": "data", "source-layer": cid,
            "filter": ["in", ["get", "line"], ["literal", sorted(members)]],
            "layout": {"line-join": "round", "line-cap": "butt"},
            "paint": {
                "line-color": match("line", members, "#666666"),
                "line-width": _rail_width_expr(),
                "line-dasharray": list(dash),
            },
        })

    write(cid, "default.json", style(
        cid, "TriMet Rail Lines — TriMet cartography",
        "A direct reproduction of TriMet's published GeoServer style `ott:rail`, "
        "whose rules key on exactly the LINE values this layer carries. Each "
        "segment gets a solid base stroke in its trunk line's color, then one "
        "dashed overlay per additional line sharing the track — so the four-line "
        "trunk through downtown Portland reads as blue under red, green and "
        "yellow dashes, the way it does on TriMet's own maps. Widths step at "
        "zoom 12, standing in for the SLD's scale break at denominator 151181. "
        "Dash lengths are converted from SLD pixels into MapLibre line-widths "
        "using the low-zoom width, so they match exactly below zoom 12 and run "
        "proportionally shorter above it. AUX segments carry no SLD rule and are "
        "drawn neutral gray rather than dropped.",
        layers,
        legend=match("line", base_colors, "#666666")))

    write(cid, "by-type.json", style(
        cid, "TriMet Rail Lines by service type",
        "Collapses the twenty LINE values into the four TYPE values: light rail, "
        "streetcar, commuter rail, and the shared MAX/streetcar segment. Colors "
        "come from TriMet's GTFS route_color. Simpler than the default style and "
        "easier to read at metro-wide zooms.",
        [
            {"id": cid, "type": "line", "source": "data", "source-layer": cid,
             "layout": {"line-join": "round", "line-cap": "round"},
             "paint": {
                 "line-color": match("type", {
                     "MAX": M.TYPE_COLORS["MAX"], "SC": M.TYPE_COLORS["SC"],
                     "CR": M.TYPE_COLORS["CR"], "MAX/SC": M.TYPE_COLORS["MAX/SC"],
                 }, "#999999"),
                 "line-width": ["interpolate", ["linear"], ["zoom"], 8, 1.2, 14, 4],
             }},
        ],
        legend=match("type", {
            "MAX": M.TYPE_COLORS["MAX"], "SC": M.TYPE_COLORS["SC"],
            "CR": M.TYPE_COLORS["CR"], "MAX/SC": M.TYPE_COLORS["MAX/SC"],
        }, "#999999")))

    write(cid, "by-passage.json", style(
        cid, "TriMet Rail Lines by passage",
        "Encodes the PASSAGE attribute — whether a segment runs at surface "
        "level, over a bridge, or through a tunnel. Bridges are drawn heavy and "
        "dark, tunnels dashed, surface track light. TriMet notes that PASSAGE is "
        "intended for cartographic display rather than analysis, so read this as "
        "a drawing hint and not an infrastructure inventory.",
        [
            {"id": f"{cid}-surface", "type": "line", "source": "data", "source-layer": cid,
             "filter": ["==", ["get", "passage"], "surface"],
             "layout": {"line-join": "round", "line-cap": "round"},
             "paint": {"line-color": "#8A94A0",
                       "line-width": ["interpolate", ["linear"], ["zoom"], 8, 1, 14, 3]}},
            {"id": f"{cid}-tunnel", "type": "line", "source": "data", "source-layer": cid,
             "filter": ["==", ["get", "passage"], "tunnel"],
             "layout": {"line-join": "round", "line-cap": "butt"},
             "paint": {"line-color": "#5B4B8A", "line-dasharray": [2, 1.5],
                       "line-width": ["interpolate", ["linear"], ["zoom"], 8, 1.4, 14, 4]}},
            {"id": f"{cid}-bridge", "type": "line", "source": "data", "source-layer": cid,
             "filter": ["==", ["get", "passage"], "bridge"],
             "layout": {"line-join": "round", "line-cap": "butt"},
             "paint": {"line-color": "#14304F",
                       "line-width": ["interpolate", ["linear"], ["zoom"], 8, 2, 14, 5.5]}},
        ],
        legend=match("passage", {"surface": "#8A94A0", "tunnel": "#5B4B8A",
                                 "bridge": "#14304F"}, "#8A94A0")))

    write(cid, "labeled.json", style(
        cid, "TriMet Rail Lines with line codes",
        "TriMet's rail cartography with the LINE code drawn along each segment. "
        "Because a code such as BGR means three lines share that track, the "
        "labels are the fastest way to read which services run where.",
        layers + [{
            "id": f"{cid}-labels", "type": "symbol", "source": "data", "source-layer": cid,
            "minzoom": 11,
            "layout": {"symbol-placement": "line", "text-field": ["get", "line"],
                       "text-font": ["Noto Sans Regular"], "text-size": 11,
                       "symbol-spacing": 200, "text-rotation-alignment": "map"},
            "paint": {"text-color": INK, "text-halo-color": HALO, "text-halo-width": 1.6},
        }],
        legend=match("line", base_colors, "#666666")))


# ---------------------------------------------------------------------------
# stops / route-stops / rail-stops
# ---------------------------------------------------------------------------

def stops():
    cid = "stops"

    write(cid, "default.json", style(
        cid, "TriMet Stops",
        "TriMet's own stop symbol, taken from the GeoServer style `ott:stops`: a "
        "white circle with a dark stroke. Radius grows with zoom so all 6,316 "
        "stops stay separable in dense corridors.",
        [stop_marker(cid, WHITE)]))

    write(cid, "by-type.json", style(
        cid, "TriMet Stops by service type",
        "The same mark filled by TYPE, so the 6,075 bus stops read apart from "
        "the 161 MAX platforms, 58 streetcar stops, 14 shared bus/streetcar "
        "stops, 6 WES platforms and 2 aerial tram terminals. Colors are TriMet's "
        "GTFS route_color values for each mode.",
        [stop_marker(cid, match("type", M.TYPE_COLORS, "#CCCCCC"))],
        legend=match("type", M.TYPE_COLORS, "#CCCCCC")))

    write(cid, "density.json", style(
        cid, "TriMet Stops — density",
        "A heatmap of stop density that fades into individual marks past zoom "
        "13. Useful for seeing where the network is dense without drawing "
        "thousands of overlapping circles at metro-wide zooms.",
        [
            {"id": f"{cid}-heat", "type": "heatmap", "source": "data", "source-layer": cid,
             "maxzoom": 14,
             "paint": {
                 "heatmap-weight": 1,
                 "heatmap-intensity": ["interpolate", ["linear"], ["zoom"], 8, 0.6, 14, 2],
                 "heatmap-radius": ["interpolate", ["linear"], ["zoom"], 8, 10, 14, 26],
                 "heatmap-opacity": ["interpolate", ["linear"], ["zoom"], 12, 0.9, 14, 0],
                 "heatmap-color": ["interpolate", ["linear"], ["heatmap-density"],
                                   0, "rgba(255,255,255,0)", 0.2, "#D5EEF8",
                                   0.4, "#7FB6D9", 0.6, "#4679AA",
                                   0.8, "#D4451F", 1, "#8C2A10"],
             }},
            {"id": cid, "type": "circle", "source": "data", "source-layer": cid,
             "minzoom": 13,
             "paint": {"circle-radius": ["interpolate", ["linear"], ["zoom"], 13, 2, 16, 5],
                       "circle-color": WHITE, "circle-stroke-color": INK,
                       "circle-stroke-width": 1.4,
                       "circle-opacity": ["interpolate", ["linear"], ["zoom"], 13, 0, 14, 1],
                       "circle-stroke-opacity": ["interpolate", ["linear"], ["zoom"], 13, 0, 14, 1]}},
        ]))

    write(cid, "labeled.json", style(
        cid, "TriMet Stops with names",
        "Stops colored by mode with STOP_NAME shown from zoom 14. Stop names are "
        "intersections or street addresses, so they read as cross-streets rather "
        "than as station names.",
        [stop_marker(cid, match("type", M.TYPE_COLORS, "#CCCCCC")),
         label_layer(cid, "stop_name", size=10, minzoom=14, offset=[0, 0.8])],
        legend=match("type", M.TYPE_COLORS, "#CCCCCC")))


def route_stops():
    cid = "route-stops"

    write(cid, "default.json", style(
        cid, "TriMet Route Stops by service type",
        "One mark per stop per route-direction, colored by TYPE. Because a stop "
        "served by several routes appears several times, marks are drawn "
        "semi-transparent — the busiest transfer points show up as the darkest "
        "spots on the map.",
        [{
            "id": cid, "type": "circle", "source": "data", "source-layer": cid,
            "paint": {
                "circle-radius": ["interpolate", ["linear"], ["zoom"], 9, 1.4, 13, 3, 16, 5.5],
                "circle-color": match("type", M.TYPE_COLORS, "#CCCCCC"),
                "circle-opacity": 0.55,
                "circle-stroke-color": INK,
                "circle-stroke-width": 0.6,
                "circle-stroke-opacity": 0.5,
            },
        }],
        legend=match("type", M.TYPE_COLORS, "#CCCCCC")))

    write(cid, "frequent-service.json", style(
        cid, "TriMet Route Stops — Frequent Service",
        "Stops on route-directions flagged FREQUENT, drawn over the rest. This "
        "is the stop-level companion to the routes Frequent Service style, and "
        "it answers a question the routes layer cannot: which stops a rider can "
        "use without consulting a timetable.",
        [
            {"id": f"{cid}-other", "type": "circle", "source": "data", "source-layer": cid,
             "filter": ["!=", ["get", "frequent"], "True"],
             "paint": {"circle-radius": ["interpolate", ["linear"], ["zoom"], 9, 1.2, 15, 3],
                       "circle-color": "#C3CBD3", "circle-opacity": 0.7}},
            {"id": f"{cid}-frequent", "type": "circle", "source": "data", "source-layer": cid,
             "filter": ["==", ["get", "frequent"], "True"],
             "paint": {"circle-radius": ["interpolate", ["linear"], ["zoom"], 9, 1.8, 15, 4.5],
                       "circle-color": M.GTFS_ROUTE_COLORS["FX2 Division"],
                       "circle-stroke-color": WHITE, "circle-stroke-width": 0.8}},
        ],
        legend=match("frequent", {"True": M.GTFS_ROUTE_COLORS["FX2 Division"],
                                  "False": "#C3CBD3"}, "#C3CBD3")))

    write(cid, "by-direction.json", style(
        cid, "TriMet Route Stops by direction",
        "Splits stops on DIR. Along a two-way corridor the inbound and outbound "
        "stops sit on opposite sides of the street, so this style shows the "
        "paired-stop structure of the network directly.",
        [{
            "id": cid, "type": "circle", "source": "data", "source-layer": cid,
            "paint": {
                "circle-radius": ["interpolate", ["linear"], ["zoom"], 9, 1.4, 15, 4],
                "circle-color": ["match", ["get", "dir"], 0, "#1359AE", 1, "#D05F27", "#999999"],
                "circle-opacity": 0.8,
                "circle-stroke-color": WHITE,
                "circle-stroke-width": 0.6,
            },
        }],
        legend=["match", ["get", "dir"], 0, "#1359AE", 1, "#D05F27", "#999999"]))

    write(cid, "by-sequence.json", style(
        cid, "TriMet Route Stops by stop sequence",
        "Ramps color across STOP_SEQ, the position of a stop along its "
        "route-direction. Following the ramp traces the direction of travel, and "
        "the gradient makes route ends easy to pick out. Sequence numbers "
        "restart at every route-direction, so the ramp is only meaningful when "
        "the view is filtered to one route.",
        [{
            "id": cid, "type": "circle", "source": "data", "source-layer": cid,
            "paint": {
                "circle-radius": ["interpolate", ["linear"], ["zoom"], 9, 1.4, 15, 4],
                "circle-color": ["interpolate", ["linear"], ["get", "stop_seq"],
                                 1, "#FFC52F", 20, "#D05F27", 45, "#C41F3E", 80, "#5B2A86"],
                "circle-opacity": 0.85,
            },
        }],
        legend=["interpolate", ["linear"], ["get", "stop_seq"],
                1, "#FFC52F", 20, "#D05F27", 45, "#C41F3E", 80, "#5B2A86"]))


def rail_stops():
    cid = "rail-stops"
    line_colors = dict(M.RAIL_BASE)

    write(cid, "default.json", style(
        cid, "TriMet Rail Stops by line",
        "Station marks filled with the color of the line that serves them, using "
        "the same palette as TriMet's `ott:rail` style so this layer sits "
        "correctly on top of the rail-lines default style. Stations on shared "
        "track take the trunk line's color; the LINE code itself records the full "
        "set of services.",
        [stop_marker(cid, match("line", line_colors, "#666666"),
                     radius=["interpolate", ["linear"], ["zoom"], 8, 2.5, 12, 4.5, 16, 8],
                     stroke=1.8)],
        legend=match("line", line_colors, "#666666")))

    write(cid, "labeled.json", style(
        cid, "TriMet Rail Stops with station names",
        "Line-colored station marks with STATION names. Unlike the bus stop "
        "names, these are real station names, which makes this the most useful "
        "style for orienting a reader on the rail network.",
        [stop_marker(cid, match("line", line_colors, "#666666"),
                     radius=["interpolate", ["linear"], ["zoom"], 8, 2.5, 12, 4.5, 16, 8],
                     stroke=1.8),
         label_layer(cid, "station", size=11, minzoom=11, offset=[0, 0.9])],
        legend=match("line", line_colors, "#666666")))

    write(cid, "by-type.json", style(
        cid, "TriMet Rail Stops by service type",
        "Three marks instead of eighteen: light rail, streetcar and commuter "
        "rail. MAX platforms are drawn largest and WES smallest, matching the "
        "relative prominence TriMet gives each mode in its own line styling.",
        [{
            "id": cid, "type": "circle", "source": "data", "source-layer": cid,
            "paint": {
                "circle-radius": zoom_scaled(
                    ["match", ["get", "type"], "MAX", 1.0, "SC", 0.7, "CR", 0.85, 0.8],
                    [8, 3, 12, 5.5, 16, 9]),
                "circle-color": match("type", {
                    "MAX": M.TYPE_COLORS["MAX"], "SC": M.TYPE_COLORS["SC"],
                    "CR": M.TYPE_COLORS["CR"],
                }, "#999999"),
                "circle-stroke-color": WHITE,
                "circle-stroke-width": 1.6,
            },
        }],
        legend=match("type", {
            "MAX": M.TYPE_COLORS["MAX"], "SC": M.TYPE_COLORS["SC"],
            "CR": M.TYPE_COLORS["CR"],
        }, "#999999")))


# ---------------------------------------------------------------------------
# transit-centers / park-and-rides
# ---------------------------------------------------------------------------

def transit_centers():
    cid = "transit-centers"

    write(cid, "default.json", style(
        cid, "TriMet Transit Centers",
        "The fifteen transit centers as prominent marks in TriMet brand orange. "
        "These are the network's timed-transfer hubs, so they are drawn larger "
        "than ordinary stops and stay visible at low zoom.",
        [stop_marker(cid, TRIMET_ORANGE,
                     radius=["interpolate", ["linear"], ["zoom"], 8, 4, 12, 7, 16, 12],
                     stroke=2)]))

    write(cid, "labeled.json", style(
        cid, "TriMet Transit Centers with names",
        "Transit center marks with NAME shown from zoom 9. Fifteen labels never "
        "collide, so this style works as a standalone overview of the network's "
        "hub structure.",
        [stop_marker(cid, TRIMET_ORANGE,
                     radius=["interpolate", ["linear"], ["zoom"], 8, 4, 12, 7, 16, 12],
                     stroke=2),
         label_layer(cid, "name", size=12, minzoom=9, offset=[0, 1.1])]))

    write(cid, "by-county.json", style(
        cid, "TriMet Transit Centers by county",
        "Colors the hubs by COUNTY. TriMet's district spans Multnomah, "
        "Washington and Clackamas counties, and this style shows how the "
        "transfer hubs are distributed across the three.",
        [stop_marker(cid, match("county", {
            "Multnomah": "#1359AE", "Washington": "#008342", "Clackamas": "#D05F27",
        }, "#999999"),
            radius=["interpolate", ["linear"], ["zoom"], 8, 4, 12, 7, 16, 12],
            stroke=2)],
        legend=match("county", {
            "Multnomah": "#1359AE", "Washington": "#008342", "Clackamas": "#D05F27",
        }, "#999999")))


def park_and_rides():
    cid = "park-and-rides"

    write(cid, "default.json", style(
        cid, "TriMet Park and Rides",
        "The 46 park and ride facilities in TriMet blue. A steady mark size "
        "makes this the right style when the question is where the lots are "
        "rather than how big they are.",
        [stop_marker(cid, M.TYPE_COLORS["MAX"],
                     radius=["interpolate", ["linear"], ["zoom"], 8, 3.5, 12, 6, 16, 10],
                     stroke=1.8)]))

    write(cid, "by-capacity.json", style(
        cid, "TriMet Park and Rides by capacity",
        "Scales each mark by SPACES and ramps its color with it, over a range "
        "that runs from small lots up to the 750-space Clackamas Town Center "
        "garage. Area, not radius, tracks capacity, so a lot that looks twice as "
        "big holds roughly twice as many cars. The whole system holds 12,501 "
        "spaces.",
        [{
            "id": cid, "type": "circle", "source": "data", "source-layer": cid,
            "paint": {
                "circle-radius": zoom_scaled(["sqrt", ["max", ["get", "spaces"], 1]],
                                             [8, 0.11, 12, 0.22, 16, 0.4]),
                "circle-color": ["interpolate", ["linear"], ["get", "spaces"],
                                 0, "#D5EEF8", 150, "#7FB6D9", 350, "#4679AA",
                                 550, "#D4451F", 750, "#8C2A10"],
                "circle-opacity": 0.8,
                "circle-stroke-color": WHITE,
                "circle-stroke-width": 1,
            },
        }],
        legend=["interpolate", ["linear"], ["get", "spaces"],
                0, "#D5EEF8", 150, "#7FB6D9", 350, "#4679AA",
                550, "#D4451F", 750, "#8C2A10"]))

    write(cid, "by-owner.json", style(
        cid, "TriMet Park and Rides by ownership",
        "Separates the 32 TriMet-owned lots from the 14 shared-use facilities. "
        "The distinction matters in practice: shared lots are much smaller, "
        "929 spaces between them against 11,572 in the TriMet-owned lots, and "
        "their availability depends on an agreement with the property owner.",
        [stop_marker(cid, match("owner", {"TriMet": "#1359AE", "Shared": "#D05F27"}, "#999999"),
                     radius=["interpolate", ["linear"], ["zoom"], 8, 3.5, 12, 6, 16, 10],
                     stroke=1.8)],
        legend=match("owner", {"TriMet": "#1359AE", "Shared": "#D05F27"}, "#999999")))

    write(cid, "labeled.json", style(
        cid, "TriMet Park and Rides with names and capacity",
        "Capacity-scaled marks labeled with the facility name and its space "
        "count, so a reader can identify a specific lot without clicking it.",
        [
            {"id": cid, "type": "circle", "source": "data", "source-layer": cid,
             "paint": {
                 "circle-radius": zoom_scaled(["sqrt", ["max", ["get", "spaces"], 1]],
                                              [8, 0.11, 12, 0.22, 16, 0.4]),
                 "circle-color": ["interpolate", ["linear"], ["get", "spaces"],
                                  0, "#D5EEF8", 150, "#7FB6D9", 350, "#4679AA",
                                  550, "#D4451F", 750, "#8C2A10"],
                 "circle-opacity": 0.8, "circle-stroke-color": WHITE, "circle-stroke-width": 1}},
            {"id": f"{cid}-labels", "type": "symbol", "source": "data", "source-layer": cid,
             "minzoom": 10,
             "layout": {"text-field": ["concat", ["get", "name"], "\n",
                                       ["to-string", ["get", "spaces"]], " spaces"],
                        "text-font": ["Noto Sans Regular"], "text-size": 10,
                        "text-anchor": "top", "text-offset": [0, 1], "text-max-width": 10},
             "paint": {"text-color": INK, "text-halo-color": HALO, "text-halo-width": 1.4}},
        ],
        legend=["interpolate", ["linear"], ["get", "spaces"],
                0, "#D5EEF8", 150, "#7FB6D9", 350, "#4679AA",
                550, "#D4451F", 750, "#8C2A10"]))


BUILDERS = [district_boundary, routes, rail_lines, stops, route_stops,
            rail_stops, transit_centers, park_and_rides]


def main():
    for b in BUILDERS:
        b()
    total = 0
    for c in M.COLLECTIONS:
        # Mirrored TriMet source styles live here too; count only ours.
        n = len([p for p in (OUT / c["id"] / "styles").glob("*.json")
                 if not p.name.startswith("trimet-")])
        total += n
        print(f"  {c['id']:<20} {n} styles")
    print(f"  {'TOTAL':<20} {total} styles")


if __name__ == "__main__":
    main()
