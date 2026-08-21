#!/usr/bin/env python3
"""FOCUS CHECK for the polar (sisterless) kinetochore outlines, and the fluorescence-vs-area comparison.

Why (user 2026-07-27): on 471 some polar outlines jump from bright-and-large to dim-and-small. That is the
kinetochore falling OUT OF FOCUS, not a real shape change, and those frames should be excluded. This script:

  1. measures, for every kt_outline on a cell that has a package fluor movie, the outline's AREA and its
     fluorescence (mean and 95th-pct intensity inside the polygon, minus the local ring background);
  2. flags a frame as SUSPECT out-of-focus when its background-subtracted brightness drops well below the
     track's own running level (robust z on log intensity) — the flag is a HINT, she makes the call;
  3. renders one montage PNG per cell: every outlined frame, outline drawn, labelled with frame / area /
     intensity, suspects boxed in red — so she can eyeball them and mark the frames to drop;
  4. writes POLAR_FOCUS_CHECK_20260727.csv (one row per outline) so the exclusions can be applied later;
  5. plots polar vs plate-aligned (paired) fluorescence and area, to test whether the intensity pattern
     tracks the area pattern.

Montages -> /Volumes/4 MB/_scratch/polar_focus_check_20260727/
"""
import sys, os, csv, json, glob, subprocess, collections, shutil
sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import numpy as np
from PIL import Image, ImageDraw
import matplotlib.pyplot as plt
from scipy import stats as st
import lib
lib.apply_style()
ROOT = "/Volumes/4 MB"; csv.field_size_limit(10 ** 9)
A = f"{ROOT}/annotations"
MONT = f"{ROOT}/_scratch/polar_focus_check_20260727"; os.makedirs(MONT, exist_ok=True)
TMP = f"{ROOT}/_scratch/_focus_frames"; os.makedirs(TMP, exist_ok=True)
OUTCSV = f"{A}/POLAR_FOCUS_CHECK_20260727.csv"
FIGDIR = f"{ROOT}/ablation_figures_20260625/group7_questions"; os.makedirs(FIGDIR, exist_ok=True)

MOVIES = {}
for p in glob.glob(f"{ROOT}/kt_outline_annot_pkgs*/*/mon_fluor.mp4"):
    MOVIES.setdefault(os.path.basename(os.path.dirname(p)), p)

rows = [r for r in csv.DictReader(open(f"{A}/kt_outlines.csv", newline=""))
        if r["label"] in ("polar", "paired", "lagging") and r["batch"] in MOVIES and r["points"]]
by_batch = collections.defaultdict(list)
for r in rows:
    by_batch[r["batch"]].append(r)
print(f"{len(rows)} outlines across {len(by_batch)} cells that have a fluor movie")


def frames_for(batch):
    d = f"{TMP}/{batch.replace('/', '_')}"
    if os.path.isdir(d) and glob.glob(f"{d}/f*.png"):
        return d
    os.makedirs(d, exist_ok=True)
    subprocess.run(["ffmpeg", "-v", "error", "-i", MOVIES[batch], "-vsync", "0", f"{d}/f%04d.png"], check=False)
    return d


def measure(im, pts):
    """mean / p95 inside the polygon, minus the median of a 6-px ring around it."""
    h, w = im.shape
    m = Image.new("L", (w, h), 0); ImageDraw.Draw(m).polygon([tuple(p) for p in pts], fill=1)
    inside = np.array(m).astype(bool)
    if inside.sum() < 4:
        return None
    ring = Image.new("L", (w, h), 0)
    cx = float(np.mean([p[0] for p in pts])); cy = float(np.mean([p[1] for p in pts]))
    grown = [((p[0]-cx)*1.9+cx, (p[1]-cy)*1.9+cy) for p in pts]
    ImageDraw.Draw(ring).polygon(grown, fill=1)
    ring = np.array(ring).astype(bool) & ~inside
    bg = float(np.median(im[ring])) if ring.sum() > 10 else float(np.median(im))
    return float(im[inside].mean() - bg), float(np.percentile(im[inside], 95) - bg), bg, int(inside.sum())


