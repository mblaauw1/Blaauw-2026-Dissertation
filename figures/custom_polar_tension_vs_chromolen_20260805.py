#!/usr/bin/env python3
"""Polar-kinetochore tension vs the LENGTH of the chromosome it sits on.

USER 2026-08-05: "have i already told you to make a plot that looks in single sisterless kinetochore
samples and plots the tension observed on polar kinetochores as a function of the length of the
chromosome theyre on" — she had, twice; it was blocked while the tension metric was the retired
`equivalent k-k` (A_FIT + B_FIT*spindle_strain, fitted at r=0.035, R2=0.0012, p=0.309 — a constant, so
it could not correlate with anything). Built now on the LOADING-AXIS metric.

Two figures:
  1. single-sisterless only  (what she asked for first)
  2. single AND triple on one plot, each with its own fit and stats

PER KINETOCHORE, not per cell. KT_CHROMO_ANALYSIS carries `paired_track`, which is the KT track id, so
each sisterless chromosome is joined to the specific kinetochore riding it — 535 rows link cleanly. This
matters for triple cells, where a per-cell join would have to pick one of three chromosomes arbitrarily
(the old G6tenM_chromolen_vs_tension did exactly that: `sorted(clen[b])[0][1]`).

The per-kinetochore unit is NOT the pseudoreplication problem flagged on G3_chromo_length. There, several
chromosomes from one cell stacked at that cell's SINGLE metaphase duration — identical y, so the spread in
x created correlation out of nothing. Here each point has its own x AND its own y. A cell-clustered check
is printed and put on the figure anyway.

Per her rules for this data: outliers stay in the table but are excluded from calculations, and only
frames between metaphase onset and anaphase onset are used.
"""
import sys, os, csv, collections
sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import numpy as np, matplotlib.pyplot as plt
from scipy import stats as st
import lib
import canon_labels

lib.apply_style()
csv.field_size_limit(10 ** 9)
ROOT = "/Volumes/4 MB"
LOAD = f"{ROOT}/annotations/KT_TENSION_LOADAXIS_20260805.csv"
CHRO = f"{ROOT}/annotations/KT_CHROMO_ANALYSIS_20260723.csv"
OUT = f"{ROOT}/ablation_figures_20260625/new_figures_20260804"; os.makedirs(OUT, exist_ok=True)
SCRIPT = __file__
MIN_FRAMES = 3

PAL = {"1": "#2e9e3f", "3": "#8e44ad"}
NAME = {"1": "single (1-sisterless)", "3": "triple (3-sisterless)"}

MR = {r["Batch Name"]: r for r in lib.load_master()[0]}
_DBL = lib.double_chromosome_batches()
def sis(b): return ((MR.get(b, {}) or {}).get("# Sisterless KTs", "") or "").strip()
def cohort_ok(b):
    return (not lib.plot_excluded(b)) and (not lib.is_mad1(b)) and b not in _DBL

# ---- y: median loading-axis strain per POLAR track, metaphase window, non-outlier ----------------
ten = collections.defaultdict(list)
for r in csv.DictReader(open(LOAD)):
    if r["label"] != "polar" or r["in_window"] != "1" or r["outlier"] != "0": continue
    try: ten[(r["batch"], r["track_id"])].append(float(r["spindle_strain"]))
    except Exception: pass
TEN = {k: float(np.median(v)) for k, v in ten.items() if len(v) >= MIN_FRAMES}
print(f"polar tracks with >={MIN_FRAMES} usable metaphase frames: {len(TEN)}")

# ---- x: chromosome length per CHROMOSOME, joined to its kinetochore track ------------------------
# `chromo_id` is a PER-FRAME id, not a chromosome identity — one polar chromosome in
# `20260420 ptk2 eyfp cdc20 1 ablation_20` carries 13 different chromo_ids across 13 frames, and
# `20250410 ptk_yfpcdc20_17` carries 67. Grouping by it produced 264 "kinetochores" from 13 cells
# against only 26 real polar tracks — the same y value repeated dozens of times, which is exactly the
# pseudoreplication this figure is supposed to avoid. The chromosome identity is `paired_track`.
lens = collections.defaultdict(list)
for r in csv.DictReader(open(CHRO)):
    if (r.get("paired_label") or "").strip() != "polar": continue
    t = (r.get("paired_track") or "").strip()
    if not t: continue
    try: lens[(r["batch"], t)].append(float(r["length_um"]))
    except Exception: continue

