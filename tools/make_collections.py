#!/usr/bin/env python3
"""Generate collection.json for every collection and the root catalog.json.

Everything descriptive comes from tools/manifest.py; everything measured (file
sizes, checksums, row counts, column types) is read off the files themselves at
generation time, so the metadata cannot drift from the bytes it describes.

    python3 tools/make_collections.py
"""
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import manifest as M  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "catalog"

# Size and checksum of TriMet's own Shapefile and KML downloads, recorded by
# tools/fetch.py. Kept in a committed sidecar because the assets themselves are
# remote and the binaries are not in this repo. They describe what TriMet served
# at the sync time in `updated`; if TriMet reissues a layer they will go stale,
# which is exactly what a consumer comparing them would want to detect.
SOURCE_SUMS = json.loads((ROOT / "sources" / "source_checksums.json").read_text())

STAC_VERSION = "1.1.0"
EXT = {
    "portolan": M.PORTOLAN_SCHEMA,
    "file": "https://stac-extensions.github.io/file/v2.1.0/schema.json",
    "table": "https://stac-extensions.github.io/table/v1.2.0/schema.json",
    "projection": "https://stac-extensions.github.io/projection/v2.0.0/schema.json",
    "web_map_links": "https://stac-extensions.github.io/web-map-links/v1.3.0/schema.json",
    "alternate": "https://stac-extensions.github.io/alternate-assets/v1.2.0/schema.json",
}

MEDIA = {
    ".parquet": "application/vnd.apache.parquet",
    ".pmtiles": "application/vnd.pmtiles",
    ".png": "image/png",
    ".webp": "image/webp",
    ".json": "application/vnd.mapbox.style+json",
    ".xml": "application/vnd.ogc.sld+xml",
}


def multihash_sha256(path):
    """STAC file:checksum, multihash-encoded: 0x12 sha2-256, 0x20 length."""
    h = hashlib.sha256(path.read_bytes()).hexdigest()
    return "1220" + h


def file_meta(path):
    return {"file:size": path.stat().st_size, "file:checksum": multihash_sha256(path)}


def parquet_schema(path):
    """Read the real column names and Arrow types out of the file."""
    import pyarrow.parquet as pq
    schema = pq.read_schema(path)
    return [(n, str(schema.field(n).type)) for n in schema.names]


def parquet_rows(path):
    import pyarrow.parquet as pq
    return pq.ParquetFile(path).metadata.num_rows


def table_columns(coll, path):
    """Merge measured types with the descriptions mined from TriMet's metadata
    pages. Columns present in the file but undocumented upstream still appear,
    with a description saying where the meaning comes from."""
    described = {c["name"]: c for c in coll["columns"]}
    cols = []
    for name, arrow_type in parquet_schema(path):
        entry = {"name": name, "type": arrow_type}
        if name in described:
            d = described[name]
            desc = d["description"]
            if "values" in d:
                codes = "; ".join(f"{k} = {v.rstrip('.')}" for k, v in d["values"].items())
                desc = f"{desc} Values: {codes}."
            if "note" in d:
                desc = f"{desc} {d['note']}"
            entry["description"] = desc
        elif name == "geometry":
            entry["description"] = (
                f"Feature geometry in TriMet's native {M.SOURCE_CRS} "
                f"({M.SOURCE_CRS_NAME}). Coordinates are feet, not degrees."
            )
        elif name.endswith("_bbox"):
            entry["description"] = ("Per-feature bounding box struct, the GeoParquet "
                                    "covering column. Same projected feet as the geometry.")
        cols.append(entry)
    return cols


def links_for(coll):
    """Structural links plus the TriMet provenance this catalog exists to carry."""
    src = M.source_links(coll)
    return [
        {"rel": "root", "href": "../catalog.json", "type": "application/json",
         "title": M.CATALOG_TITLE},
        {"rel": "parent", "href": "../catalog.json", "type": "application/json",
         "title": M.CATALOG_TITLE},
        {"rel": "describedby", "href": "./README.md", "type": "text/markdown",
         "title": f"{coll['title']} README"},
        {"rel": "agents", "href": "./AGENTS.md", "type": "text/markdown",
         "title": f"{coll['title']} agent guide"},
        {"rel": "license", "href": M.TERMS_URL, "type": "text/html",
         "title": "TriMet Terms of Use"},
        # `via` is required: TriMet produced this data, this catalog only hosts
        # a cloud-native copy of it.
        {"rel": "via", "href": src["metadata"], "type": "text/html",
         "title": f"TriMet metadata for {coll['source']}"},
        {"rel": "via", "href": M.GIS_PAGE, "type": "text/html",
         "title": "TriMet Geospatial Data"},
        # TriMet's mark, shown by browsers next to the collection. Section 6 of
        # TriMet's terms permits a TriMet web logo used to link to trimet.org.
        {"rel": "icon", "href": "../_assets/trimet-logo.png", "type": "image/png",
         "title": "TriMet"},
        {"rel": "pmtiles", "href": f"./{coll['id']}.pmtiles",
         "type": "application/vnd.pmtiles",
         "title": f"{coll['title']} vector tiles",
         "pmtiles:layers": [coll["id"]]},
    ]


