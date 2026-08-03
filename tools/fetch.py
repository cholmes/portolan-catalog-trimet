#!/usr/bin/env python3
"""Re-download the TriMet sources this catalog is built from.

Fetches, for each of the eight layers, the Shapefile zip and the metadata page,
plus TriMet's published cartography (the GeoServer SLDs and the `trimet-routes`
MapLibre style) and the GTFS `routes.txt` the style colors come from.

Writes ``sources/synced.txt``, which is what ``make_collections.py`` stamps into
each collection's ``updated`` field — a mirror has to record when it last synced.

    python3 tools/fetch.py                     # everything
    python3 tools/fetch.py --data              # just the Shapefiles
    python3 tools/fetch.py --data --no-stamp   # ... without recording a sync

KML is fetched only to record its size and checksum in
``sources/source_checksums.json``; the bytes are not kept, since the file is
linked as a remote asset served by TriMet and the route-stops KML alone is 12 MB.
"""
import argparse
import datetime
import hashlib
import io
import json
import sys
import urllib.request
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import manifest as M  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "sources"

GEOSERVER = "https://ws.trimet.org/geoserver/ows"
SLD_LAYERS = ["current_rail", "current_stops", "current_routes"]
GTFS_URL = "https://developer.trimet.org/schedule/gtfs.zip"


def get(url):
    with urllib.request.urlopen(url, timeout=120) as r:
        return r.read()


def multihash(blob):
    return "1220" + hashlib.sha256(blob).hexdigest()


def fetch_data(stamp=True):
    """Download each Shapefile zip and record what TriMet served.

    The size and checksum of TriMet's own zip and KML go into a committed
    sidecar so collection.json can carry `file:size` and `file:checksum` on the
    remote source assets without this repo holding the binaries.
    """
    (SRC / "shp").mkdir(parents=True, exist_ok=True)
    sums = {}
    for coll in M.COLLECTIONS:
        name = coll["source"]
        links = M.source_links(coll)
        blob = get(links["shapefile"])
        d = SRC / "shp" / name
        d.mkdir(exist_ok=True)
        with zipfile.ZipFile(io.BytesIO(blob)) as z:
            z.extractall(d)
        sums[name] = {"shapefile": {"size": len(blob), "checksum": multihash(blob)}}

        if not stamp:
            # The KML is fetched only to checksum it. Skip the ~18 MB of
            # downloads when the sidecar is not being rewritten.
            print(f"  {name:<16} zip {len(blob):>9,} B")
            continue

        kml = get(links["kml"])
        sums[name]["kml"] = {"size": len(kml), "checksum": multihash(kml)}
        print(f"  {name:<16} zip {len(blob):>9,} B   kml {len(kml):>10,} B")

    if stamp:
        (SRC / "source_checksums.json").write_text(json.dumps(sums, indent=2) + "\n")
        print("  source_checksums.json")


def fetch_metadata():
    (SRC / "meta").mkdir(parents=True, exist_ok=True)
    for coll in M.COLLECTIONS:
        url = M.source_links(coll)["metadata"]
        (SRC / "meta" / f"meta_{coll['source']}.shtml").write_bytes(get(url))
        print(f"  meta_{coll['source']}")
    (SRC / "meta" / "terms_of_use.html").write_bytes(get(M.TERMS_URL))
    print("  terms_of_use")


def fetch_styles():
    """TriMet's own cartography. These are the reference this catalog's styles
    reproduce, so they are mirrored rather than merely cited."""
    (SRC / "sld").mkdir(parents=True, exist_ok=True)
    for layer in SLD_LAYERS:
        url = (f"{GEOSERVER}?service=WMS&version=1.1.1&request=GetStyles"
               f"&layers=ott:{layer}")
        (SRC / "sld" / f"{layer}.xml").write_bytes(get(url))
        print(f"  sld/{layer}.xml")
    blob = get("https://tiles.trimet.org/styles/trimet-routes/style.json")
    (SRC / "trimet-routes-style.json").write_bytes(blob)
    print("  trimet-routes-style.json")


def fetch_gtfs():
    """Only routes.txt is kept — the full feed is ~38 MB and the rest is
    schedule data this catalog does not use."""
    blob = get(GTFS_URL)
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        for name in ("routes.txt", "agency.txt", "feed_info.txt"):
            (SRC / name).write_bytes(z.read(name))
            print(f"  {name}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", action="store_true", help="Shapefiles only")
    ap.add_argument("--no-stamp", action="store_true",
                    help="do not rewrite synced.txt or source_checksums.json")
    args = ap.parse_args()

    print("Shapefiles:")
    fetch_data(stamp=not args.no_stamp)
    if not args.data:
        print("Metadata pages:")
        fetch_metadata()
        print("TriMet cartography:")
        fetch_styles()
        print("GTFS:")
        fetch_gtfs()

    if args.no_stamp:
        # CI rebuilds the data files to run the tests; that is not a sync, and
        # rewriting the stamp would change every collection's `updated` field
        # and make test_regen.py fail against the committed catalog.
        print("\n--no-stamp: synced.txt and source_checksums.json left as committed")
        return

    when = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    (SRC / "synced.txt").write_text(when + "\n")
    print(f"\nsynced.txt = {when}")
    print("Source contents may have changed — re-check tools/manifest.py against")
    print("the metadata pages before publishing (counts, dates, code lists).")


if __name__ == "__main__":
    main()