out_rows = []
for bi, (batch, rs) in enumerate(sorted(by_batch.items()), 1):
    d = frames_for(batch)
    per = []
    for r in sorted(rs, key=lambda r: (int(r["frame"]), r["id"])):
        f = int(r["frame"])
        p = f"{d}/f{f:04d}.png"
        if not os.path.exists(p):
            continue
        im = np.array(Image.open(p).convert("L")).astype(float)
        pts = json.loads(r["points"])
        mm = measure(im, pts)
        if mm is None:
            continue
        mean_i, p95_i, bg, npx = mm
        px = float(r.get("pixel_size_um") or 0.062)
        per.append(dict(batch=batch, id=r["id"], label=r["label"], frame=f, t_sec=r["t_sec"],
                        area_um2=round(npx * px * px, 4), mean_int=round(mean_i, 2),
                        p95_int=round(p95_i, 2), bg=round(bg, 2), png=p, points=pts))
    # suspect flag, per label-track within the cell
    for lab in {x["label"] for x in per}:
        sub = [x for x in per if x["label"] == lab]
        v = np.array([max(x["p95_int"], 1.0) for x in sub])
        lv = np.log(v)
        med = np.median(lv); mad = np.median(np.abs(lv - med)) * 1.4826
        for x, z in zip(sub, (lv - med) / (mad if mad > 0 else 1)):
            x["z_intensity"] = round(float(z), 2)
            x["suspect_out_of_focus"] = "yes" if z < -2.0 else ""
    out_rows += per
    print(f"  [{bi}/{len(by_batch)}] {batch}: {len(per)} outlines measured, "
          f"{sum(1 for x in per if x.get('suspect_out_of_focus'))} suspect")

    # montage of the POLAR outlines (the ones 471 is built from)
    pol = [x for x in per if x["label"] == "polar"]
    if not pol:
        continue
    CELL, COLS = 190, 10
    rowsN = int(np.ceil(len(pol) / COLS))
    sheet = Image.new("RGB", (COLS * CELL, rowsN * (CELL + 26)), (12, 12, 12))
    dr = ImageDraw.Draw(sheet)
    for i, x in enumerate(pol):
        im = Image.open(x["png"]).convert("RGB")
        pts = x["points"]
        cx = int(np.mean([p[0] for p in pts])); cy = int(np.mean([p[1] for p in pts]))
        R = 70
        crop = im.crop((cx - R, cy - R, cx + R, cy + R)).resize((CELL, CELL))
        cd = ImageDraw.Draw(crop)
        sc = CELL / (2.0 * R)
        cd.line([(int((p[0] - cx + R) * sc), int((p[1] - cy + R) * sc)) for p in pts] +
                [(int((pts[0][0] - cx + R) * sc), int((pts[0][1] - cy + R) * sc))],
                fill=(255, 90, 90) if x.get("suspect_out_of_focus") else (90, 220, 255), width=2)
        col, row = i % COLS, i // COLS
        sheet.paste(crop, (col * CELL, row * (CELL + 26)))
        lab = f"f{x['frame']}  A={x['area_um2']:.2f}  I={x['p95_int']:.0f}"
        dr.text((col * CELL + 4, row * (CELL + 26) + CELL + 6), lab,
                fill=(255, 120, 120) if x.get("suspect_out_of_focus") else (200, 200, 200))
        if x.get("suspect_out_of_focus"):
            dr.rectangle([col*CELL+1, row*(CELL+26)+1, col*CELL+CELL-2, row*(CELL+26)+CELL-2], outline=(255, 60, 60), width=3)
    sheet.save(f"{MONT}/{batch.replace('/', '_')}__polar_focus.png")

