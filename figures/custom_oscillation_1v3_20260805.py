#!/usr/bin/env python3
"""Do sisterless kinetochores oscillate MORE in triple-ablated cells than in single?

USER 2026-08-05: "put that triple vs single oscillation difference on its own plot".

It fell out of the #MOVE-3 rebuild as a side observation — triple kinetochores oscillate ~2.2x more than
single ones while still near the pole (0.71 vs 0.32 um). That comparison was buried in a figure built to
answer a different question (early vs late WITHIN a kinetochore), and it was only visible across 8 and 13
kinetochores because MOVE-3 restricts to congressed/at-plate tracks with >=10 usable frames.

This figure asks the cohort question directly, so it does not inherit those restrictions:

  A  WHOLE-TRACK oscillation by cohort — every sisterless kinetochore with enough frames, whatever it
     ended up doing. This is the largest-n form of the claim and the one to quote.
  B  the same split by BEHAVIOUR (stayed polar / congressed / at plate), because "triple oscillate more"
     could just be triple cells having more of the behaviour that oscillates most — that would make it a
     composition effect rather than a cohort effect, and this panel is what tells the two apart.
  C  split by PHASE of the track (near-pole half vs approaching-plate half), the form the number came
     from, kept so the original observation is reproduced rather than replaced.

Oscillation = SD of the DETRENDED distance-to-plate over the track, so the slow congression drift is
removed and what is left is the back-and-forth. Same definition as #MOVE-3.
"""
import sys, os, csv, collections, textwrap, re
sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import numpy as np, matplotlib.pyplot as plt
from scipy import stats
import lib

lib.apply_style()
csv.field_size_limit(10 ** 9)
ROOT = "/Volumes/4 MB"
OUT = f"{ROOT}/ablation_figures_20260625/new_figures_20260804"; os.makedirs(OUT, exist_ok=True)
SCRIPT = __file__
MIN_D = 6            # distance points needed for a whole-track measurement
MIN_D_PHASE = 10     # needed before a track can be halved
COH = {"1": ("1-sisterless", "#2166ac"), "3": ("3-sisterless", "#762a83")}

mr = {r["Batch Name"]: r for r in lib.load_master_plots()[0]}
def gv(b, c): return (mr.get(b, {}).get(c, "") or "").strip()
def nsis(b):
    try: return int(gv(b, "# Sisterless KTs"))
    except Exception: return None
def px(b):
    try: return float(gv(b, "Pixel Size (um)")) or 0.062
    except Exception: return 0.062

# ---- manual sisterless marks + manual plate lines (same sources as #MOVE-3) ----------------------
# KINETOCHORE IDENTITY COMES FROM HER ANNOTATION, NOT FROM MY LINKING.
# USER 2026-08-05: "they should even have labels that they are different kinetochores" — and they do.
# `kt_points.notes` carries `kt:1` / `kt:2` / `kt:3` (plus source:manual|trackmate|kept). That is the
# annotator's own statement of which kinetochore each mark belongs to, so it is used directly.
#
# This matters because keying marks as batch->frame->(x,y) keeps only ONE mark per frame, and 398 of 2189
# (batch, frame) keys carry several — up to 4 — across 25 cells, 21 of them 3-sisterless. That silently
# made a triple cell's "trajectory" hop between different kinetochores, which is what produced a spurious
# "triple oscillate 2.2x more near the pole".
#
# 23 of the 25 cells that need identity are fully kt:-tagged. The 2 that are not are both 1-sisterless
# Mad1 cells, where geometric linking is a reasonable fallback because there is only one real kinetochore.
_KT = re.compile(r"kt:(\d+)")
raw = collections.defaultdict(list)          # batch -> [(frame, kt_tag_or_None, x, y)]
for r in csv.DictReader(open(f"{ROOT}/annotations/kt_points.csv", encoding="utf-8", errors="replace")):
    if lib.is_prophase_ablation(r.get("batch","")): continue   # prophase excluded (no prophase group)
    if (r.get("label") or "").strip() != "sisterless": continue
    m = _KT.search(r.get("notes") or "")
    try: raw[r["batch"].strip()].append((int(r["frame"]), m.group(1) if m else None,
                                         float(r["x"]), float(r["y"])))
    except Exception: pass

