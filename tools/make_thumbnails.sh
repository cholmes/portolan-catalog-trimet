#!/usr/bin/env bash
# Render a thumbnail per collection by drawing its own styles/default.json with
# chiitiler (MapLibre GL Native), over a light basemap. Portolan asks that the
# thumbnail be generated from default styling, so this renders the real style
# file rather than approximating it.
#
#   bash tools/make_thumbnails.sh [collection ...]
#
# Requires Node.js 18+. Clones chiitiler into $CHIITILER_DIR on first run.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CATALOG_DIR="$ROOT/catalog"
CHIITILER_DIR="${CHIITILER_DIR:-/tmp/chiitiler}"
PORT="${PORT:-13579}"
SIZE="${SIZE:-800}"
# Rendered lossless. tools/to_webp.py then converts to WebP under a size
# budget, searching quality per file -- doing it there rather than here means
# trying a different budget does not refetch every basemap tile.
# Bash ends a ${VAR:-default} at the first "}", so a {z}/{x}/{y} template cannot
# be inlined as the default -- it would silently become "{z/{x}/{y}.png}" and the
# basemap would fetch nothing. Keep the template in its own variable.
DEFAULT_BASEMAP_URL='https://basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png'
BASEMAP_URL="${BASEMAP_URL:-$DEFAULT_BASEMAP_URL}"

# Portable file size (macOS stat differs from GNU stat).
fsize() { stat -f%z "$1" 2>/dev/null || stat -c%s "$1"; }

if [ ! -d "$CHIITILER_DIR/node_modules" ]; then
    echo "Installing chiitiler into $CHIITILER_DIR ..."
    rm -rf "$CHIITILER_DIR"
    git clone --depth 1 https://github.com/Kanahiro/chiitiler "$CHIITILER_DIR"
    (cd "$CHIITILER_DIR" && npm install --silent)
fi

echo "Starting chiitiler on :$PORT ..."
(cd "$CHIITILER_DIR" && CHIITILER_PROCESSES=0 npx tsx src/main.ts tile-server \
    --port "$PORT" --cache memory > /tmp/chiitiler.log 2>&1) &
SERVER_PID=$!
trap 'kill $SERVER_PID 2>/dev/null || true' EXIT

for _ in $(seq 1 40); do
    curl -sf "http://localhost:$PORT/health" >/dev/null 2>&1 && break
    curl -s "http://localhost:$PORT/" >/dev/null 2>&1 && break
    sleep 1
done
if ! kill -0 $SERVER_PID 2>/dev/null; then
    echo "ERROR: chiitiler failed to start; see /tmp/chiitiler.log" >&2
    exit 1
fi

WANTED=("$@")
COUNT=0

while IFS='|' read -r CID BBOX; do
    if [ ${#WANTED[@]} -gt 0 ]; then
        found=0
        for w in "${WANTED[@]}"; do [ "$w" = "$CID" ] && found=1; done
        [ $found -eq 1 ] || continue
    fi
    DIR="$CATALOG_DIR/$CID"
    PM="$DIR/$CID.pmtiles"
    STYLE="$DIR/styles/default.json"
    [ -f "$PM" ] && [ -f "$STYLE" ] || { echo "skip $CID (missing pmtiles or style)"; continue; }

    PMTILES_PATH="$(cd "$DIR" && pwd)/$CID.pmtiles"
    RENDER="$DIR/.render-style.json"

    PMTILES_PATH="$PMTILES_PATH" BASEMAP_URL="$BASEMAP_URL" \
    STYLE="$STYLE" RENDER="$RENDER" python3 - <<'PYSTYLE'
import json, os
style = json.load(open(os.environ['STYLE']))
style['sources'] = {
    'basemap': {'type': 'raster', 'tiles': [os.environ['BASEMAP_URL']], 'tileSize': 256},
    'data': {'type': 'vector',
             'tiles': ['pmtiles://%s/{z}/{x}/{y}' % os.environ['PMTILES_PATH']]},
}
style['layers'] = [{'id': 'basemap', 'type': 'raster', 'source': 'basemap'}] + style.get('layers', [])
# chiitiler has no glyph server configured, so drop text from the render. The
# published style keeps its labels; only the thumbnail goes without them.
style['layers'] = [l for l in style['layers'] if l.get('type') != 'symbol']
json.dump(style, open(os.environ['RENDER'], 'w'))
PYSTYLE

    OUT="$DIR/thumbnail.png"
    TMP="$DIR/.thumbnail.png.tmp"
    curl -s -X POST "http://localhost:$PORT/clip.png?bbox=${BBOX}&size=${SIZE}" \
        -H "Content-Type: application/json" \
        -d "{\"style\": $(cat "$RENDER")}" -o "$TMP"
    rm -f "$RENDER"

    # A render failure answers with a short error string, so only replace the
    # existing thumbnail once the response is plausibly a real PNG.
    if [ -f "$TMP" ] && [ "$(fsize "$TMP")" -gt 5000 ]; then
        mv "$TMP" "$OUT"
        echo "  ok   $CID  ($(fsize "$OUT") bytes)"
        COUNT=$((COUNT + 1))
    else
        echo "  FAIL $CID: $(head -c 200 "$TMP" 2>/dev/null)"
        rm -f "$TMP"
    fi
done < <(ROOT="$ROOT" python3 - <<'PYLIST'
import os, sys, pathlib
sys.path.insert(0, str(pathlib.Path(os.environ["ROOT"], "tools").resolve()))
from manifest import COLLECTIONS
for c in COLLECTIONS:
    w, s, e, n = c["bbox"]
    # Pad by 4% of the larger span so features are not flush against the edge.
    pad = max(e - w, n - s) * 0.04
    print(f'{c["id"]}|{w-pad:.6f},{s-pad:.6f},{e+pad:.6f},{n+pad:.6f}')
PYLIST
)

echo "Done: $COUNT thumbnails rendered as PNG"
echo "Next: python3 tools/to_webp.py"
