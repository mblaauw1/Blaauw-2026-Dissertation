"""Prophase-ablated cells vs prometaphase-ablated triple-sisterless cells: KT movement, and cell shape.

USER 2026-08-08: "we also have new annotations for the set of prophase ablation cells - the three that are
plotted in the violin plot for prophase against prometaphase. look at the paired kinetochore movement
patterns and plot how these movement patterns in the prophase clls compare to the movement patterns in
prometaphase triple sisterless cells. do the same for the circularity and cross-sectional area of the two
groups of cells over time."

COHORTS derived with the VIOLIN'S OWN logic rather than re-specified, so they cannot drift from the figure
(this is the same trap that produced a wrong prophase set on 2026-08-08 and was corrected then):
  prophase   = on-target cdc20, 2-or-3 sisterless, phase_v2 == Prophase, minus the TD_OUTLIER the violin
               hard-excludes. Resolves to exactly the 3 cells she means:
                 20251104 ablations_5 (3-sis) · 20260108 two_sisterless_kinetochores_14 (2-sis) ·
                 20260417 ptk2 eyfp cdc20 ablation_14 (3-sis)
  prometaphase = the same filter but phase_v2 == Prometaphase, restricted to **3-sisterless** because she
               asked specifically for "prometaphase triple sisterless cells".

MOVEMENT uses DRIFT-CORRECTED track coordinates (common-mode removed at source in kt_tracks.py); shape
(circularity, cross-sectional area) comes from her CELL outlines, which are drift-immune anyway because
both are properties of one traced polygon, not a position.

TIME is expressed from METAPHASE START so the two groups are on a common axis; pre-metaphase frames run
negative. NO ANAPHASE (her standing rule).
"""
import sys; sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import os, csv, json, collections, numpy as np, matplotlib.pyplot as plt
import lib
lib.apply_style()
csv.field_size_limit(10 ** 9)

A = "/Volumes/4 MB/annotations/"
OUT = "/Volumes/4 MB/ablation_figures_20260625/group7"; os.makedirs(OUT, exist_ok=True)
SCRIPT = __file__

full, _ = lib.load_master(); MR = {r["Batch Name"]: r for r in full}
coh = lib.assign_cohorts(include_prophase=True)


def nsis(b):
    v = (MR.get(b, {}).get("# Sisterless KTs", "") or "").strip()
    try:
        return int(float(v))
    except Exception:
        return None


def phase_v2(b):
    if lib.is_v2_prometaphase(b):
        return "Prometaphase"
    p = (MR.get(b, {}).get("Phase of Ablations", "") or "").strip().lower()
    return "Prometaphase" if p.startswith("promet") else ("Prophase" if p.startswith("proph") else None)


def ontarget_cdc20(b):
    r = MR.get(b, {}); ct = (r.get("Cell Type", "") or "").lower()
    if "cdc20" not in ct or "hec1" in ct or "mad1" in ct:
        return False
    return (r.get("On-Target / Off-Target", "") or "").strip().lower() == "on-target"


TD_OUTLIER = {"20260107 two_sisterless_kinetochores_3"}
combined = [b for b, v in (coh["2-Sister"] + coh["3-Sister"])
            if ontarget_cdc20(b) and b not in TD_OUTLIER]
PROPHASE = sorted(b for b in combined if phase_v2(b) == "Prophase")
PROMET = sorted(b for b in combined if phase_v2(b) == "Prometaphase" and nsis(b) == 3)
print(f"prophase cells ({len(PROPHASE)}): {PROPHASE}")
print(f"prometaphase 3-sisterless cells: {len(PROMET)}")
GRP = {b: "prophase" for b in PROPHASE}
GRP.update({b: "prometaphase 3-sis" for b in PROMET})
GC = {"prophase": "#1b7837", "prometaphase 3-sis": "#762a83"}
ORDER = ["prophase", "prometaphase 3-sis"]


def win(b):
    return (lib.parse_time(MR.get(b, {}).get("Metaphase Start (s)", "")),
            lib.parse_time(MR.get(b, {}).get("Anaphase Onset (s)", "")))


# ---------- movement: paired KT speed ------------------------------------------------------------
TRK = collections.defaultdict(list)
for r in csv.DictReader(open(A + "KT_OUTLINE_TRACKS_20260723.csv", newline="", encoding="utf-8",
                             errors="replace")):
    b = r["batch"].strip()
    if b in GRP and (r.get("label") or "").strip() == "paired":
        TRK[(b, r["track_id"])].append(r)

