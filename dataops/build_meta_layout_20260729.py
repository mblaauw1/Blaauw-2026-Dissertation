#!/usr/bin/env python3
"""Turn the meta-figure ASSIGNMENT into concrete artboard rects and per-figure cells (2026-07-29f).

CONSTRAINTS THAT SET THE NUMBERS
  * Illustrator's canvas is about 16,383pt ACROSS IN TOTAL, not +/-16,383 per axis. A first attempt at
    10,000 x 7,000pt boards tiled 3x3 (a 30,800 x 21,800pt spread) threw Error 1200 'CoOA' on the very
    first artboardRect assignment. The real budget is a ~16,000pt square for ALL NINE boards together -
    consistent with copy.ai itself, whose artboards span 13,937 x 15,336pt.
  * 9 boards tiled 3x3 with a 200pt gutter therefore caps each board at 5,200 x 5,200pt, and that is what
    they are - as large as the canvas allows, which is what she asked for. Cells still come out at
    430-2,400pt wide against figures that are 400-500pt wide in copy.ai, so nothing is being shrunk below
    its current size except on the two most crowded boards.
  * Cells are laid out on a grid sized to the board's own figure count, so a 14-figure board gets big cells
    and a 120-figure board gets small ones. Nothing is forced to a single global scale.

ASPECT RATIO IS NEVER FORCED. A cell is a BUDGET, not a frame: the JSX reads each placed PDF's natural
aspect and scales it to fit inside its cell, so a figure can end up letterboxed in its cell but is never
stretched. This file only decides where each cell is and how big it may be.

  python3 build_meta_layout_20260729.py       # write meta_layout.json + print the plan
"""
import collections
import json
import math
import os

ROOT = "/Volumes/4 MB"
ASSIGN = os.path.join(ROOT, "_deck_jsx_inputs/meta_assignment.json")
OUT = os.path.join(ROOT, "_deck_jsx_inputs/meta_layout.json")

BOARD_W, BOARD_H = 5100.0, 5100.0        # 3*5100 + 2*200 = 15,700pt across, inside the ~16,383pt canvas
GUTTER = 200.0                          # between boards
PAD = 120.0                             # inside a board, around the whole grid
TITLE_H = 190.0                         # reserved strip at the top of each board for its heading
CELL_GAP = 26.0                         # between cells
ORDER = ["M1", "M2", "M3", "M4", "M5", "M5b", "M6", "M7", "M8"]

TITLES = {
    "M1": "1 | Ablation destroys one or several kinetochores in early mitosis",
    "M2": "2 | One sisterless kinetochore does not delay metaphase; several do",
    "M3": "3 | Mad1 at sisterless kinetochores: an unsatisfied checkpoint at the poles",
    "M4": "4 | Longer metaphase, more exaggerated cell-shape phenotypes",
    "M5": "5 | Force on persistent polar kinetochores, and how small chromosomes escape",
    "M5b": "5b | Kinetochore shape and motion across mitotic time: the systematic sweep",
    "M6": "6 | Chromosome size and sisterless number set the anaphase fate",
    "M7": "7 | Three disrupted chromosomes: oscillation, force and spindle stability",
    "M8": "8 | When the ablation happens sets the delay",
}


def grid_for(n, w, h):
    """Columns/rows that best fill a w x h area with n cells of roughly 1.4:1 (the usual figure shape)."""
    best = None
    for cols in range(1, n + 1):
        rows = math.ceil(n / cols)
        cw = (w - (cols - 1) * CELL_GAP) / cols
        ch = (h - (rows - 1) * CELL_GAP) / rows
        if cw <= 0 or ch <= 0:
            continue
        # prefer the grid whose cell shape is closest to 1.4:1 and whose cells are biggest
        score = min(cw / 1.4, ch) * min(1.0, (cw / ch) / 1.4 if ch else 0)
        if best is None or score > best[0]:
            best = (score, cols, rows, cw, ch)
    return best[1], best[2], best[3], best[4]


