#!/usr/bin/env python3
"""Render every frame of a batch with its kt_outlines drawn on, so the frame assignment can be checked by eye.

  python3 verify_outline_frames_20260729.py "<batch name>"

Each panel is one monitoring frame of the 16-bit fluor TIF, read through lib.FluorTif.plane_by_frame -
the SAME call every measurement uses - so what you see is literally the pixels a measurement would read
for an outline on that frame. Outlines are drawn in their traced coordinates, coloured by (label, grp),
with the frame number in the corner. If a trace sat on the wrong frame, the polygon would float off the
kinetochore in its panel and sit on it in a neighbour.

Companion to the 2026-07-29 correlation test (MP4-traced-on vs TIF plane: 97.8% correct at frame-1),
which is statistical; this is the visual check of the same thing.
"""
import sys, os, csv, json, re, collections
sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import lib

csv.field_size_limit(10 ** 9)
BATCH = sys.argv[1] if len(sys.argv) > 1 else "20250402 ptk_yfpcdc20_2"
OUT = "/Volumes/4 MB/_scratch/verify_%s_annotframes_20260729.png" % re.sub(r"\W+", "_", BATCH)

rows = [r for r in csv.DictReader(open("/Volumes/4 MB/annotations/kt_outlines.csv"))
        if r["batch"].strip() == BATCH and r.get("channel") == "fluor"]
if not rows:
    sys.exit("no fluor outlines for %r" % BATCH)


def grp_of(r):
    m = re.search(r"grp:([^;]*)", r.get("notes") or "")
    return (m.group(1).strip() or None) if m else None


byframe = collections.defaultdict(list)
for r in rows:
    try:
        byframe[int(r["frame"])].append(r)
    except Exception:
        pass

keys = sorted({((r.get("label") or "").strip(), grp_of(r)) for r in rows},
              key=lambda t: (t[0], str(t[1])))
cmap = plt.get_cmap("tab10")
COL = {k: cmap(i % 10) for i, k in enumerate(keys)}

ft = lib.FluorTif(BATCH, "monitoring")
if not ft.ok():
    sys.exit("no monitoring fluor TIF for %r" % BATCH)

frames = sorted(byframe)
lo, hi = min(frames), max(frames)
allf = list(range(lo, hi + 1))
ncol = 8
nrow = (len(allf) + ncol - 1) // ncol
fig, axs = plt.subplots(nrow, ncol, figsize=(ncol * 3.4, nrow * 3.4), squeeze=False)
fig.patch.set_facecolor("black")

drawn = 0
for i, f in enumerate(allf):
    ax = axs[i // ncol][i % ncol]
    ax.set_facecolor("black"); ax.set_xticks([]); ax.set_yticks([])
    for s in ax.spines.values():
        s.set_color("#444")
    g = ft.plane_by_frame(f)
    if g is None:
        ax.text(.5, .5, "no plane\nf%d" % f, color="#888", ha="center", va="center", fontsize=6,
                transform=ax.transAxes)
        continue
    v = g.astype(float)
    p1, p2 = np.percentile(v, [20, 99.7])
    ax.imshow(np.clip((v - p1) / (p2 - p1 + 1e-6), 0, 1), cmap="gray", interpolation="nearest")
    for r in byframe.get(f, []):
        try:
            P = np.asarray(json.loads(r["points"]), float)
        except Exception:
            continue
        if P.ndim != 2 or len(P) < 3:
            continue
        Q = np.vstack([P, P[:1]])
        # THIN line, drawn ON the trace path (no offset/inset): the enclosed area PLUS the pixels the
        # line covers is what a measurement uses, so the drawn stroke must sit exactly on the polygon.
        # 0.45 pt ~ 1/3 of the old 1.2 pt, so the kinetochore underneath stays visible.
        ax.plot(Q[:, 0], Q[:, 1], lw=0.45, solid_joinstyle="miter", solid_capstyle="butt",
                color=COL[((r.get("label") or "").strip(), grp_of(r))])
        drawn += 1
    ax.text(.02, .97, "f%d" % f, color="#ffd400", fontsize=6, va="top", transform=ax.transAxes)
for j in range(len(allf), nrow * ncol):
    axs[j // ncol][j % ncol].axis("off")

handles = [plt.Line2D([], [], color=COL[k], lw=2,
                      label="%s grp %s" % (k[0], k[1] if k[1] else "-")) for k in keys]
fig.legend(handles=handles, loc="lower center", ncol=min(len(keys), 6), facecolor="black",
           labelcolor="white", edgecolor="#444", fontsize=8)
fig.suptitle("%s — every monitoring frame with its TRACED kt_outlines overlaid "
             "(plane read via lib.FluorTif.plane_by_frame, the measurement path). "
             "%d outlines over frames %d-%d." % (BATCH, drawn, lo, hi),
             color="white", fontsize=11, x=.01, ha="left")
plt.tight_layout(rect=[0, 0.03, 1, 0.985])
fig.savefig(OUT, dpi=190, facecolor="black", bbox_inches="tight")
plt.close(fig)
ft.close()
print("wrote %s  (%d outlines, %d frames)" % (OUT, drawn, len(allf)))
