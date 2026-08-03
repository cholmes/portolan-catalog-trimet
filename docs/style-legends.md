# Making Portolan styles produce legends

Guidance for anyone — human or agent — authoring MapLibre styles for a Portolan
catalog. Written generically, not specific to this catalog, so it can be lifted
into other catalogs or into the spec's styling best practices.

## The one thing to understand

**A legend is derived from your style, not declared in it.** There is no
`legend` field. portolan-browser builds one by inspecting the style you publish,
and it looks in exactly one place:

> the **first layer of type `fill`**, and its **`fill-color`** paint property.

From [`src/utils/portolanStyles.js`](https://github.com/portolan-sdi/portolan-browser/blob/main/src/utils/portolanStyles.js):

```js
export function extractLegend(glStyle) {
  if (!glStyle?.layers) { return []; }
  const fillLayer = glStyle.layers.find(l => l.type === 'fill');
  if (!fillLayer) { return []; }
  const fillColor = fillLayer.paint?.['fill-color'];
  if (!fillColor || typeof fillColor === 'string') { return []; }
  if (!Array.isArray(fillColor)) { return []; }
  const type = fillColor[0];
  if (type === 'step')  { /* … */ }
  if (type === 'match') { /* … */ }
  return [];
}
```

Every `return []` there is a silent failure. Your style stays valid, the map
draws correctly, and no legend appears. Nothing warns you.

## The two traps

### 1. Line and point styles get no legend by default

`extractLegend` never looks at `line-color` or `circle-color`. A style whose
only layers are `line` or `circle` — which is most transit, road, hydrography,
address and POI data — produces nothing, however carefully its colors encode an
attribute.

**Fix:** prepend an inert `fill` layer carrying the same expression.

```json
{
  "id": "stops-legend",
  "type": "fill",
  "source": "data",
  "source-layer": "stops",
  "paint": { "fill-color": ["match", ["get", "type"], "BUS", "#4679AA", "MAX", "#1359AE", "#CCCCCC"],
             "fill-opacity": 0 }
}
```

This is safe twice over: a `fill` layer renders nothing at all on line or point
geometry, and `fill-opacity` is 0 regardless. Adding these to a catalog and
re-rendering its thumbnails produced byte-identical images. The workaround is
tracked as [portolan-browser#13](https://github.com/portolan-sdi/portolan-browser/issues/13).

Put it **first**, before the visible layers — `find()` takes the first `fill`
layer, so a real fill layer earlier in the list would win.

### 2. Only `step` and `match` are understood

`interpolate` is the natural way to write a graduated ramp, and it is **silently
ignored**. So are `case`, `coalesce`, and a bare `["get", …]`. This is the
easiest mistake to make, because the map looks perfect.

```jsonc
// Renders beautifully. Legend: empty.
["interpolate", ["linear"], ["get", "spaces"], 0, "#D5EEF8", 750, "#8C2A10"]

// Same data, legend works.
["step", ["get", "spaces"], "#D5EEF8", 150, "#7FB6D9", 350, "#4679AA", 750, "#8C2A10"]
```

You do not have to give up a smooth ramp on the map. Keep `interpolate` on the
visible layer and give the inert legend layer a `step` that classes the same
ramp — the legend is a summary, and a classed summary of a continuous ramp is
what a reader wants anyway.

## How each expression is read

**`match`** — `["match", ["get", field], val1, color1, val2, color2, …, fallback]`

One legend entry per value/color pair, labelled with the value as a string. The
**fallback is dropped** (`slice(2, -1)`), so a catch-all "other" category will
not appear. If you need it visible, make it an explicit value.

**`step`** — `["step", ["get", field], defaultColor, stop1, color1, stop2, color2, …]`

Entries are labelled `< stop1`, then `stop1–stop2`, and the last is `stopN+`.
Note the label text comes from the numbers alone, so choose round, meaningful
break values — they are what the reader sees.

## Checklist for a new style

1. Does color encode an attribute? If it is a single constant, **stop** — no
   legend belongs here, and inventing one describes a classification that does
   not exist.
2. Is the classifying expression on `fill-color` of the first `fill` layer? If
   the visible layers are `line` or `circle`, prepend the inert fill layer.
3. Is the expression `step` or `match`? Convert `interpolate` to `step`.
4. Are the visible layers **filtered** rather than data-driven — one flat-colored
   layer per category? Then the classification exists nowhere as an expression;
   restate it as a `match` for the legend, and keep the two in sync by hand.
5. Verify. Do not assume.

## Verify it mechanically

Assertions beat inspection here, because the failure is invisible. This check
found three broken legends in a catalog whose styles all validated and all
drew correctly:

```python
import json, pathlib

for p in pathlib.Path("catalog").glob("*/styles/*.json"):
    style = json.loads(p.read_text())
    fill = next((l for l in style.get("layers", []) if l.get("type") == "fill"), None)
    if not fill:
        continue
    color = fill.get("paint", {}).get("fill-color")
    if isinstance(color, list) and color[0] not in ("step", "match"):
        print(f"{p}: '{color[0]}' legend renders empty")
```

`tests/test_styles.py` in this repo runs exactly that alongside MapLibre
style-spec validation, and reports how many styles carry a readable legend.

## When *not* to add a legend

Legends should describe a real classification. Leave them off when:

- the layer paints a single constant color;
- the collection is one feature, so there is nothing to distinguish;
- the encoding is a `heatmap`, whose ramp is over `heatmap-density` rather than
  any attribute of a feature.

In this catalog 21 of 29 styles carry a legend and 8 deliberately do not, for
exactly those reasons.
