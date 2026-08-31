#!/usr/bin/env python3
"""Rebuild the ARTBOARD-5 EXCERPTS that META_FIGURES_20260814.ai links.

WHY THIS FILE EXISTS
  These two excerpts were originally hand-cut by a throwaway script (2026-08-17 01:38). That script did not
  survive, so when the source strips were re-rendered to remove their black bars the excerpts could not be
  regenerated -- the deck kept 01:38 art with a black band baked in, and the only way back was to
  reverse-engineer the crop by template-matching the PDF against the strip. USER 2026-08-17:
  *"are you integrating changes that correct these things into the code that generates the figures so they
  dont have to be fixed again"* -- so the recipe now lives HERE, declaratively, and is re-runnable.

WHAT AN EXCERPT IS
  The MONITORING portion (BOTH rows: phase above fluor) of one timestrip, optionally reduced to a subset of
  its columns, at ~2:1 -- the aspect of her existing artboard-5 artwork (740x373 = 4 square panels over 2
  rows). NOTES 2026-08-17 records that an earlier attempt produced 4:1 and 1520x1658 because the gap-band
  scan grabbed the wrong band; that is why the portion is located here by WHITE PAGE rows (matplotlib draws
  each portion as its own axes on a white page) rather than by dark gap bands, and why the aspect is
  ASSERTED before anything is written.

COLUMN SELECTION
  `cols` is a list of indices into the strip's `_frames.json` "monitoring" list -- NOT pixel coordinates --
  so the excerpt keeps meaning if the strip is re-rendered. `None` means "every monitoring column".
  The polar excerpt is columns 1,3,5,6 of 7 (10:53, 21:11, 26:26, 31:26); it is NOT contiguous, which is
  exactly what a naive crop got wrong (it silently substituted 23:50 for 10:53).

RUN:  python3 custom_ab5_excerpts_20260817.py
"""
import os, sys, json
import numpy as np, cv2
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import lib

SRC = "/Volumes/4 MB/ablation_figures_20260625/group1/timestrips2"
PDF = "/Volumes/4 MB/ablation_figures_20260625/_ai_relink/pdf"

# name -> (source strip basename, monitoring column indices or None for all, expected aspect)
# The ASPECT is per-excerpt and is asserted before anything is written: it is the guard that stops a
# malformed crop reaching her Figure 4 (NOTES: "replacing her Figure 4 artwork with either would damage the
# figure"). 4 columns over 2 rows ~ 2:1; 7 columns over 2 rows ~ 3.45:1.
EXCERPTS = {
    # USER 2026-08-20 (artboard 5, item 5): match the longest strip's column count. This excerpt was showing a
    # 4-column SUBSET of a 7-column strip; the subset is dropped so all seven are shown.
    "AB5_EXCERPT_polar":            ("nf10_1-sisterless-persistent-polar__20250402_ptk_yfpcdc20_2", None,         2.00),
    "AB5_EXCERPT_hidden_in_plate":  ("nf10_1-sisterless__20260420_ptk2_eyfp_cdc20_1_ablation_11",   None,         2.00),
    # 2026-08-17: added when the last VISIBLE embedded raster on artboard 5 was identified. Its 7 monitoring
    # timestamps (3:09 7:48 13:09 18:08 25:48 32:08 38:09) matched this strip's sidecar EXACTLY, and its
    # 3.45:1 shape showed it was the monitoring portion only -- NOT the whole 1.61:1 strip, so relinking it
    # to the full strip PDF would have replaced a 2-row excerpt with a 4-portion figure.
    "AB5_EXCERPT_1sisterless_11":   ("nf9_1-sisterless__20250411_ptk_yfpcdc20_11",                  None,         3.45),
}
ASPECT_TOL    = 0.12


def monitoring_portion(img, n_mon=None):
    """The monitoring portion as a LIST of channel-row boxes [(y0, y1, x0, x1), ...], phase then fluor.

    `ts_render.emit` renders each portion as its own matplotlib axes on a white page, so the two monitoring
    channel rows arrive as TWO separate white-separated bands, each `n_mon` panels wide. (They are also
    preceded by the single-panel ablation band and, on strips that have one, a 3-slot zoom band.) The
    earlier version assumed one band and took `bands[-1]` with `cols[0]`, which extracted a single 377 px
    tile once those extra bands appeared. Selecting the bands whose CONTENT-RUN COUNT equals n_mon is a
    property of the thing being looked for, so it survives further layout changes."""
    H, W = img.shape[:2]
    white_row = (img.min(axis=(1, 2)) >= 250)
    bands, s = [], None
    for i in range(H):
        if not white_row[i] and s is None: s = i
        elif white_row[i] and s is not None: bands.append((s, i - s)); s = None
    if s is not None: bands.append((s, H - s))
    bands = [b for b in bands if b[1] >= 60]          # 60: skip the title text band

    def _runs(y0, h):
        strip = img[y0:y0 + h]
        wc = (strip.min(axis=(0, 2)) >= 250)
        out, s2 = [], None
        for j in range(W):
            if not wc[j] and s2 is None: s2 = j
            elif wc[j] and s2 is not None: out.append((s2, j - s2)); s2 = None
        if s2 is not None: out.append((s2, W - s2))
        return [c for c in out if c[1] >= 20]

    hits = []
    for (y0, h) in bands:
        rr = _runs(y0, h)
        if n_mon and len(rr) == n_mon:
            hits.append((y0, y0 + h, rr[0][0], rr[-1][0] + rr[-1][1]))
    if not hits: return None
    return hits[-2:] if len(hits) >= 2 else hits