speed = collections.defaultdict(list)
mrows = []
for (b, tid), rs in TRK.items():
    ms, ana = win(b)
    ps = float(MR.get(b, {}).get("Pixel Size (um)", "") or 0.062)
    seq = []
    for r in rs:
        try:
            t = float(r["t_sec"])
        except Exception:
            continue
        if ana is not None and t >= ana:
            continue
        seq.append((t, float(r["cx_px"]), float(r["cy_px"])))
    seq.sort()
    sp = [np.hypot(c[1] - a[1], c[2] - a[2]) * ps / (c[0] - a[0])
          for a, c in zip(seq, seq[1:]) if c[0] > a[0]]
    if sp:
        speed[GRP[b]].append(float(np.median(sp)))
        for a, c in zip(seq, seq[1:]):
            if c[0] > a[0]:
                mrows.append([b, GRP[b], tid, f"{c[0]:.2f}",
                              ("" if ms is None else f"{(c[0]-ms)/60.0:.3f}"),
                              f"{np.hypot(c[1]-a[1], c[2]-a[2])*ps/(c[0]-a[0]):.5f}"])
print("paired-speed tracks:", {g: len(v) for g, v in speed.items()})

# ---------- shape: her CELL outlines --------------------------------------------------------------
shape = collections.defaultdict(list)
srows = []
for r in csv.DictReader(open(A + "cell_outlines.csv", newline="", encoding="utf-8", errors="replace")):
    b = (r.get("batch") or "").strip()
    if b not in GRP:
        continue
    ms, ana = win(b)
    try:
        t = float(r["t_sec"])
    except Exception:
        continue
    if ana is not None and t >= ana:
        continue
    # `circularity`/`area_um2` are EMPTY in cell_outlines.csv -- the geometry lives only in `points`.
    # Measure the traced polygon DIRECTLY (shoelace area + polygon perimeter), never by fitting a shape
    # to it, per her standing rule "Never FIT a shape to a manual outline".
    try:
        pts = np.asarray(json.loads(r["points"]), float)
    except Exception:
        continue
    if pts.ndim != 2 or len(pts) < 3:
        continue
    px = float(r.get("pixel_size_um") or 0.062)
    x, y = pts[:, 0] * px, pts[:, 1] * px
    area = float(abs(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1))) / 2.0)
    per = float(np.hypot(np.diff(np.append(x, x[0])), np.diff(np.append(y, y[0]))).sum())
    if area <= 0 or per <= 0:
        continue
    circ = float(4 * np.pi * area / (per * per))
    trel = None if ms is None else (t - ms) / 60.0
    shape[GRP[b]].append((trel, circ, area))
    srows.append([b, GRP[b], f"{t:.2f}", ("" if trel is None else f"{trel:.3f}"),
                  f"{circ:.4f}", f"{area:.3f}"])
print("cell-outline frames:", {g: len(v) for g, v in shape.items()})

# ---------- figure --------------------------------------------------------------------------------
fig, axes = plt.subplots(1, 3, figsize=(14.6, 4.9))
stat_lines = []

# A: paired KT speed
vals = [np.array(speed.get(g, []), float) for g in ORDER]
bp = axes[0].boxplot([v for v in vals], widths=.55, patch_artist=True, showfliers=False,
                     medianprops=dict(color="k", lw=1.4))
for patch, g in zip(bp["boxes"], ORDER):
    patch.set_facecolor(GC[g]); patch.set_alpha(.35); patch.set_edgecolor("k")
rng = np.random.default_rng(0)
for i, (g, v) in enumerate(zip(ORDER, vals), start=1):
    if len(v):
        axes[0].scatter(np.full(len(v), i) + rng.uniform(-.10, .10, len(v)), v, s=26,
                        c=GC[g], edgecolor="k", lw=.4, zorder=3)