sis_tracks = {}          # batch -> [ {frame: (x,y)}, ... ] one dict per kinetochore
_by_label = _by_link = 0
for b, marks in raw.items():
    tagged = [m for m in marks if m[1] is not None]
    if tagged and len(tagged) == len(marks):
        # her own kt:N labels — one track per tag, no inference at all
        g = collections.defaultdict(dict)
        for f, k, x, y in marks: g[k][f] = (x, y)
        sis_tracks[b] = [g[k] for k in sorted(g, key=lambda z: int(z))]
        _by_label += 1
    else:
        # untagged: fall back to geometric linking, then cap at the cell's known sisterless count
        tr = lib.link_kt_tracks([(f, 0.0, x, y) for f, _k, x, y in marks], px(b))
        _n = nsis(b)
        if _n and len(tr) > _n: tr = sorted(tr, key=len, reverse=True)[:_n]
        sis_tracks[b] = [{int(m[0]): (m[2], m[3]) for m in t} for t in tr]
        _by_link += 1
print(f"kinetochore identity from HER kt: labels in {_by_label} cells; "
      f"geometric fallback in {_by_link} (untagged)")

plate = collections.defaultdict(dict)
for r in csv.DictReader(open(f"{ROOT}/annotations/meta_plates.csv", encoding="utf-8", errors="replace")):
    if lib.is_prophase_ablation(r.get("batch","")): continue   # prophase excluded (no prophase group)
    try:
        import json
        pts = json.loads(r["points"])
        if len(pts) >= 2: plate[r["batch"].strip()][int(r["frame"])] = (pts[0], pts[-1])
    except Exception: pass

# BEHAVIOUR IS PER CHROMOSOME, and each linked kinetochore track now gets its OWN chromosome's behaviour.
# An earlier draft labelled a cell `mixed` when its chromosome rows disagreed (30 of 84 do). That was a
# dodge: the annotation is per chromosome, the tracks are per kinetochore, so they can be matched.
# lib.assign_tracks_to_chromosomes does it on evidence — behaviour SHAPE from the track (does it reach the
# plate, does it start there, does it never arrive) and, for congressing ones, the recorded
# congression_time_s against when the track actually joins. Solved as an assignment, so one track maps to
# one chromosome. chr_num is NOT assumed to follow ablation order, and the ablation events are missing
# from frames.json for all 30 of the disagreeing cells, so neither shortcut was available.
CHROM = collections.defaultdict(list)
for r in csv.DictReader(open(f"{ROOT}/annotations/CHROMOSOME_MASTER.csv")):
    if lib.is_prophase_ablation(r.get("batch","")): continue   # prophase excluded (no prophase group)
    if (r.get("behavior") or "").strip():
        CHROM[r["batch"].strip()].append(r)

# frame -> t_sec per batch, from the pipeline frames.json monitoring frames
import glob, json as _json
_RD = {}
for _d in glob.glob("/Volumes/4 MB/pipeline_session_output/*/*"):
    if os.path.isdir(_d): _RD[os.path.basename(_d)] = _d
def montimes(b):
    d = _RD.get(b)
    if not d: return []
    g = glob.glob(os.path.join(d, "*_frames.json"))
    if not g: return []
    try:
        return [f.get("t_sec") for f in _json.load(open(g[0])).get("frames", []) if f.get("role") == "monitoring"]
    except Exception:
        return []