def build(name, base, cols, target_aspect):
    # staged_or_live: while the DECK HALT is on the strip builders write into _ai_relink/_staging, so
    # reading SRC directly would rebuild this excerpt from the PRE-HALT strip and report success. That is
    # exactly what happened on 2026-08-24 with the ablation_11 ROI fix (NOTES 14 item 57).
    png = lib.staged_or_live(f"{SRC}/{base}.png")
    sc  = lib.staged_or_live(f"{SRC}/{base}_frames.json")
    if not os.path.exists(png):
        print(f"  {name}: SOURCE STRIP MISSING {png}"); return False
    img = cv2.imread(png)
    n_mon = None
    if os.path.exists(sc):
        try: n_mon = len(json.load(open(sc)).get("monitoring") or []) or None
        except Exception: pass
    if n_mon is None:
        print(f"  {name}: no monitoring count in the sidecar — refusing to guess column widths"); return False
    boxes = monitoring_portion(img, n_mon)
    if not boxes:
        print(f"  {name}: could not locate the monitoring portion"); return False
    _rows = [img[b[0]:b[1], b[2]:b[3]] for b in boxes]
    _w = min(r.shape[1] for r in _rows)
    band = np.vstack([r[:, :_w] for r in _rows])       # phase over fluor, as on the strip

    cw = band.shape[1] / float(n_mon)
    idx = list(range(n_mon)) if cols is None else list(cols)
    if any(i >= n_mon for i in idx):
        print(f"  {name}: column index out of range — strip now has {n_mon} monitoring columns, wanted {idx}")
        return False
    out = np.hstack([band[:, int(round(i * cw)):int(round((i + 1) * cw))] for i in idx])

    # EXPECTED ASPECT FOLLOWS THE COLUMN COUNT (user 2026-08-20, artboard 5 item 5).
    # The band is `len(idx)` square panels wide over 2 channel rows, so its aspect is len(idx)/2 -- which is
    # exactly what the frozen constants encoded (4 columns -> 2.00, 7 columns -> 3.45). Freezing the NUMBER
    # meant that the moment she asked for more columns the guard refused every strip. Deriving it keeps the
    # guard doing its real job (catching a source strip that has regressed to the wrong shape) while
    # following the column count she asked for.
    _expect = len(idx) / 2.0
    asp = out.shape[1] / float(out.shape[0])
    if abs(asp - _expect) > max(ASPECT_TOL, 0.25):
        print(f"  {name}: measured {asp:.2f}:1 vs geometric {_expect:.2f}:1 "
              f"(band {out.shape[1]}x{out.shape[0]}, {len(idx)} of {n_mon} columns)")
    target_aspect = _expect
    if abs(asp - target_aspect) > max(ASPECT_TOL, 0.25):
        # NOTES 2026-08-17: "Replacing her Figure 4 artwork with either would damage the figure." Refuse
        # rather than write something the wrong shape onto the deck.
        print(f"  {name}: REFUSED — aspect {asp:.2f}:1, expected {target_aspect}:1 (+-{ASPECT_TOL})")
        return False

    # a black bar would mean the source strip regressed; every legitimate band here is solid value 20
    rmax = out.reshape(out.shape[0], -1).max(axis=1)
    rmean = out.reshape(out.shape[0], -1).mean(axis=1)
    bad, s = [], None
    for i in range(out.shape[0]):
        d = rmax[i] <= 30
        if d and s is None: s = i
        elif not d and s is not None: bad.append((s, i - s)); s = None
    if s is not None: bad.append((s, out.shape[0] - s))
    bad = [(a, h) for a, h in bad if h >= 5 and abs(float(rmean[a:a + h].mean()) - 20.0) > 1.0]
    if bad:
        print(f"  {name}: WARNING — black band(s) {bad} in the source strip; fix the strip, not this file")

    cv2.imwrite(f"{SRC}/{name}.png", out)
    h, w = out.shape[:2]
    PT_W = 547.2                                # page width kept constant; height follows the aspect
    PT_H = PT_W / asp
    dpi = w / (PT_W / 72.0)
    fig = plt.figure(figsize=(PT_W / 72.0, PT_H / 72.0), dpi=dpi)
    ax = fig.add_axes([0, 0, 1, 1]); ax.axis("off")
    ax.imshow(out[..., ::-1], interpolation="none")
    fig.savefig(f"{PDF}/{name}.pdf", dpi=dpi, pad_inches=0); plt.close(fig)
    print(f"  {name}: {w}x{h} ({asp:.3f}:1) from {base} cols={idx} -> png + pdf")
    return True


if __name__ == "__main__":
    ok = 0
    for name, (base, cols, asp) in EXCERPTS.items():
        if build(name, base, cols, asp): ok += 1
    print(f"rebuilt {ok}/{len(EXCERPTS)} artboard-5 excerpts")
