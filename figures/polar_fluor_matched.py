#!/usr/bin/env python3
"""Polar vs plate-aligned kinetochore FLUORESCENCE, done properly (user 2026-07-28, two corrections):

  1. PER-FRAME CYTOSOL BACKGROUND. The first pass subtracted only a local ring around each outline. Cytosol
     level falls through mitosis (photobleaching), so a ring-only subtraction leaves a time-dependent offset.
     Here every frame gets its own cytosol level from the same image: the median of in-cell pixels between
     the frame's 25th and 90th percentile — above the dark background outside the cell, below the
     kinetochore puncta. KT signal = p95(inside outline) − cytosol(frame).

  2. TIME-MATCHED COMPARISON. A polar KT early in mitosis cannot be compared with a paired KT late in
     mitosis: KT fluorescence falls over metaphase from bleaching AND from kinetochore maturation. So the
     headline test is WITHIN-CELL, WITHIN-FRAME — only frames that carry BOTH a polar and a paired outline
     in the same cell contribute, and they are compared as a PAIRED sample (Wilcoxon signed-rank).

Also plots signal vs time-from-metaphase for both states, so the bleaching/maturation decay is visible
rather than hidden, and re-tests whether intensity tracks area once the cytosol term is removed.
Out-of-focus frames (POLAR_FOCUS_CHECK suspect=yes) are excluded throughout."""
import sys, os, csv, json, glob, collections
sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import numpy as np
from PIL import Image, ImageDraw
import matplotlib.pyplot as plt
from scipy import stats as st
import lib
from kt_landmark_analysis import phase_times
lib.apply_style()
ROOT = "/Volumes/4 MB"; csv.field_size_limit(10 ** 9)
A = f"{ROOT}/annotations"
TMP = f"{ROOT}/_scratch/_focus_frames"
OUT = f"{ROOT}/ablation_figures_20260625/group7_questions"; os.makedirs(OUT, exist_ok=True)
OUTCSV = f"{A}/KT_FLUOR_CYTOSOLNORM_20260728.csv"
C = {"paired": "#3b6fb6", "polar": "#e6820e"}

rows = [r for r in csv.DictReader(open(f"{A}/kt_outlines.csv", newline=""))
        # USER 2026-08-19: "Compare to kinetochores that are congressed, or that can be seen to have
        # merotelic attachments" -- the merotelic group IS the `lagging` label, and it had NEVER been
        # measured: this filter was the only reason 1,511 lagging outline rows carried no intensity at all.
        # Same recipe, same file, one more label; the polar/paired figures this script draws are unchanged
        # because they select their own labels downstream.
        if r["label"] in ("polar", "paired", "lagging") and r["points"] and not lib.focus_excluded(r["id"])]
by_batch = collections.defaultdict(list)
for r in rows:
    d = f"{TMP}/{r['batch'].replace('/', '_')}"
    if os.path.isdir(d):
        by_batch[r["batch"]].append(r)
ph = phase_times(sorted(by_batch))
print(f"{sum(len(v) for v in by_batch.values())} outlines across {len(by_batch)} cells with extracted frames")

cyto_cache = {}
def cytosol(path, im):
    """per-FRAME cytosol level: median of in-cell, non-punctate pixels."""
    if path in cyto_cache:
        return cyto_cache[path]
    lo, hi = np.percentile(im, [25, 90])
    band = im[(im >= lo) & (im <= hi)]
    v = float(np.median(band)) if band.size else float(np.median(im))
    cyto_cache[path] = v
    return v


out = []
for bi, (batch, rs) in enumerate(sorted(by_batch.items()), 1):
    d = f"{TMP}/{batch.replace('/', '_')}"
    mt, at = ph.get(batch, (None, None))
    for r in rs:
        f = int(r["frame"]); p = f"{d}/f{f:04d}.png"
        if not os.path.exists(p):
            continue
        im = np.array(Image.open(p).convert("L")).astype(float)
        pts = json.loads(r["points"])
        m = Image.new("L", im.shape[::-1], 0)
        ImageDraw.Draw(m).polygon([tuple(q) for q in pts], fill=1)
        inside = np.array(m).astype(bool)
        if inside.sum() < 4:
            continue
        cy = cytosol(p, im)
        px = float(r.get("pixel_size_um") or 0.062)
        try: t = float(r["t_sec"])
        except Exception: t = None
        out.append(dict(batch=batch, id=r["id"], label=r["label"], frame=f,
                        t_sec=(round(t, 2) if t is not None else ""),
                        tmeta=(round((t - mt) / 60.0, 3) if (t is not None and mt is not None) else ""),
                        area_um2=round(inside.sum() * px * px, 4),
                        cytosol=round(cy, 2),
                        signal=round(float(np.percentile(im[inside], 95)) - cy, 2),
                        mean_signal=round(float(im[inside].mean()) - cy, 2)))
    if bi % 10 == 0:
        print(f"  [{bi}/{len(by_batch)}]")

with open(OUTCSV, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(out[0].keys())); w.writeheader(); w.writerows(out)
print(f"wrote {len(out)} rows -> {OUTCSV}")

POL = [x for x in out if x["label"] == "polar"]
PAI = [x for x in out if x["label"] == "paired"]