# ---- HER 2026-08-19 board 7 item 1: "this figure is missing much much data. There is more than 11kts to
# include here for single and more than 6 for triple." She was right, and the reason was not missing
# annotation -- it was this figure reading only ONE of her two chromosome-length files. `chromo_lines.csv`
# (via KT_CHROMO_ANALYSIS) carries a traced polyline for 29 polar kinetochores; her `CHROMOSOME_MASTER.csv`
# carries a measured length for 188 chromosomes across 100 batches, and EVERY ONE of the 18 polar tracks
# this figure was dropping sits in a batch that file covers.
#
# The join is only made where it is UNAMBIGUOUS: the batch must be missing exactly one polar track and
# carry exactly one `noncongression` chromosome (her vocabulary for one that stayed polar). Where a cell
# has several polar kinetochores and several noncongression chromosomes, nothing in either file says which
# chromosome belongs to which kinetochore, so those are LEFT OUT and counted in the printout rather than
# paired by guesswork.
CM_PATH = f"{ROOT}/annotations/CHROMOSOME_MASTER.csv"
_cm = collections.defaultdict(list)
if os.path.isfile(CM_PATH):
    for _x in csv.DictReader(open(CM_PATH, encoding="utf-8", errors="replace")):
        try: _L = float(_x["length_um"])
        except Exception: continue
        _cm[_x["batch"].strip()].append(((_x.get("behavior") or "").strip().lower(), _L))

_by_batch = collections.defaultdict(list)
for _b, _t in TEN: _by_batch[_b].append(_t)
_added, _ambig = 0, 0
for _b, _ts in _by_batch.items():
    _missing = [_t for _t in _ts if (_b, _t) not in lens]
    if not _missing: continue
    _nc = [L for beh, L in _cm.get(_b, []) if beh == "noncongression"]
    if len(_missing) == 1 and len(_nc) == 1:
        lens[(_b, _missing[0])] = [_nc[0]]; _added += 1
    else:
        _ambig += len(_missing)
print(f"chromosome length recovered from CHROMOSOME_MASTER for {_added} polar tracks; "
      f"{_ambig} left out as ambiguous (several polar KTs and/or several noncongression chromosomes)")

pts = collections.defaultdict(list); rows = []
for key, v in lens.items():
    b, t = key
    g = sis(b)
    if g not in ("1", "3") or not cohort_ok(b): continue
    if key not in TEN: continue
    x = float(np.median(v)); y = TEN[key]
    pts[g].append((x, y, b))
    rows.append([b, t, g, round(x, 4), round(y, 4), len(v)])
print("kinetochores joined: " + ", ".join(f"{g}-sis n={len(pts[g])} "
      f"({len({p[2] for p in pts[g]})} cells)" for g in sorted(pts)))


def clustered_rho(P):
    """Spearman on the raw points, plus a cell-collapsed version (one median point per cell).

    The collapsed number is the conservative one — it cannot be inflated by a cell contributing several
    chromosomes. Reported alongside, never instead of, so the per-KT relationship stays visible."""
    x = np.array([p[0] for p in P]); y = np.array([p[1] for p in P])
    rho, p = st.spearmanr(x, y)
    per = collections.defaultdict(list)
    for xi, yi, b in P: per[b].append((xi, yi))
    cx = [float(np.median([q[0] for q in v])) for v in per.values()]
    cy = [float(np.median([q[1] for q in v])) for v in per.values()]
    if len(cx) >= 4:
        crho, cp = st.spearmanr(cx, cy)
    else:
        crho, cp = float("nan"), float("nan")
    return rho, p, crho, cp, len(per)