def assets_for(coll):
    cdir = OUT / coll["id"]
    parquet = cdir / f"{coll['id']}.parquet"
    pmtiles = cdir / f"{coll['id']}.pmtiles"
    thumb = cdir / "thumbnail.webp"
    src = M.source_links(coll)

    assets = {}

    assets["data"] = {
        "href": f"./{coll['id']}.parquet",
        "type": MEDIA[".parquet"],
        "title": f"{coll['title']} (GeoParquet)",
        "description": (
            f"{coll['description']} In TriMet's native {M.SOURCE_CRS} "
            f"({M.SOURCE_CRS_NAME}), not reprojected, so lengths and areas are "
            f"in feet. Hilbert-ordered, zstd-compressed, with a GeoParquet 1.1 "
            f"bbox covering column for row-group pruning."
        ),
        "roles": ["data"],
        **file_meta(parquet),
        "table:columns": table_columns(coll, parquet),
        "table:primary_geometry": "geometry",
        "table:row_count": parquet_rows(parquet),
        "proj:code": M.SOURCE_CRS,
        # The same object over the bucket-native scheme, for readers that
        # prefer direct S3 access to https.
        "alternate": {
            "s3": {"href": f"{M.S3_BASE}/{coll['id']}/{coll['id']}.parquet",
                   "title": "S3 URI"},
        },
    }

    assets["visual"] = {
        "href": f"./{coll['id']}.pmtiles",
        "type": MEDIA[".pmtiles"],
        "title": f"{coll['title']} (PMTiles)",
        "description": (
            f"Vector tiles for web display, layer name `{coll['id']}`, "
            f"reprojected to WGS84 as tiles require. Built with tippecanoe "
            f"keeping every feature at every zoom, so what a map draws matches "
            f"the GeoParquet exactly."
        ),
        # Both roles apply. `visual` is the rendering derivative Portolan asks
        # for; `data` is also true — the PMTiles is a genuine distribution of
        # these features, not just a picture of them — and it is the role
        # clients key on when listing which formats a collection is available
        # in. Without it, STAC Browser's format badges advertise the legacy
        # Shapefile and KML but omit the cloud-native tiles.
        "roles": ["visual", "data"],
        **file_meta(pmtiles),
        "alternate": {
            "s3": {"href": f"{M.S3_BASE}/{coll['id']}/{coll['id']}.pmtiles",
                   "title": "S3 URI"},
        },
    }

    if thumb.exists():
        assets["thumbnail"] = {
            "href": "./thumbnail.webp",
            "type": MEDIA[".webp"],
            "title": f"{coll['title']} preview",
            "description": (
                "Rendered from this collection's styles/default.json with "
                "MapLibre GL Native, over a light basemap. WebP is allowed for "
                "thumbnails by spec PR portolan-sdi/portolan-spec#121, which "
                "this catalog targets; Portolan 0.1 alone permits only PNG and "
                "JPEG."
            ),
            "roles": ["thumbnail"],
            **file_meta(thumb),
        }

    # Styles, default first as the spec asks.
    sdir = cdir / "styles"
    if sdir.is_dir():
        # Mirrored TriMet source styles are registered separately below, so keep
        # them out of the generated-style list.
        source_files = {f for _, f, _, _ in SOURCE_STYLES.get(coll["id"], [])}
        names = sorted(p.name for p in sdir.glob("*.json") if p.name not in source_files)
        names.sort(key=lambda n: (n != "default.json", n))
        for name in names:
            p = sdir / name
            meta = json.loads(p.read_text())
            key = "style" if name == "default.json" else f"style-{p.stem}"
            assets[key] = {
                "href": f"./styles/{name}",
                "type": MEDIA[".json"],
                "title": meta.get("name", name),
                "description": meta.get("metadata", {}).get("description", ""),
                "roles": ["style"],
                **file_meta(p),
            }

    # The original TriMet artifacts. These are alternates to the cloud-native
    # primaries above, per the primary-vs-alternate rule.
    sums = SOURCE_SUMS[coll["source"]]
    assets["source_shapefile"] = {
        "href": src["shapefile"],
        "type": "application/zip",
        "title": f"{coll['title']} — original TriMet Shapefile",
        "description": (
            f"TriMet's own distribution of `{coll['source']}`, in "
            f"{M.SOURCE_CRS_NAME}. This is the file this collection was built "
            f"from. Size and checksum are of what TriMet served at the sync time "
            f"recorded in `updated`."
        ),
        "roles": ["data", "source"],
        "file:size": sums["shapefile"]["size"],
        "file:checksum": sums["shapefile"]["checksum"],
    }
    assets["source_kml"] = {
        "href": src["kml"],
        "type": "application/vnd.google-earth.kml+xml",
        "title": f"{coll['title']} — original TriMet KML",
        "description": "TriMet's KML distribution of the same layer.",
        "roles": ["data", "source"],
        "file:size": sums["kml"]["size"],
        "file:checksum": sums["kml"]["checksum"],
    }
    # TriMet's metadata page is carried as a rel:via link rather than an asset:
    # it describes the data, it is not the data, and its bytes change whenever
    # TriMet edits the page.

    # Where TriMet publishes cartography for this layer, mirror the source
    # style file so the styles here can be checked against their origin.
    for key, filename, title, desc in SOURCE_STYLES.get(coll["id"], []):
        p = cdir / "styles" / filename
        if not p.exists():
            continue
        assets[key] = {
            "href": f"./styles/{filename}",
            "type": MEDIA[p.suffix],
            "title": title,
            "description": desc,
            # `style` is reserved for MapLibre style files, so the SLD mirrors
            # carry `metadata` instead; the MapLibre one keeps `style`.
            "roles": ["style", "source"] if p.suffix == ".json" else ["metadata"],
            **file_meta(p),
        }

    return assets