# ── the TIME-MATCHED test: same cell, same frame ─────────────────────────────────────────────────
# This figure's test is specifically POLAR vs PAIRED within a frame, and stays that way. `lagging` is now
# MEASURED into the store above (2026-08-19, for her merotelic comparison) but is not part of this
# comparison, so it is filtered out here rather than being allowed to KeyError into the bucket dict.
byf = collections.defaultdict(lambda: {"polar": [], "paired": []})
for x in out:
    if x["label"] not in ("polar", "paired"):
        continue
    byf[(x["batch"], x["frame"])][x["label"]].append(x)
mp, mq, ap, aq, tt = [], [], [], [], []
for k, v in byf.items():
    if not v["polar"] or not v["paired"]:
        continue
    mp.append(float(np.median([z["signal"] for z in v["polar"]])))
    mq.append(float(np.median([z["signal"] for z in v["paired"]])))
    ap.append(float(np.median([z["area_um2"] for z in v["polar"]])))
    aq.append(float(np.median([z["area_um2"] for z in v["paired"]])))
    t = v["polar"][0]["tmeta"]
    tt.append(float(t) if t != "" else np.nan)
print(f"time-matched frames (a polar AND a paired outline in the same cell+frame): {len(mp)}")

fig, axs = plt.subplots(1, 3, figsize=(15.4, 4.8))

ax = axs[0]
if len(mp) >= 8:
    ws = st.wilcoxon(mp, mq)[1]
    ax.scatter(mq, mp, s=16, color="#7a5cff", alpha=0.45, lw=0)
    lim = [0, max(max(mp), max(mq)) * 1.05]
    ax.plot(lim, lim, "--", color="#666", lw=1.2)
    ax.set_xlim(lim); ax.set_ylim(lim)
    ax.set_xlabel("plate-aligned signal (p95 − cytosol)"); ax.set_ylabel("polar signal (p95 − cytosol)")
    ax.text(0.03, 0.97, f"same cell, SAME FRAME\nn={len(mp)} frames\nWilcoxon p={ws:.2g}\n"
                        f"median polar/paired = {np.median(np.array(mp)/np.maximum(np.array(mq),1e-6)):.2f}×",
            transform=ax.transAxes, va="top", fontsize=8, family="monospace",
            bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="#bbb", alpha=0.9))
    ax.set_title("time-matched: polar vs paired brightness", loc="left", fontweight="bold", fontsize=9.5)
else:
    ax.axis("off"); ax.text(0.5, 0.5, "too few co-occurring frames", ha="center", va="center")

# decay over metaphase, both states
ax = axs[1]
for lab, XS in (("paired", PAI), ("polar", POL)):
    x = np.array([float(v["tmeta"]) for v in XS if v["tmeta"] != ""])
    y = np.array([v["signal"] for v in XS if v["tmeta"] != ""])
    if len(x) < 10: continue
    ax.scatter(x, y, s=4, color=C[lab], alpha=0.13, lw=0)
    bins = np.linspace(np.percentile(x, 2), np.percentile(x, 98), 12); idx = np.digitize(x, bins)
    bx, bm = [], []
    for bi2 in range(1, len(bins)):
        sel = y[idx == bi2]
        if len(sel) >= 5: bx.append((bins[bi2-1]+bins[bi2])/2); bm.append(np.median(sel))
    if bx: ax.plot(bx, bm, "-o", color=C[lab], lw=2.2, ms=3.5)
    rho, pv = st.spearmanr(x, y)
    ax.plot([], [], color=C[lab], lw=2.2, label=f"{lab}: ρ={rho:+.2f}, p={pv:.1g} (n={len(x)})")
ax.axvline(0, ls=":", color="#999")
ax.set_xlabel("minutes from metaphase onset"); ax.set_ylabel("signal (p95 − cytosol)")
ax.legend(fontsize=8); ax.set_title("bleaching / maturation decay", loc="left", fontweight="bold", fontsize=9.5)

# does signal track area now?
ax = axs[2]
for lab, XS in (("paired", PAI), ("polar", POL)):
    x = np.array([v["area_um2"] for v in XS]); y = np.array([v["signal"] for v in XS])
    keep = lib.robust_keep(x, y)
    x, y = x[keep], y[keep]
    ax.scatter(x, y, s=5, color=C[lab], alpha=0.28, lw=0)
    rho, pv = st.spearmanr(x, y)
    b, a = np.polyfit(x, y, 1); xf = np.linspace(x.min(), x.max(), 20)
    ax.plot(xf, a + b*xf, "-", color=C[lab], lw=2.0, label=f"{lab}: ρ={rho:+.2f}, p={pv:.1g} (n={len(x)})")
ax.set_xlabel("outline area (µm²)"); ax.set_ylabel("signal (p95 − cytosol)")
ax.legend(fontsize=8); ax.set_title("does signal track area, cytosol-normalised?", loc="left", fontweight="bold", fontsize=9.5)

fig.suptitle("Polar vs plate-aligned kinetochore fluorescence — per-frame cytosol subtracted, time-matched",
             fontsize=11, fontweight="bold")
fig.tight_layout(); fig.savefig(f"{OUT}/QNEW_fluor_cytosolnorm_timematched.png", dpi=200, bbox_inches="tight")
plt.close(fig)
try: lib.record_plot("QNEW_fluor_cytosolnorm_timematched", ["x"], [], {"family": "questions_20260727"},
                     script=__file__, caption="polar vs paired fluorescence, cytosol-normalised and time-matched",
                     source=[OUTCSV], key_column=None, fig=fig)
except Exception: pass
print("  QNEW_fluor_cytosolnorm_timematched")