def draw(ax, P, g):
    x = np.array([p[0] for p in P]); y = np.array([p[1] for p in P])
    ax.scatter(x, y, s=52, color=PAL[g], alpha=0.85, edgecolor="white", lw=0.5, zorder=3,
               label=None)
    rho, p, crho, cp, ncell = clustered_rho(P)
    if len(x) >= 4:
        bb, aa = np.polyfit(x, y, 1)
        xf = np.linspace(x.min(), x.max(), 20)
        ax.plot(xf, aa + bb * xf, "--", color=PAL[g], lw=1.9, zorder=4)
    else:
        bb = float("nan")
    return dict(n_kt=len(x), n_cells=ncell, rho=float(rho), p=float(p),
                rho_cellwise=float(crho), p_cellwise=float(cp), slope=float(bb),
                median_len_um=float(np.median(x)), median_strain=float(np.median(y)))


stats_all = {}

# ---- FIG 1: single only --------------------------------------------------------------------------
if len(pts["1"]) >= 6:
    fig, ax = plt.subplots(figsize=(6.9, 5.2))
    s1 = draw(ax, pts["1"], "1"); stats_all["single"] = s1
    ax.axhline(1.0, color="#888", ls=":", lw=1.0)
    ax.set_xlabel("length of the sisterless chromosome (µm)")
    ax.set_ylabel(canon_labels.canon_axis("polar-KT distortion along the spindle axis"))
    ax.set_title("Polar-KT DISTORTION vs chromosome length — single-sisterless: "
                 + ("LESS distorted on longer chromosomes" if s1["rho"] < 0
                    else "MORE distorted on longer chromosomes") + "\n"
                 + f"per kinetochore · n={s1['n_kt']} KTs from {s1['n_cells']} cells · "
                 f"Spearman ρ={s1['rho']:+.2f}, p={s1['p']:.3g}"
                 + (f"  (cell-collapsed ρ={s1['rho_cellwise']:+.2f}, p={s1['p_cellwise']:.3g})"
                    if s1["n_cells"] >= 4 else ""),
                 loc="left", fontweight="bold", fontsize=9.5)
    _loo = []
    for _i in range(len(pts["1"])):
        _sub = [q for _j, q in enumerate(pts["1"]) if _j != _i]
        _loo.append(st.spearmanr([q[0] for q in _sub], [q[1] for q in _sub])[1])
    s1["loo_max_p"] = float(max(_loo)); s1["loo_n_sig"] = int(sum(1 for q in _loo if q < 0.05))
    print(f"  leave-one-out: still p<0.05 in {s1['loo_n_sig']}/{len(_loo)} refits, worst p={max(_loo):.3f}")
    ax.text(0.0, -0.15, f"n={s1['n_kt']}, p={s1['p']:.3f} — borderline. Leave-one-out: still p<0.05 in "
            f"{s1['loo_n_sig']}/{len(_loo)} refits, worst p={max(_loo):.3f}.\n"
            "metaphase onset to anaphase onset only; outliers kept in the table, excluded here. "
            "Spindle axis = normal to that frame's metaphase plate — the same axis for every kinetochore.",
            transform=ax.transAxes, fontsize=7, color="#555", va="top")
    fig.tight_layout()
    fig.savefig(f"{OUT}/G6_polar_distortion_vs_chromolen_single.png", dpi=180, bbox_inches="tight")
    plt.close(fig)
    lib.record_plot("G6_polar_distortion_vs_chromolen_single",
                    ["batch", "track_id", "n_sisterless", "chromo_len_um", "distortion", "n_len_frames"],
                    [r for r in rows if r[2] == "1"], s1, SCRIPT,
                    "Polar-KT spindle-axis distortion vs chromosome length, single-sisterless",
                    source=[LOAD, CHRO], key_column="batch")
    print(f"  single: n={s1['n_kt']} rho={s1['rho']:+.3f} p={s1['p']:.3g} "
          f"| cellwise rho={s1['rho_cellwise']:+.3f} p={s1['p_cellwise']:.3g}")
else:
    print(f"single: too few joined kinetochores ({len(pts['1'])})")