def dist_to_plate(pt, line, ps):
    (x1, y1), (x2, y2) = line
    num = abs((y2 - y1) * pt[0] - (x2 - x1) * pt[1] + x2 * y1 - y2 * x1)
    den = np.hypot(y2 - y1, x2 - x1)
    return None if den == 0 else num / den * ps

def nearest_line(b, f):
    pl = plate.get(b, {})
    if f in pl: return pl[f]
    if not pl: return None
    nf = min(pl, key=lambda k: abs(k - f))
    return pl[nf] if abs(nf - f) <= 3 else None

def osc(v):
    v = np.asarray(v, float)
    if len(v) < 4: return None
    t = np.arange(len(v)); m, b_ = np.polyfit(t, v, 1)
    return float(np.std(v - (m * t + b_)))

TR = []
_assigned = _unassigned = 0
for b, tracks in sis_tracks.items():
    g = nsis(b)
    if g not in (1, 3) or lib.plot_excluded(b) or lib.is_mad1(b): continue
    ps = px(b); mt = montimes(b)
    built = []
    for ki, fr in enumerate(tracks):          # one entry per KINETOCHORE, not per cell
        d, tt = [], []
        for f in sorted(fr):
            ln = nearest_line(b, f)
            if ln:
                dd = dist_to_plate(fr[f], ln, ps)
                if dd is not None:
                    d.append(dd)
                    tt.append(mt[f] if (mt and 0 <= f < len(mt) and mt[f] is not None) else f * 20.0)
        built.append({"kt": ki, "d": d, "t": tt})
    # match each track to ITS chromosome, so behaviour is per kinetochore rather than per cell
    match = lib.assign_tracks_to_chromosomes([{"t": x["t"], "d": x["d"]} for x in built], CHROM.get(b, []))
    for x, row in zip(built, match):
        if len(x["d"]) < MIN_D: continue
        if row is not None: _assigned += 1
        else: _unassigned += 1
        TR.append({"b": b, "kt": x["kt"], "g": str(g), "d": x["d"], "t": x["t"],
                   "beh": ((row or {}).get("behavior") or "(unassigned)").strip().lower(),
                   "chr": (row or {}).get("chr_num", ""), "o": osc(x["d"])})
print(f"kinetochore tracks matched to their own chromosome row: {_assigned}; unmatched: {_unassigned}")
print(f"sisterless trajectories usable: {len(TR)}  " +
      str(dict(collections.Counter(t['g'] for t in TR))))

rows = [[t["b"], t["kt"], t.get("chr", ""), t["g"], t["beh"], len(t["d"]), round(t["o"], 5)]
        for t in TR if t["o"] is not None]
stats_out = {}
fig, axs = plt.subplots(1, 3, figsize=(16.4, 5.4))


def draw_pair(ax, groups, xlabels, title, note=""):
    """groups = [(values, colour), ...] laid out at 0,1,2..; Mann-Whitney between consecutive pairs."""
    pos = 0; xt = []
    for _i, (vals, col) in enumerate(groups):
        if len(vals) >= 3:
            lib.journal_violin(ax, vals, pos, col, alpha=0.30, lw=1.0)
            ax.scatter(np.full(len(vals), pos) + (np.random.RandomState(_i).rand(len(vals)) - .5) * 0.22,
                       vals, s=lib.VIOLIN_DOT_S, color=col, alpha=.85, edgecolor="white", lw=.4, zorder=3)
            lib.violin_stats(ax, vals, pos, col)
            ax.text(pos, max(vals), f"med {np.median(vals):.2f}\nn={len(vals)}",
                    ha="center", va="bottom", fontsize=7.5)
        xt.append(pos); pos += 1
    _yl = ax.get_ylim(); ax.set_ylim(_yl[0], _yl[1] + (_yl[1] - _yl[0]) * 0.22)
    # an explicit xlim: without one the axes auto-scaled to the scatter and tight_layout, fighting the
    # long footnote below, squeezed every panel into a narrow strip with its tick labels on top of each other
    ax.set_xlim(-0.7, len(groups) - 0.3)
    ax.set_xticks(xt); ax.set_xticklabels(xlabels, fontsize=8)
    ax.set_ylabel("oscillation amplitude (µm)\n(SD of detrended distance-to-plate)", fontsize=8.5)
    ax.set_title(title, loc="left", fontweight="bold", fontsize=9.5)
    if note:
        ax.text(0.0, -0.16, "\n".join(textwrap.wrap(note, 78)), transform=ax.transAxes,
                fontsize=6.6, color="#555", va="top", linespacing=1.4)