with open(OUTCSV, "w", newline="") as f:
    cols = ["batch", "id", "label", "frame", "t_sec", "area_um2", "mean_int", "p95_int", "bg",
            "z_intensity", "suspect_out_of_focus"]
    w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
    w.writeheader(); w.writerows(out_rows)
nsus = sum(1 for x in out_rows if x.get("suspect_out_of_focus"))
print(f"\nwrote {len(out_rows)} rows ({nsus} suspect out-of-focus) -> {OUTCSV}")
print(f"montages -> {MONT}")

# ── fluorescence vs area, polar vs plate-aligned ─────────────────────────────────────────────────
POL = [x for x in out_rows if x["label"] == "polar"]
PAI = [x for x in out_rows if x["label"] == "paired"]
if len(POL) >= 10 and len(PAI) >= 10:
    fig, axs = plt.subplots(1, 3, figsize=(15.0, 4.6))
    C = {"polar": "#e6820e", "paired": "#3b6fb6"}
    for ax, key, yl in ((axs[0], "p95_int", "fluorescence (95th pct − local bg)"),
                        (axs[1], "area_um2", "outline area (µm²)")):
        g = {"paired": [x[key] for x in PAI], "polar": [x[key] for x in POL]}
        for i, k in enumerate(("paired", "polar")):
            dd = g[k]
            lib.journal_violin(ax, dd, i, C[k], alpha=0.28, lw=1.0, min_n=3)
            ax.scatter(np.full(len(dd), i)+(np.random.RandomState(i).rand(len(dd))-0.5)*0.2, dd,
                       s=lib.VIOLIN_DOT_S, color=C[k], alpha=lib.VIOLIN_DOT_ALPHA_DENSE, lw=0)
            ax.hlines(np.median(dd), i-0.34, i+0.34, color=C[k], lw=2.4)
        ax.set_xticks([0, 1]); ax.set_xticklabels([f"plate-aligned\n(n={len(PAI)})", f"polar\n(n={len(POL)})"], fontsize=9)
        ax.set_ylabel(yl)
        p = st.mannwhitneyu(g["paired"], g["polar"], alternative="two-sided")[1]
        ax.set_title(f"MW p={p:.2g}   med {np.median(g['paired']):.2f} vs {np.median(g['polar']):.2f}",
                     loc="left", fontsize=9)
    ax = axs[2]
    for k, XS in (("paired", PAI), ("polar", POL)):
        x = np.array([v["area_um2"] for v in XS]); y = np.array([v["p95_int"] for v in XS])
        ax.scatter(x, y, s=6, color=C[k], alpha=0.3, lw=0)
        rho, pv = st.spearmanr(x, y)
        b, a = np.polyfit(x, y, 1); xf = np.linspace(x.min(), x.max(), 20)
        ax.plot(xf, a + b*xf, "-", color=C[k], lw=2.0, label=f"{k}: ρ={rho:+.2f}, p={pv:.1g} (n={len(x)})")
    ax.set_xlabel("outline area (µm²)"); ax.set_ylabel("fluorescence (95th pct − local bg)")
    ax.legend(fontsize=8); ax.set_title("does intensity track area?", loc="left", fontsize=9)
    fig.suptitle("Polar vs plate-aligned kinetochore: fluorescence and area", fontsize=11, fontweight="bold")
    fig.tight_layout(); fig.savefig(f"{FIGDIR}/QNEW_fluor_vs_area_polar_vs_paired.png", dpi=200, bbox_inches="tight")
    plt.close(fig)
    try: lib.record_plot("QNEW_fluor_vs_area_polar_vs_paired", ["x"], [], {"family": "questions_20260727"},
                         script=__file__, caption="polar vs plate-aligned fluorescence and area", source=[OUTCSV], key_column=None, fig=fig)
    except Exception: pass
    print("  QNEW_fluor_vs_area_polar_vs_paired")