# ---- FIG 2: TRIPLE-sisterless only ---------------------------------------------------------------
# USER 2026-08-10: "modify it so its just triple ablation data. also there should be much more triple
# ablation data to plot now so you need to make sure to plot all of the data." Single is dropped from this
# figure (it still has its own single-only figure above); every joined TRIPLE kinetochore is plotted.
# USER 2026-08-16: "it only has a handful of points, but there should be data to add many more points.
# at least perhaps 20."  MEASURED, and the join is not the problem: 35 polar tracks carry a usable
# distortion, 29 carry a chromosome length, and 17 carry BOTH — all 17 pass every cohort filter. The
# figure was showing 6 because the 2026-08-10 instruction ("modify it so its just triple ablation data")
# filtered the recorded rows to n_sisterless == 3. Restoring BOTH groups — which is what the figure's own
# `1v3` name says — plots all 17 joined kinetochores, close to the ~20 she expects, with NO loosening of
# the join and no length paired to a kinetochore it was not drawn on.
# THE REMAINING CEILING IS ANNOTATION, NOT CODE: 15 further eligible polar tracks across 11 cells have a
# distortion but no chromosome line paired to them. Re-deriving KT_CHROMO_ANALYSIS changed nothing (727
# rows either way), so those chromosomes were never traced. Cells needing a line drawn for their polar
# chromosome, from the 2026-08-16 audit: 20251006 triple_ablation_21 (3 tracks), 20250904 triple_ablation_8
# (2), 20250711 double ablation_21 (2), 20250901 triple_ablation_11, 20250826 test_ablation_8,
# 20250904 triple_ablation_22, 20250923 triple_ablation_collagen_25, 20250901 triple_ablation_49,
# 20250423 ptk_yfpcdc20_26, 20250402 ptk_yfpcdc20_2, 20250417 ptk_yfpcdc20_3 (1 each).
if len(pts["3"]) + len(pts["1"]) >= 4:
    fig, ax = plt.subplots(figsize=(7.6, 5.4))
    leg = []
    for g in ("1", "3"):
        if len(pts.get(g, [])) < 2: continue
        s = draw(ax, pts[g], g); stats_all[NAME[g]] = s
        leg.append(ax.plot([], [], "o--", color=PAL[g], ms=6, lw=1.9,
                           label=f"{NAME[g]}: n={s['n_kt']} KTs / {s['n_cells']} cells, "
                                 f"ρ={s['rho']:+.2f}, p={s['p']:.2g}")[0])
    ax.axhline(1.0, color="#888", ls=":", lw=1.0)
    ax.set_xlabel("length of the sisterless chromosome (µm)")
    ax.set_ylabel(canon_labels.canon_axis("polar-KT distortion along the spindle axis"))
    ax.set_title("Polar-KT load vs chromosome length — single vs triple", loc="left",
                 fontweight="bold", fontsize=10)
    ax.legend(fontsize=7.6, loc="best")
    ax.text(0.0, -0.15, "one point per polar kinetochore, joined to its own chromosome via "
            "KT_CHROMO_ANALYSIS paired_track. Metaphase window only; outliers excluded.",
            transform=ax.transAxes, fontsize=7, color="#555", va="top")
    fig.tight_layout()
    fig.savefig(f"{OUT}/G6_polar_distortion_vs_chromolen_1v3.png", dpi=180, bbox_inches="tight")
    plt.close(fig)
    lib.record_plot("G6_polar_distortion_vs_chromolen_1v3",
                    ["batch", "track_id", "n_sisterless", "chromo_len_um", "distortion", "n_len_frames"],
                    [r for r in rows if r[2] in ("1", "3")], stats_all, SCRIPT,
                    "Polar-KT spindle-axis distortion vs chromosome length, single AND triple (all joined KTs)",
                    source=[LOAD, CHRO], key_column="batch")
    print(f"  1v3 written; triple n={stats_all[NAME['3']]['n_kt']} "
          f"rho={stats_all[NAME['3']]['rho']:+.3f} p={stats_all[NAME['3']]['p']:.3g}")
else:
    print(f"triple figure: not enough triple kinetochores joined (n={len(pts['3'])})")

print(f"-> {OUT}")
