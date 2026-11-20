# Portolan conformance

The catalog targets **Portolan 0.3.0**, declared through the
`https://schemas.portolan-sdi.org/portolan/v0.3.0/schema.json` extension URI
that `tools/manifest.py` stamps on every object. Conformance means passing
[rashid](https://github.com/portolan-sdi/rashid) (0.4.0 or later, which
implements the 0.3 rules), not claiming to conform, so it is checked in CI:

```
python3 tests/test_conformance.py
```

The test fails on any error or warning whose rule is not in the `ACCEPTED` list.
That list is reproduced below with the reasoning. **It must never grow without a
matching entry here.**

## Accepted deviations

None. The catalog passes rashid 0.4.0 with zero errors and zero warnings.

Portolan 0.3 allows `image/webp` thumbnails, so the WebP deviation this file
carried against 0.1 (spec PR
[#121](https://github.com/portolan-sdi/portolan-spec/pull/121)) is retired. The
size reasoning stands and still motivates the format choice: a 800px PNG render
averages ~187 KB where `tools/to_webp.py` holds every WebP under a 50 KB budget
by binary-searching the quality per file.

Portolan 0.3 also requires one style asset per collection to carry the
`default` role (PTL-VIZ-006). Each collection's `styles/default.json` carries
it, stamped by `tools/make_collections.py`.

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