def main():
    A = json.load(open(ASSIGN))
    # HER PRUNE (2026-07-30). She removed 74 figures from META by hand in
    # META_FIGURES_20260729_Copy.ai, keeping 482. That keep-list is honoured here: a figure absent from it
    # is not laid out at all, so a rebuild can never restore something she deleted. Delete
    # _deck_jsx_inputs/meta_kept.json to go back to laying out everything.
    KEEP = None
    kp = os.path.join(ROOT, "_deck_jsx_inputs/meta_kept.json")
    if os.path.isfile(kp):
        KEEP = set(json.load(open(kp)))
        print(f"honouring her keep-list: {len(KEEP)} figures kept, {len(A)-len(KEEP & set(A))} dropped")
    by = collections.defaultdict(list)
    for f, v in A.items():
        if KEEP is not None and f not in KEEP:
            continue
        by[v["meta"]].append(f)
    # inside a board, keep figures from the same source artboard together, then alphabetical -
    # families and their zoom companions stay side by side instead of scattering
    for m in by:
        by[m].sort(key=lambda f: (A[f]["src"], f))

    layout = {"boards": {}, "cells": {}}
    for i, m in enumerate(ORDER):
        col, row = i % 3, i // 3
        # PROBED, not guessed. A JSX binary-search on a fresh 1000x1000 document (artboard 0 at
        # [0,1000,1000,0], centre (500,500)) found the usable artboard window to be x [-7657, 8664] and
        # y down to -7188 - i.e. a ~16,320pt canvas centred on artboard 0's CENTRE, not on the origin and
        # not +/-16383 per axis. Three earlier guesses each cost a failed run with Error 'CoOA'.
        # The 15,700pt grid is therefore centred on (500, 500).
        left = -7350 + col * (BOARD_W + GUTTER)
        top = 8350 - row * (BOARD_H + GUTTER)
        rect = [left, top, left + BOARD_W, top - BOARD_H]
        figs = by.get(m, [])
        gw = BOARD_W - 2 * PAD
        gh = BOARD_H - 2 * PAD - TITLE_H
        cols, rows, cw, ch = grid_for(max(1, len(figs)), gw, gh)
        layout["boards"][m] = {"rect": rect, "title": TITLES[m], "n": len(figs),
                               "cols": cols, "rows": rows, "cell": [round(cw, 1), round(ch, 1)]}
        gx0 = left + PAD
        gy0 = top - PAD - TITLE_H
        for k, f in enumerate(figs):
            c, r = k % cols, k // cols
            x = gx0 + c * (cw + CELL_GAP)
            y = gy0 - r * (ch + CELL_GAP)
            layout["cells"][f] = {"meta": m, "x": round(x, 1), "y": round(y, 1),
                                  "w": round(cw, 1), "h": round(ch, 1),
                                  "red": not A[f]["sure"], "title": A[f]["title"][:150]}

    xs = [v for b in layout["boards"].values() for v in (b["rect"][0], b["rect"][2])]
    ys = [v for b in layout["boards"].values() for v in (b["rect"][1], b["rect"][3])]
    json.dump(layout, open(OUT, "w"), indent=1)
    print(f"{len(layout['cells'])} cells across {len(layout['boards'])} boards")
    for m in ORDER:
        b = layout["boards"][m]
        print(f"   {m:4s} {b['n']:4d} figs  {b['cols']:2d}x{b['rows']:<2d} grid  cell "
              f"{b['cell'][0]:6.0f}x{b['cell'][1]:<5.0f}pt   {b['title'][:60]}")
    print(f"\ncanvas extent x {min(xs):.0f}..{max(xs):.0f}   y {min(ys):.0f}..{max(ys):.0f}"
          f"   (span must stay under 16383)")
    assert (max(xs)-min(xs)) < 16383 and (max(ys)-min(ys)) < 16383, "canvas SPAN limit exceeded"


if __name__ == "__main__":
    main()
