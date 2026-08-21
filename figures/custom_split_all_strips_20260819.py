#!/usr/bin/env python3
"""Split EVERY timestrip placed on the live decks into independently movable pieces.

USER 2026-08-19 (to-do list 0819 1pm), all-figures item 2 — verbatim:
    "I've already told you in feedback prior to this that timestrips throughout the main and supplemental
     boards need to be broken apart into independently manipulatable ablation and monitoring timestrips so
     I can manipulate their placement independently on the boards so i can add the needed labeling to each.
     You need to implement this feedback on every applicable timestrip in the 5 files. You did not do this,
     as you did not do much of the feedback prior to this. Unacceptable. You are wasting my time."

WHY THE EARLIER PASS MISSED MOST OF THEM
    `custom_split_strip_pieces_20260817.py` takes a NAME PREFIX (`nf9_` / `nf10_`) and only ever looks in
    `group1/timestrips2`. That covered 22 strips. The decks carry 64 timestrip-like figures, and the other
    42 -- every `G5_mad1_*_aligned`, `G9_drug_*_aligned`, `G3_slippage_*`, `G4_polar_timestrip_*`, the
    `*_aligned` category strips and the AB5 excerpts -- are rendered by different builders into `group4/`
    and `group1/`, so the prefix scan never saw them. This driver works from the DECKS instead: it takes the
    list of figures actually placed on the five live decks (plus the two publication copies), finds each
    one's source raster wherever it lives, and splits it.

HOW THE CUT IS FOUND is unchanged and is imported, not reimplemented: `rows_of_gap` from the 2026-08-17
splitter, which segments on the WHITE PAGE rows that matplotlib leaves between portions and falls back to
the renderer's own value-20 gap band. Splitting on the renderer's own separator is what makes the cut land
on a real portion boundary rather than a guessed pixel row.

The combined `<name>.pdf` is never touched -- several decks and her hand-arranged paper figures link it.
Pieces are ADDED beside it as `<name>__pieceN`.
"""
import glob
import io
import os
import runpy
import sys

import numpy as np
import cv2
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import lib

lib.apply_style()

ROOT = "/Volumes/4 MB"
FIG = f"{ROOT}/ablation_figures_20260625"
PDF = f"{FIG}/_ai_relink/pdf"
DUMPS = f"{ROOT}/_claude_tmp"
# every directory a strip raster is written to, in search order
SRC_DIRS = [f"{FIG}/group1/timestrips2", f"{FIG}/group4", f"{FIG}/group1",
            f"{FIG}/group5", f"{FIG}/custom_collagen_vs_triple"]
DECKS = ["0814", "0813supp", "newfig", "supp", "newts", "pub0814", "pub0813"]

TS_HINT = ("timestrip", "_aligned", "contact", "_strip", "excerpt")


def rows_of_gap(img, val=20, tol=6):
    """WHITE-PAGE FIRST, then the renderer's value-20 gap band. Copied deliberately from
    custom_split_strip_pieces_20260817.py so this driver has no import side effects (that module splits at
    import time); the two must stay identical -- if one changes, change both."""
    white = (img.min(axis=(1, 2)) >= 250)
    bands, start = [], None
    for i, v in enumerate(white):
        if v and start is None: start = i
        elif not v and start is not None:
            if i - start >= 4: bands.append((start, i))
            start = None
    if start is not None and len(white) - start >= 4: bands.append((start, len(white)))
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


def placed_figures():
    """Every figure name placed on any live deck, from the read-only geometry dumps."""
    names = set()
    for tag in DECKS:
        p = f"{DUMPS}/geom9_{tag}.tsv"
        if not os.path.exists(p):
            print(f"  (no dump for {tag} -- run DUMP_ALL9_20260817.jsx)"); continue
        for ln in io.open(p, encoding="utf-8", errors="replace").read().replace("\r", "\n").split("\n"):
            f = ln.split("\t")
            if len(f) > 11 and f[0] == "PlacedItem" and f[5]:
                n = f[5]
                # A strip that has ALREADY been split is placed as `<base>__pieceN`, so its PARENT no longer
                # appears on any deck. Reading only the literal placed names therefore stopped finding the
                # strips on a second run -- the 2026-08-19 zoom change re-split 1 strip instead of 57.
                # Recover the base name so a re-render always reaches every strip that is on a deck.
                if "__piece" in n:
                    n = n.split("__piece")[0]
                names.add(n)
    return names


