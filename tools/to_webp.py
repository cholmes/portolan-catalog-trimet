#!/usr/bin/env python3
"""Convert the rendered PNG thumbnails to WebP, each under a size budget.

``tools/make_thumbnails.sh`` renders lossless PNGs once. This converts them,
searching per file for the highest quality that still fits the budget, so a
dense layer like `stops` is not held to the same quality as a single polygon.
Re-rendering to try a different quality would refetch every basemap tile; this
does not.

Portolan 0.1 allows only PNG and JPEG for thumbnails. `image/webp` is added by
spec PR #121 (portolan-sdi/portolan-spec#121), which this catalog targets — the
same deliberate deviation the portolan-nl catalog makes.

    python3 tools/to_webp.py [--budget 50000] [--keep-png]
"""
import argparse
import io
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "catalog"

DEFAULT_BUDGET = 50_000
Q_MAX, Q_MIN = 92, 40


def encode(im, q):
    buf = io.BytesIO()
    im.save(buf, "WEBP", quality=q, method=6)
    return buf.getvalue()


def best_under(im, budget):
    """Highest quality in [Q_MIN, Q_MAX] whose encoding fits the budget.

    Returns (bytes, quality, fits). If even Q_MIN overshoots, the Q_MIN encoding
    is returned with fits=False rather than degrading further — a thumbnail that
    is 10% over budget is better than one that is unreadable.
    """
    hi = encode(im, Q_MAX)
    if len(hi) <= budget:
        return hi, Q_MAX, True

    lo, hi_q, best = Q_MIN, Q_MAX, None
    while lo <= hi_q:
        mid = (lo + hi_q) // 2
        data = encode(im, mid)
        if len(data) <= budget:
            best = (data, mid)
            lo = mid + 1
        else:
            hi_q = mid - 1
    if best:
        return best[0], best[1], True
    return encode(im, Q_MIN), Q_MIN, False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--budget", type=int, default=DEFAULT_BUDGET,
                    help=f"max bytes per thumbnail (default {DEFAULT_BUDGET})")
    ap.add_argument("--keep-png", action="store_true",
                    help="leave the source PNG in place")
    args = ap.parse_args()

    pngs = sorted(CATALOG.glob("*/thumbnail.png"))
    if not pngs:
        sys.exit("no catalog/*/thumbnail.png found — run tools/make_thumbnails.sh first")

    over = []
    total = 0
    for png in pngs:
        im = Image.open(png).convert("RGB")
        data, q, fits = best_under(im, args.budget)
        out = png.with_suffix(".webp")
        out.write_bytes(data)
        total += len(data)
        flag = "" if fits else "  OVER BUDGET"
        print(f"  {png.parent.name:<20} {png.stat().st_size:>8,} PNG -> "
              f"{len(data):>7,} WebP  q{q}{flag}")
        if not fits:
            over.append(png.parent.name)
        if not args.keep_png:
            png.unlink()

    print(f"  {'TOTAL':<20} {total:>29,} WebP")
    if over:
        print(f"\n  over budget: {', '.join(over)}")


if __name__ == "__main__":
    main()