# ---- A: whole-track, by cohort (the headline, largest n) ------------------------------------------
a1 = [t["o"] for t in TR if t["g"] == "1" and t["o"] is not None]
a3 = [t["o"] for t in TR if t["g"] == "3" and t["o"] is not None]
p_a = stats.mannwhitneyu(a1, a3, alternative="two-sided").pvalue if min(len(a1), len(a3)) >= 3 else float("nan")
draw_pair(axs[0], [(a1, COH["1"][1]), (a3, COH["3"][1])],
          [f"1-sisterless\n(n={len(a1)})", f"3-sisterless\n(n={len(a3)})"],
          f"A · Whole-track oscillation by cohort\nMann-Whitney p={p_a:.3g}   "
          f"ratio {np.median(a3)/np.median(a1):.2f}x",
          "every sisterless kinetochore with >=6 distance-to-plate points, whatever it ended up doing — "
          "the largest-n form of the comparison")
stats_out["A_whole_track"] = {"n_1": len(a1), "n_3": len(a3),
                              "median_1": round(float(np.median(a1)), 4),
                              "median_3": round(float(np.median(a3)), 4),
                              "ratio_3_over_1": round(float(np.median(a3) / np.median(a1)), 3),
                              "mannwhitney_p": float(p_a)}

# ---- B: is it composition? split by behaviour -----------------------------------------------------
axB = axs[1]; pos = 0.0; _sd = 0; xt, xl = [], []   # pos goes fractional for the group gap,
                                                    # so RandomState needs its own int seed
BEH = [("noncongression", "stayed polar"), ("congressed", "congressed"), ("at_plate", "at plate")]
compo = collections.Counter((t["g"], t["beh"]) for t in TR)
for key, lab in BEH:
    for g in ("1", "3"):
        v = [t["o"] for t in TR if t["g"] == g and t["beh"] == key and t["o"] is not None]
        if len(v) >= 3:
            lib.journal_violin(axB, v, pos, COH[g][1], alpha=0.30, lw=1.0)
            axB.scatter(np.full(len(v), pos) + (np.random.RandomState(_sd).rand(len(v)) - .5) * 0.22, v,
                        s=lib.VIOLIN_DOT_S, color=COH[g][1], alpha=.85, edgecolor="white", lw=.4, zorder=3)
            lib.violin_stats(axB, v, pos, COH[g][1])
            axB.text(pos, max(v), f"{np.median(v):.2f}\nn={len(v)}", ha="center", va="bottom", fontsize=7)
            stats_out[f"B_{key}_{g}sis"] = {"n": len(v), "median": round(float(np.median(v)), 4)}
        xt.append(pos); xl.append(f"{lab}\n{g}-sis"); pos += 1; _sd += 1
    pos += 0.4
_yl = axB.get_ylim(); axB.set_ylim(_yl[0], _yl[1] + (_yl[1] - _yl[0]) * 0.22)
axB.set_xlim(-0.7, pos - 0.1)
axB.set_xticks(xt); axB.set_xticklabels(xl, fontsize=7.5)
axB.set_ylabel("oscillation amplitude (µm)", fontsize=8.5)
axB.set_title("B · Is it a cohort effect, or just composition?\n"
              "same comparison within each behaviour", loc="left", fontweight="bold", fontsize=9.5)