def is_timestrip(name):
    n = name.lower()
    return n.startswith("nf9_") or n.startswith("nf10_") or any(h in n for h in TS_HINT)


def source_raster(name):
    for d in SRC_DIRS:
        p = f"{d}/{name}.png"
        if os.path.exists(p): return p
    return None


def split_one(name, src, dry=False):
    img = cv2.imread(src)
    if img is None:
        return 0, "unreadable"
    outdir = os.path.dirname(src)
    # 🔴 2026-08-21: this used to delete `{PDF}/*__piece*.pdf` UNCONDITIONALLY. Under PUB=1 the savefig
    # wrapper writes the publication twin only, so a PUB run deleted the WORKING library's piece PDFs and
    # never rewrote them -- 223 placed pieces on the four working decks became broken links, silently,
    # because the publication decks (which link pdf_pub) still resolved. Clean only the library this run
    # will actually rewrite.
    # 🔴 2026-08-21b: cleaning only ONE library was still wrong. `lib.apply_style()`'s savefig wrapper
    # mirrors every piece into BOTH `_ai_relink/pdf` AND `_ai_relink/pdf_pub`, so a non-PUB run that
    # produced FEWER pieces than a previous run deleted the surplus from `pdf/` and left it in `pdf_pub/`.
    # The publication decks link `pdf_pub`, so they went on resolving three stale 08-17 pieces of
    # `nf9_3-sisterless__20260417...` -- one of them blank, one a runt that had been scaled 11.6x on the
    # board to hide that it was a fragment. Clean BOTH libraries; the writer writes both.
    _clean = [PDF, f"{PDF}_pub"]
    _olds = glob.glob(f"{outdir}/{name}__piece*.png")
    for _d in _clean:
        _olds += glob.glob(f"{_d}/{name}__piece*.pdf")
    for old in _olds:
        if not dry:
            try: os.remove(old)
            except OSError: pass
    bands = rows_of_gap(img)
    if not bands:
        return 0, "no gap bands (single portion)"
    cuts = [0] + [(a + b) // 2 for a, b in bands] + [img.shape[0]]
    pieces = [img[cuts[i]:cuts[i + 1]] for i in range(len(cuts) - 1)]
    pieces = [q for q in pieces if q.shape[0] > 40]
    if len(pieces) < 2:
        return 0, "only one usable piece"
    if dry:
        return len(pieces), "ok (dry)"
    for n, q in enumerate(pieces, 1):
        pname = f"{name}__piece{n}"
        h, w = q.shape[:2]; dpi = 200.0
        fig = plt.figure(figsize=(w / dpi, h / dpi), dpi=dpi)
        ax = fig.add_axes([0, 0, 1, 1]); ax.axis("off")
        ax.imshow(q[..., ::-1], interpolation="none")
        # lib.apply_style()'s savefig wrapper mirrors the PNG to _ai_relink/pdf AND the publication twin
        fig.savefig(f"{outdir}/{pname}.png", dpi=dpi, pad_inches=0)
        plt.close(fig)
    return len(pieces), "ok"


def main():
    dry = "--dry-run" in sys.argv
    only = next((a for a in sys.argv[1:] if not a.startswith("-")), None)
    names = sorted(n for n in placed_figures() if is_timestrip(n) and "__piece" not in n)
    if only:
        names = [n for n in names if only in n]
    print(f"{len(names)} timestrip figures placed on the decks")
    made = split = skipped = missing = 0
    for n in names:
        src = source_raster(n)
        if not src:
            missing += 1
            print(f"  MISSING RASTER  {n}")
            continue
        k, why = split_one(n, src, dry)
        if k:
            split += 1; made += k
            print(f"  {k:2d} pieces  {n}")
        else:
            skipped += 1
            print(f"      skip    {n}  ({why})")
    print(f"\nsplit {split} strips into {made} pieces | {skipped} single-portion | {missing} raster not found")


if __name__ == "__main__":
    main()
