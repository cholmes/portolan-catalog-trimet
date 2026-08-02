# Portolan conformance

The catalog targets **Portolan 0.1.0** plus spec PR
[#121](https://github.com/portolan-sdi/portolan-spec/pull/121). Conformance means
passing [rashid](https://github.com/portolan-sdi/rashid), not claiming to
conform, so it is checked in CI:

```
python3 tests/test_conformance.py
```

The test fails on any error or warning whose rule is not in the `ACCEPTED` list.
That list is reproduced below with the reasoning. **It must never grow without a
matching entry here.**

## Accepted deviations

### PTL-VIZ-001 — thumbnails are WebP (8 findings)

> thumbnail asset 'thumbnail' has type 'image/webp', expected image/png or image/jpeg

Portolan 0.1 permits only `image/png` and `image/jpeg` for thumbnails. Spec PR
[#121](https://github.com/portolan-sdi/portolan-spec/pull/121), *"feat(spec):
allow image/webp for thumbnails"*, adds `image/webp` to that list; its companion
validator change is [rashid#91](https://github.com/portolan-sdi/rashid/pull/91).
This catalog is authored against that change, and the finding will disappear when
it lands.

The reason WebP is worth the deviation is size. Each thumbnail is a 800px
MapLibre render over a raster basemap, which is expensive to store losslessly:

| Encoding | Average per thumbnail | Total for 8 |
|---|---|---|
| PNG, 800px, optimized | ~187 KB | 1.5 MB |
| WebP, quality-searched under 50 KB | ~49 KB | 394 KB |

`tools/to_webp.py` binary-searches the quality per file for the highest one that
still fits a 50 KB budget, so a dense layer such as `stops` is compressed harder
than a single polygon rather than holding every image to one quality.

## Informational findings, deliberately not addressed

### PTL-PRO-002 — no `canonical` link (8 findings, info)

> mirror collection has no rel:'canonical' link; add one if the upstream publishes its own STAC catalog

Correct as it stands. A mirror must add a `canonical` link **when the source
publishes its own STAC catalog**. TriMet does not: `developer.trimet.org/gis`
serves Shapefile, KML and HTML metadata pages, and there is no STAC anywhere on
it. Every collection carries `via` links to TriMet's per-layer metadata page and
to the GIS index, which is the required provenance. The spec anticipates exactly
this and says a validator "MAY surface a mirror without a `canonical` link as
informational, never as a failure".

If TriMet ever publishes STAC, add the `canonical` link in
`tools/make_collections.py:links_for()`.

## Notes on choices the validator does not check

- **`license: "other"`.** TriMet's terms do not grant redistribution rights, so
  no SPDX identifier fits. Each collection carries a `rel: license` link to
  [TriMet's Terms of Use](https://developer.trimet.org/terms_of_use.shtml), which
  is what the spec requires for `other`. See the licensing note in the root
  README.
- **Source assets carry `file:size` and `file:checksum` from a sidecar.**
  TriMet's Shapefile and KML are remote assets this repo does not host, so their
  size and checksum are recorded by `tools/fetch.py` into
  `sources/source_checksums.json` at sync time and emitted from there. They
  describe what TriMet served at the moment named in each collection's `updated`
  field; if TriMet reissues a layer they will stop matching, which is precisely
  the signal a consumer would want.
- **TriMet's metadata page is a `via` link, not an asset.** It describes the data
  rather than being the data, and its bytes change whenever TriMet edits the
  page, so a checksum on it would be noise.
- **The mirrored SLDs carry the `metadata` role, not `style`.** Portolan reserves
  `style` for MapLibre style files. TriMet's `ott:rail` and `ott:stops` SLDs are
  mirrored into `styles/` as the reference our MapLibre styles reproduce, so they
  are registered with `metadata`. The mirrored `trimet-routes` MapLibre style
  does carry `style`, because that is what it is.