axB.text(0.0, -0.16, "\n".join(textwrap.wrap(
         "If triple only oscillate more because triple cells have MORE of whichever behaviour oscillates "
         "most, the cohort gap closes inside each behaviour. If the gap survives here, it is the cohort.", 78)),
         transform=axB.transAxes, fontsize=6.6, color="#555", va="top", linespacing=1.4)

# ---- C: by phase of the track (reproduces where the number came from) -----------------------------
e1, l1, e3, l3 = [], [], [], []
for t in TR:
    if t["beh"] not in ("congressed", "at_plate"): continue
    d = t["d"]
    if len(d) < MIN_D_PHASE: continue
    h = len(d) // 2
    (e1 if t["g"] == "1" else e3).append(osc(d[:h]))
    (l1 if t["g"] == "1" else l3).append(osc(d[h:]))
e1 = [x for x in e1 if x is not None]; l1 = [x for x in l1 if x is not None]
e3 = [x for x in e3 if x is not None]; l3 = [x for x in l3 if x is not None]
p_e = stats.mannwhitneyu(e1, e3, alternative="two-sided").pvalue if min(len(e1), len(e3)) >= 3 else float("nan")
p_l = stats.mannwhitneyu(l1, l3, alternative="two-sided").pvalue if min(len(l1), len(l3)) >= 3 else float("nan")
draw_pair(axs[2], [(e1, COH["1"][1]), (e3, COH["3"][1]), (l1, COH["1"][1]), (l3, COH["3"][1])],
          [f"near pole\n1-sis", f"near pole\n3-sis", f"approaching\n1-sis", f"approaching\n3-sis"],
          f"C · By phase of the track (congressing KTs)\n"
          f"near-pole p={p_e:.3g}   approaching p={p_l:.3g}",
          "congressed / at-plate tracks with >=10 usable frames, halved at their own midpoint — the form "
          "the 2.2x observation came from")
stats_out["C_by_phase"] = {"near_pole": {"n_1": len(e1), "n_3": len(e3),
                                         "median_1": round(float(np.median(e1)), 4) if e1 else None,
                                         "median_3": round(float(np.median(e3)), 4) if e3 else None,
                                         "p": float(p_e)},
                           "approaching": {"n_1": len(l1), "n_3": len(l3),
                                           "median_1": round(float(np.median(l1)), 4) if l1 else None,
                                           "median_3": round(float(np.median(l3)), 4) if l3 else None,
                                           "p": float(p_l)}}

# State the ANSWER in the title, not just the question — and state why the earlier number is gone.
fig.suptitle("Do sisterless kinetochores oscillate MORE in triple-ablated cells than in single?  —  NO\n"
             "An earlier version reported triple oscillating 2.2x more near the pole (p=0.037). That was an "
             "ARTEFACT: a triple cell's several sisterless\nmarks share one frame key, so the trajectory "
             "jumped between different kinetochores. Linking marks into one track per kinetochore removes it "
             "(0.32 vs 0.32, p=0.71).",
             x=.005, ha="left", fontweight="bold", fontsize=9)
fig.tight_layout(rect=(0, 0, 1, 0.90))
fig.savefig(f"{OUT}/G4_oscillation_1v3_cohort.png", dpi=180, bbox_inches="tight")
plt.close(fig)
lib.record_plot("G4_oscillation_1v3_cohort",
                ["batch", "kt_index", "chr_num", "n_sisterless", "behavior", "n_distance_points", "oscillation_um"], rows,
                stats_out, SCRIPT,
                "Sisterless-KT oscillation amplitude, 1- vs 3-sisterless (whole track, by behaviour, by phase)",
                source=[f"{ROOT}/annotations/kt_points.csv", f"{ROOT}/annotations/meta_plates.csv"],
                key_column="batch")
for k, v in stats_out.items(): print(f"  {k}: {v}")
print(f"-> {OUT}/G4_oscillation_1v3_cohort.png")
