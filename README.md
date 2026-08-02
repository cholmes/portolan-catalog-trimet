# portolan-catalog-trimet

A [Portolan](https://www.portolan-sdi.org/) catalog mirroring the eight
geospatial datasets [TriMet](https://trimet.org/) publishes at
[developer.trimet.org/gis](https://developer.trimet.org/gis/) — the transit
district boundary, routes, rail lines, stops, route stops, rail stops, transit
centers and park and rides for the Portland, Oregon metropolitan area.

TriMet distributes these as Shapefile and KML. This catalog republishes them as
**GeoParquet and PMTiles**, with TriMet's original files and metadata linked from
every collection, column definitions mined from TriMet's own metadata pages, and
visualization styles that reproduce **TriMet's own published cartography**.

**This repository holds the catalog metadata.** The data itself is generated from
TriMet's sources and published to object storage; `.parquet` and `.pmtiles` are
never committed.

| | |
|---|---|
| Published at | `https://data.source.coop/cholmes/trimet` |
| Collections | 8 |
| Features | 15,232 |
| Styles | 29 |
| Spec | Portolan 0.1.0 + [spec#121](https://github.com/portolan-sdi/portolan-spec/pull/121) |

## ⚠️ Licensing

**TriMet's terms of use do not grant redistribution rights for these GIS
downloads.** Section 4 of the
[Terms of Use](https://developer.trimet.org/terms_of_use.shtml) reserves
reproduction, modification, distribution and republication of site Content
without written consent; the redistribution license in section 5 covers the Web
Services API, not these files.

Collections therefore declare `"license": "other"` with a link to those terms
rather than claiming an open license the source does not offer. **Contact
gis@trimet.org before redistributing this data or publishing it further.** For
transit data under clear open terms, TriMet's
[GTFS feed](https://developer.trimet.org/GTFS.shtml) is the better starting
point.

The TriMet name and logo are trademarks of TriMet. The logo appears in this
catalog solely as a link back to trimet.org, which section 6 of those terms
permits. This project is **not affiliated with TriMet**.

## Layout

```
catalog/            the published catalog — synced 1:1 to object storage
  catalog.json  README.md  AGENTS.md  _assets/
  <collection>/
    collection.json  README.md  AGENTS.md  thumbnail.webp
    <collection>.parquet   (gitignored, generated)
    <collection>.pmtiles   (gitignored, generated)
    styles/*.json          plus TriMet's mirrored source style
sources/            TriMet inputs; Shapefiles gitignored, re-fetchable
tools/              the generators
tests/              the gates
docs/               conformance notes
```

`catalog/` **is** the published catalog. Everything in it is published;
everything outside it never is.

## Build

Everything is generated. Nothing under `catalog/` should be hand-edited — the
next build would silently undo it, and `tests/test_regen.py` fails if you try.

```bash
python3 tools/build.py            # full pipeline from the local sources
python3 tools/build.py --fetch    # re-download from TriMet first
```

The steps, in dependency order:

| Step | Script | Needs |
|---|---|---|
| Fetch sources | `tools/fetch.py` | network |
| Shapefile → GeoParquet + PMTiles | `tools/convert.py` | GDAL 3.9+, tippecanoe |
| MapLibre styles | `tools/make_styles.py` | — |
| Render thumbnails | `tools/make_thumbnails.sh` | Node 20/22/24 |
| PNG → WebP under budget | `tools/to_webp.py` | Pillow |
| STAC metadata | `tools/make_collections.py` | pyarrow |
| README + AGENTS | `tools/make_docs.py` | pyarrow |

**Thumbnails need Node 20, 22 or 24 — not 23.** They are rendered by
[chiitiler](https://github.com/Kanahiro/chiitiler) with MapLibre GL Native, which
publishes prebuilt binaries only for ABI v115/v127/v137 and refuses to build from
source. Node 23 is ABI v131 and will fail to install. `brew install node@24` is
keg-only and does not disturb an existing Node. `build.py` skips the step with a
warning if it finds no usable Node, leaving existing thumbnails in place.

## Test

```bash
python3 tests/run_all.py
```

| Test | Checks |
|---|---|
| `test_catalog.py` | Links and asset hrefs resolve; sizes and checksums match the bytes; providers, license, bbox, PMTiles link and style assets are well-formed; docs agree with the data |
| `test_conformance.py` | `rashid check` — only documented deviations may fail. SKIPs without rashid |
| `test_styles.py` | Every style validates against the real MapLibre style spec. SKIPs without chiitiler installed |
| `test_recipes.py` | Every SQL snippet published in the docs actually runs |
| `test_regen.py` | Regenerating reproduces the committed catalog byte-for-byte |

`test_recipes.py` is the one that matters most in practice: a broken example
costs more trust than no example, so every query in every AGENTS.md is executed
against the real files before it ships.

## Publish

```bash
python3 tools/publish.py            # dry run
python3 tools/publish.py --confirm  # upload; needs AWS credentials
```

Syncs `catalog/` 1:1 to the bucket in `catalog.publish.yaml`. Objects whose bytes
already match are skipped. **It never deletes** — removing a file from `catalog/`
does not unpublish it; use `aws s3 rm`.

## Cartography

Where TriMet publishes a style for a layer, this catalog reproduces it rather
than inventing one, and mirrors the source style alongside so the reproduction
can be checked against its origin.

- **`ott:rail`** — the GeoServer SLD behind TriMet's rail maps, retrieved from
  `ws.trimet.org` via WMS `GetStyles`. Its rules key on exactly the `line` values
  the rail layers carry, so `rail-lines/styles/default.json` reproduces it rule
  for rule, including the layered dashed overlays that show which services share
  a track. Mirrored at `catalog/rail-lines/styles/trimet-rail.sld.xml`.
- **`trimet-routes`** — TriMet's MapLibre style at `tiles.trimet.org`, source of
  the line weights and the flat bus color `#136390`. Where it resolves
  `route_color` at draw time from GTFS, the equivalent colors come from TriMet's
  GTFS `routes.txt`. Mirrored at
  `catalog/routes/styles/trimet-routes.style.json`.

Two approximations are made converting SLD to MapLibre, both recorded in each
style's `description`: SLD dash arrays are in pixels while MapLibre's are in
multiples of line width, and the SLD's scale break at denominator 151181 is
rendered as zoom 12.

## Conformance

Passes `rashid check` with one documented deviation — WebP thumbnails, pending
[spec#121](https://github.com/portolan-sdi/portolan-spec/pull/121). See
[`docs/conformance.md`](docs/conformance.md).

## Credits

Data © TriMet. Catalog maintained by Chris Holmes (cholmes@9eo.org), not
affiliated with TriMet. Basemap in the thumbnails © OpenStreetMap contributors,
© CARTO.