axes[0].set_xticks([1, 2])
axes[0].set_xticklabels([f"{g}\nn={len(v)} tracks" for g, v in zip(ORDER, vals)], fontsize=8)
axes[0].set_ylabel("paired KT median speed (um/s)")
axes[0].set_title("Paired kinetochore movement", fontsize=10)
try:
    from scipy import stats as st
    if all(len(v) >= 3 for v in vals):
        p = st.mannwhitneyu(vals[0], vals[1], alternative="two-sided")[1]
        axes[0].text(.5, .98, f"p = {p:.3g}", transform=axes[0].transAxes, ha="center", va="top", fontsize=9)
        stat_lines.append(f"paired KT speed: prophase {np.median(vals[0]):.4f} vs prometa-3sis "
                          f"{np.median(vals[1]):.4f} um/s, p={p:.3g}")
except Exception as e:
    stat_lines.append(f"speed stats failed: {e}")

# B, C: circularity and area over time
for ax, idx, ylab, title in ((axes[1], 1, "cell circularity", "Cell circularity over time"),
                             (axes[2], 2, "cell cross-sectional area (um2)", "Cell area over time")):
    for g in ORDER:
        pts = [(p[0], p[idx]) for p in shape.get(g, []) if p[0] is not None]
        if not pts:
            continue
        pts.sort()
        xs = np.array([p[0] for p in pts]); ys = np.array([p[1] for p in pts])
        ax.scatter(xs, ys, s=13, c=GC[g], alpha=.35, zorder=2)
        edges = np.quantile(xs, np.linspace(0, 1, 6)); edges = np.unique(edges)
        cx, cy, ce = [], [], []
        for i in range(len(edges) - 1):
            m = (xs >= edges[i]) & (xs <= edges[i + 1] if i == len(edges) - 2 else xs < edges[i + 1])
            if m.sum() >= 3:
                cx.append(float(np.median(xs[m]))); cy.append(float(np.median(ys[m])))
                ce.append(float(np.std(ys[m]) / np.sqrt(m.sum())))
        if cx:
            ax.errorbar(cx, cy, yerr=ce, marker="o", color=GC[g], lw=1.9, capsize=3, zorder=3,
                        label=f"{g} (n={len(pts)})")
    ax.axvline(0, color="#444", ls="--", lw=1)
    ax.set_xlabel("time from metaphase start (min)")
    ax.set_ylabel(ylab); ax.set_title(title, fontsize=10)
    ax.legend(frameon=False, fontsize=7)
    try:
        from scipy import stats as st
        a = [p[idx] for p in shape.get(ORDER[0], []) if p[0] is not None]
        b_ = [p[idx] for p in shape.get(ORDER[1], []) if p[0] is not None]
        if len(a) >= 3 and len(b_) >= 3:
            p = st.mannwhitneyu(a, b_, alternative="two-sided")[1]
            stat_lines.append(f"{ylab}: prophase {np.median(a):.3f} vs prometa-3sis {np.median(b_):.3f}, p={p:.3g}")
    except Exception:
        pass

fig.suptitle("Prophase-ablated vs prometaphase-ablated triple-sisterless cells", fontsize=11, y=1.02)
fig.tight_layout()
png = os.path.join(OUT, "G7_prophase_vs_prometaphase_triple.png")
fig.savefig(png, dpi=200, bbox_inches="tight"); plt.close(fig)
print("wrote", png)
for s in stat_lines:
    print("   " + s)

lib.record_plot(
    "G7_prophase_vs_prometaphase_triple",
    ["batch", "group", "track_id", "t_sec", "t_rel_metaphase_min", "speed_um_s"],
    mrows,
    {"kind": "box+timeseries", "anaphase": "excluded", "drift": "common-mode corrected"},
    script=SCRIPT,
    caption=("Paired-kinetochore movement and whole-cell shape in the 3 prophase-ablated cells (the ones "
             "on the prophase-vs-prometaphase violin) versus prometaphase-ablated triple-sisterless cells. "
             "Cohorts derived with the violin's own logic. Speeds drift-corrected; shape from her cell "
             "outlines. Anaphase excluded. " + " | ".join(stat_lines)),
    source=[A + "KT_OUTLINE_TRACKS_20260723.csv", A + "cell_outlines.csv",
            "/Volumes/4 MB/ABLATION_MASTER.csv"],
    key_column="batch", fig=png,
)
with open("/Volumes/4 MB/ablation_plots/data/G7_prophase_vs_prometaphase_shape.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["batch", "group", "t_sec", "t_rel_metaphase_min",
                                   "circularity", "area_um2"]); w.writerows(srows)
print("recorded G7_prophase_vs_prometaphase_triple")
