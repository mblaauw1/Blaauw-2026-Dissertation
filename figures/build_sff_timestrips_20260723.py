#!/usr/bin/env python3
"""Whole-movie SFF-cropped timestrips for the 5 hand-cropped Mad1 batches (handoff-5 §14).

Uses group_timestrips' own rendering primitives (build_panel -> ts_render.assemble/emit) so the look
matches every other strip. The ONLY difference: the crop window is the fitted SFF square from
annotations/SFF_CROPS_20260723.csv (passed as `crop=` to make_strip, which feeds it straight to
build_panel -> _render_panel -> ts_render.crop_pad), NOT the outline-based tight_square.

Format (NOTES §1.5): ablation portion = fluor-only; monitoring = phase+fluor; uniform scale only.
make_strip's non-aligned path already does exactly that.

Whole movie: one monitoring panel per UNIQUE timepoint (dedup by t_sec -> collapses the z-slice stack
that contaminates xy2/xy6: 47 monitoring frames but 14 real timepoints). mad1_14 also gets its ablation
triples + close-ups via cat_panels.

ANAPHASE CUTOFF (her step 4): all 5 have BLANK Metaphase/Anaphase/NEB/Cytokinesis in the master AND no
anaphase annotation mark, so the anaphase onset is NOT derivable from the data. Rather than fabricate a
cutoff (rules 3/8), the whole movie is rendered and the missing-cutoff is reported for her to place.
Output prefixes carry `_WHOLE_MOVIE` so it is unambiguous these are not yet cut at anaphase+5min.

Output: /Volumes/4 MB/ablation_plots/sff_timestrips_20260723/<batch>_WHOLE_MOVIE.png
"""
import csv, os, sys
sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import group_timestrips as g
import numpy as np

ROOT = "/Volumes/4 MB"
OUT = f"{ROOT}/ablation_plots/sff_timestrips_20260723"
os.makedirs(OUT, exist_ok=True)

SFF = {r["batch"]: r for r in csv.DictReader(open(f"{ROOT}/annotations/SFF_CROPS_20260723.csv"))}


def sff_box(b):
    r = SFF[b]
    return (int(float(r["sff_x0"])), int(float(r["sff_y0"])),
            int(float(r["sff_x1"])), int(float(r["sff_y1"])))


def mon_timepoints(b, max_panels=40):
    """Unique monitoring timepoints (whole movie), z-slices collapsed by t_sec dedup. Show MANY frames
    (user 2026-07-23: 'make the timestrips have many frames; if the movie has few, include them all').
    If more than max_panels, evenly subsample keeping first & last."""
    fj = g.fjson(b)
    ts = sorted({round(f["t_sec"], 1) for f in fj["frames"] if f["role"] == "monitoring"})
    if len(ts) > max_panels:
        idx = np.unique(np.linspace(0, len(ts) - 1, max_panels).astype(int))
        ts = [ts[i] for i in idx]
    return ts


ABL = "20260310 ptk2_eyfp_mad1_14"   # the only one of the 5 with a real ablation movie (62 events)

report = []
for b in SFF:
    box = sff_box(b)
    if b == ABL:
        # ablation triples + close-ups from cat_panels, but swap its 3-frame monitoring for whole-movie
        pan, specs = g.cat_panels(b)
        abl = [p for p in pan if p[0].lower() == "ablation"]
        mon = [("Monitoring", t, None, None) for t in mon_timepoints(b)]
        panels = abl + mon
        title = f"SFF whole-movie timestrip (abl+mon) — {b}   [anaphase cutoff: NOT SET — event times blank]"
        ok = g.make_strip(b, panels, f"{OUT}/{b.replace(' ', '_')}_WHOLE_MOVIE",
                          closeup_specs=specs, crop=box, title=title, do_closeups=True)
    else:
        mon = [("Monitoring", t, None, None) for t in mon_timepoints(b)]
        title = f"SFF whole-movie timestrip (monitoring) — {b}   [anaphase cutoff: NOT SET — event times blank]"
        ok = g.make_strip(b, mon, f"{OUT}/{b.replace(' ', '_')}_WHOLE_MOVIE",
                          crop=box, title=title, do_closeups=False)
    n_mon = len(mon_timepoints(b))
    report.append((b, ok, n_mon, box))
    print(f"  {b}: {'OK' if ok else 'FAIL'}  ({n_mon} monitoring timepoints, SFF side {box[2]-box[0]}px)", flush=True)

print("\n=== SFF timestrip summary ===")
for b, ok, n, box in report:
    print(f"  {'ok ' if ok else 'FAIL'} {b}: {n} mon frames, SFF {box}")
print(f"\nAll anaphase cutoffs UNSET (master event columns blank; no anaphase marks) -> whole movie rendered.")
print(f"Output: {OUT}")