_SLD_RAIL = (
    "source_sld", "trimet-rail.sld.xml",
    "TriMet GeoServer style ott:rail (SLD)",
    "TriMet's own published cartography for its rail layer, fetched from "
    "ws.trimet.org via WMS GetStyles. Its rules filter on exactly the LINE "
    "values this data carries, and styles/default.json is a direct "
    "reproduction of it.",
)
_SLD_STOPS = (
    "source_sld", "trimet-stops.sld.xml",
    "TriMet GeoServer style ott:stops (SLD)",
    "TriMet's own stop symbology: a white circle with a dark 2px stroke at "
    "size 6, which styles/default.json reproduces.",
)
_STYLE_ROUTES = (
    "source_style", "trimet-routes.style.json",
    "TriMet MapLibre style trimet-routes",
    "TriMet's published MapLibre style for the whole network, from "
    "tiles.trimet.org. Its line widths, caps and colors are what "
    "styles/default.json follows.",
)

# Where TriMet publishes cartography for a layer, its source style file is
# mirrored into the collection so the generated styles can be checked against
# their origin.
SOURCE_STYLES = {
    "rail-lines": [_SLD_RAIL],
    "rail-stops": [_SLD_RAIL],
    "stops": [_SLD_STOPS],
    "route-stops": [_SLD_STOPS],
    "routes": [_STYLE_ROUTES],
}


def providers():
    return [
        {
            "name": "TriMet",
            "description": (
                "Tri-County Metropolitan Transportation District of Oregon, the "
                "transit agency for the Portland metropolitan area and the "
                "originator of this data."
            ),
            "roles": ["producer", "licensor"],
            "url": M.GIS_PAGE,
            "email": M.TRIMET_CONTACT["email"],
        },
        {
            "name": M.HOST["name"],
            "description": (
                "Maintains this cloud-native mirror. Not affiliated with TriMet."
            ),
            "roles": ["host"],
            "url": "https://github.com/cholmes/portolan-catalog-trimet",
            "email": M.HOST["email"],
        },
    ]


def collection_json(coll):
    return {
        "type": "Collection",
        "stac_version": STAC_VERSION,
        "stac_extensions": [EXT["portolan"], EXT["file"], EXT["table"],
                            EXT["projection"], EXT["web_map_links"], EXT["alternate"]],
        "id": coll["id"],
        "title": coll["title"],
        "description": description_for(coll),
        "license": M.LICENSE,
        "keywords": ["transit", "public transport", "TriMet", "Portland",
                     "Oregon", coll["geometry"].lower()],
        "providers": providers(),
        "extent": {
            "spatial": {"bbox": [coll["bbox"]]},
            "temporal": {"interval": [[f"{coll['source_updated']}T00:00:00Z", None]]},
        },
        # A mirror records when it last synced from its source.
        "updated": SYNCED,
        # Also at the collection level, not only on the data asset: STAC
        # Browser and similar clients render a collection's schema from here,
        # and an agent reading collection.json alone then sees the fields.
        "table:columns": table_columns(coll, OUT / coll["id"] / f"{coll['id']}.parquet"),
        "table:primary_geometry": "geometry",
        "table:row_count": parquet_rows(OUT / coll["id"] / f"{coll['id']}.parquet"),
        "links": links_for(coll),
        "assets": assets_for(coll),
    }


