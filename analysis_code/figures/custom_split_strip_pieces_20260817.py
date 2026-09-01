#!/usr/bin/env python3
"""Emit each timestrip ALSO as independently movable PIECES.

USER 2026-08-16: "right now they exist as one 'unit' or 'piece' and I need to add some notation that will
require them to be broken apart ... i need the ablation and monitoring to be separate 'pieces' that i can
move independently on the artboard, and then even beyond that, for the ablation strips, i need each group
of three frames that corresponds to an ablation to be movable by itself."

WHY A POST-PROCESS AND NOT A CHANGE TO emit()
  A placed link cannot be subdivided in Illustrator, so the split has to happen in the render. But the
  combined PDF `<name>.pdf` is linked by SEVERAL decks at once (NEW_TIMESTRIPS, META_FIGURES_20260805, the
  paper-figure files). Replacing it would silently reshape the figure everywhere. So this ADDS
  `<name>__piece<N>` files beside it and leaves the combined one exactly as it is — only
  META_FIGURES_20260814.ai gets the piece placements.

HOW THE CUT IS FOUND
  `ts_render.emit` stacks the portions with a GAP band of solid value-20 rows between them. Those bands are
  found by scanning for rows that are uniformly that value, so the cut lands exactly on the boundary the
  renderer itself drew — no guessing at panel heights.
"""
import os, sys, glob
import numpy as np, cv2
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import lib

lib.apply_style()
SRC = "/Volumes/4 MB/ablation_figures_20260625/group1/timestrips2"
PDF = "/Volumes/4 MB/ablation_figures_20260625/_ai_relink/pdf"
ONLY = sys.argv[1] if len(sys.argv) > 1 else "nf9_"

def rows_of_gap(img, val=20, tol=6):
    """Row bands that separate PORTIONS in a rendered strip.

    2026-08-17 — WHITE-PAGE FIRST. This used to look only for bands of the value-20 gap colour, which is how
    `ts_render.assemble` separates the two channel ROWS inside one portion. But the delivered `.png` is a
    matplotlib render in which each PORTION is its own axes on a WHITE page, and matplotlib's resampling
    leaves that 4 px value-20 band no longer exactly 20 — so after the black bars were removed from the
    strips, several of them suddenly reported "no gap bands -> skipped" and kept their OLD, black-barred
    pieces on disk. In other words the scan had partly been keying on the black bars themselves.
    So: segment on white page rows, which is what actually delimits portions here, and fall back to the
    value-20 scan for any raster that has no page (e.g. a `_notext` raster passed in directly)."""
    white = (img.min(axis=(1, 2)) >= 250)
    bands, start = [], None
    for i, v in enumerate(white):
        if v and start is None: start = i
        elif not v and start is not None:
            if i - start >= 4: bands.append((start, i))
            start = None
    if start is not None and len(white) - start >= 4: bands.append((start, len(white)))
    # drop a leading/trailing page margin — those are not separators between portions
    bands = [(a, b) for a, b in bands if a > 0 and b < img.shape[0]]
    if bands: return bands

    m = (np.abs(img.astype(np.int16) - val) <= tol).all(axis=(1, 2))
    bands, start = [], None
    for i, v in enumerate(m):
        if v and start is None: start = i
        elif not v and start is not None:
            if i - start >= 4: bands.append((start, i))
            start = None
    if start is not None and len(m) - start >= 4: bands.append((start, len(m)))
    return bands

made = 0
for p in sorted(glob.glob(f"{SRC}/*.png")):
    base = os.path.basename(p)[:-4]
    if ONLY not in base or base.endswith("_notext") or "__piece" in base: continue   # never re-split a piece
    img = cv2.imread(p)
    if img is None: continue
    # 2026-08-17: CLEAR THIS BASE'S OLD PIECES FIRST. Pieces are derived art; if a re-render changes how a
    # strip splits (or stops it splitting), the previous run's pieces would otherwise survive on disk and
    # keep showing whatever defect the strip has since had fixed — which is exactly what happened when the
    # black bars were removed and several strips began reporting "no gap bands".
    for _old in glob.glob(f"{SRC}/{base}__piece*.png") + glob.glob(f"{PDF}/{base}__piece*.pdf"):
        try: os.remove(_old)
        except OSError: pass
    bands = rows_of_gap(img)
    if not bands:
        print(f"  {base}: no gap bands -> single piece, skipped"); continue
    cuts = [0] + [ (a + b) // 2 for a, b in bands ] + [img.shape[0]]
    pieces = [img[cuts[i]:cuts[i+1]] for i in range(len(cuts) - 1)]
    pieces = [q for q in pieces if q.shape[0] > 40]
    if len(pieces) < 2:
        print(f"  {base}: only one usable piece, skipped"); continue
    # ── USER 2026-08-16, the finer half ──────────────────────────────────────────────────────────
    # "for the ablation strips, i need each group of three frames that corresponds to an ablation to be
    #  movable by itself."
    # Done by slicing the two ROWS of the ablation portion SEPARATELY, which is what makes it possible
    # without padding. `emit` pads the narrower row out to the widest, so the whole-cell row (n_targets
    # tiles) and the zoom row (3 x n_targets tiles) are NOT column-aligned inside the portion — an earlier
    # attempt to divide the portion as a block gave 5 groups for a 3-ablation strip and was reverted.
    # Slicing per row sidesteps that entirely: both rows are built from the SAME tile width,
    # tile_w = portion_width / (3 * n_targets), so every cut lands on a real tile boundary.
    # n_targets is READ from the strip's own sidecar (`ablation` is one entry per ablation), never inferred
    # from geometry.
    import json as _json
    _sc = os.path.join(SRC, base + "_frames.json")
    if os.path.exists(_sc) and len(pieces) >= 2:
        try:
            n_t = len(_json.load(open(_sc)).get("ablation") or [])
        except Exception:
            n_t = 0
        if n_t > 1:
            abl = pieces[0]
            gb = rows_of_gap(abl)
            split_y = gb[0][0] if gb else abl.shape[0] // 2      # whole-cell row ends where the gap starts
            rowA, rowB = abl[:split_y], abl[split_y:]
            tw = abl.shape[1] / float(3 * n_t)
            subs = []
            for i2 in range(n_t):
                a0, a1 = int(round(i2 * tw)), int(round((i2 + 1) * tw))          # whole-cell tile i
                z0, z1 = int(round(3 * i2 * tw)), int(round(3 * (i2 + 1) * tw))  # its zoom triple
                if a1 - a0 > 20 and rowA.shape[0] > 20: subs.append(rowA[:, a0:a1])
                if z1 - z0 > 20 and rowB.shape[0] > 20: subs.append(rowB[:, z0:z1])
            if subs:
                pieces = subs + pieces[1:]
                print(f"      ablation portion -> {n_t} whole-cell tiles + {n_t} zoom triples")

    for n, q in enumerate(pieces, 1):
        name = f"{base}__piece{n}"
        h, w = q.shape[:2]; dpi = 200.0
        fig = plt.figure(figsize=(w/dpi, h/dpi), dpi=dpi)
        ax = fig.add_axes([0, 0, 1, 1]); ax.axis("off")
        ax.imshow(q[..., ::-1], interpolation="none")
        fig.savefig(f"{PDF}/{name}.pdf", dpi=dpi, pad_inches=0)
        fig.savefig(f"{SRC}/{name}.png", dpi=dpi, pad_inches=0)
        plt.close(fig); made += 1
    print(f"  {base}: {len(pieces)} pieces")
print(f"TOTAL piece files: {made}")