def description_for(coll):
    """The STAC description and the README opening are two views of the same
    facts, so both are generated from this.

    STAC Browser renders this as Markdown, so every reference is a real link
    rather than a bare URL a reader has to copy."""
    src = M.source_links(coll)
    n = f"{coll['count']:,}"
    return (
        f"{coll['description']} {n} {coll['geometry']} feature"
        f"{'' if coll['count'] == 1 else 's'} covering "
        f"[TriMet]({M.GIS_PAGE})'s service district in the Portland, Oregon "
        f"metropolitan area, published by TriMet as "
        f"[`{coll['source']}`]({src['shapefile']}) and last updated at the "
        f"source on {coll['source_updated_text']}.\n\n"
        f"This is a cloud-native mirror: the same data as GeoParquet and "
        f"PMTiles. The GeoParquet keeps TriMet's native {M.SOURCE_CRS} "
        f"({M.SOURCE_CRS_NAME}), so lengths and areas are in feet; only the "
        f"PMTiles are reprojected to WGS84. The original "
        f"[Shapefile]({src['shapefile']}), [KML]({src['kml']}) and "
        f"[metadata page]({src['metadata']}) are linked as assets, and column "
        f"descriptions and code lists are TriMet's own, taken from that page.\n\n"
        f"The [collection README]({M.BROWSE_BASE}/{coll['id']}/README.md) covers "
        f"suggested uses, limitations and the full schema.\n\n"
        f"**Agents:** [`AGENTS.md`]({M.BROWSE_BASE}/{coll['id']}/AGENTS.md) is "
        f"the guide written for you — what joins to what and on which column, "
        f"the quirks that produce silently wrong answers (documented codes that "
        f"do not appear in the data, columns TriMet's metadata omits, counts "
        f"that mean different things in different collections), what the "
        f"coordinate system implies for measurement, and query recipes that "
        f"have each been run against these files."
    )


def catalog_json():
    children = []
    for c in M.COLLECTIONS:
        children.append({
            "rel": "child",
            "href": f"./{c['id']}/collection.json",
            "type": "application/json",
            "title": c["title"],
        })
    return {
        "type": "Catalog",
        "stac_version": STAC_VERSION,
        "stac_extensions": [EXT["portolan"]],
        "id": M.CATALOG_ID,
        "title": M.CATALOG_TITLE,
        "description": M.CATALOG_DESCRIPTION,
        "updated": SYNCED,
        "extent": {
            "spatial": {"bbox": [M.CATALOG_BBOX]},
            "temporal": {"interval": [["2013-01-09T00:00:00Z", None]]},
        },
        "providers": providers(),
        "links": [
            {"rel": "root", "href": "./catalog.json", "type": "application/json",
             "title": M.CATALOG_TITLE},
            {"rel": "describedby", "href": "./README.md", "type": "text/markdown",
             "title": "Catalog README"},
            {"rel": "agents", "href": "./AGENTS.md", "type": "text/markdown",
             "title": "Catalog agent guide"},
            {"rel": "license", "href": M.TERMS_URL, "type": "text/html",
             "title": "TriMet Terms of Use"},
            {"rel": "via", "href": M.GIS_PAGE, "type": "text/html",
             "title": "TriMet Geospatial Data"},
            {"rel": "icon", "href": "./_assets/trimet-logo.png", "type": "image/png",
             "title": "TriMet"},
        ] + children,
    }


# The sync timestamp. Kept in a file so regenerating metadata does not silently
# claim a fresh sync; tools/sync_stamp.py rewrites it when data is re-fetched.
STAMP = ROOT / "sources" / "synced.txt"
SYNCED = STAMP.read_text().strip() if STAMP.exists() else "2026-08-02T00:00:00Z"


def main():
    for coll in M.COLLECTIONS:
        p = OUT / coll["id"] / "collection.json"
        p.write_text(json.dumps(collection_json(coll), indent=2) + "\n")
        print(f"  wrote {p.relative_to(ROOT)}")
    p = OUT / "catalog.json"
    p.write_text(json.dumps(catalog_json(), indent=2) + "\n")
    print(f"  wrote {p.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
