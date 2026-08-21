"""custom_sisterless_fluor_20260722.py — plots-to-make #5.

Sisterless-kinetochore fluorescence right AFTER ABLATION, once it has sat at the POLE for a while, and
right AT ANAPHASE onset — per kinetochore, plus an anaphase-aligned trace for comparison.

Z-DEFOCUS FILTER (user instruction 2026-07-22): a kinetochore's intensity flickers when it moves in and
out of the imaging plane, so the low values are focus artefacts rather than real signal loss. For every
kinetochore we therefore keep only the brighter half of its own timepoints (per-KT median split) — the
mildest filter that removes the out-of-focus dips while sacrificing as few points as possible. Both the
filtered and unfiltered curves are drawn so the effect of the filter is visible, never hidden.

Source: ablation_plots/data/G4_kt_intensity_time.csv (batch, t_min_since_first_abl, kt_fluor_au) — the
recorded data behind G4_kt_intensity_time, so this stays consistent with that figure.

2026-08-03 REBUILD (feedback: "circle back to; could be interesting if three-point: early, polar, polar
at anaphase - with also aligned for comparison."):
  - THREE POINTS PER KINETOCHORE instead of two: early (just after ablation, first 30% of this KT's own
    pre-anaphase span) / polar (settled, the window between "early" and "at anaphase") / polar-at-anaphase
    (within +-8 min of this cell's own Anaphase Onset). "At anaphase" needs a real per-cell anaphase time,
    which needs BOTH master 'First Ablation (s)' and 'Anaphase Onset (s)' to be sane.
  - DATA-QUALITY GATE FOUND DURING THIS REBUILD: 'First Ablation (s)' holds a raw Unix epoch timestamp
    (~1.7e9) for a large fraction of batches instead of a seconds-since-movie-start value -- naively
    subtracting it from 'Anaphase Onset (s)' (a real MM:SS/H:MM:SS clock) produces nonsense multi-decade
    offsets. Any value >100000 (>27h, far past any real relative offset) is treated as epoch junk and
    dropped rather than trusted. Of 44 kinetochores with a usable intensity trace, only 9 have a SANE
    ablation->anaphase offset; of those, 7 have tracked intensity data before their own anaphase (2 tracks
    start after their computed anaphase and are unusable for "early"/"polar"); of those 7, only 3 have a
    genuine gap between the "early" window and the "at anaphase" window to also report a "polar" point.
    This N is reported HONESTLY per stage below rather than padded — see printed N's and figure caption.
    N is too small (3 complete triplets) for a formal paired test; the paired panel is descriptive only.
  - ALIGNED PANEL (new, panel C): the same sane-timing kinetochores' RAW traces, x-axis re-expressed as
    minutes SINCE ANAPHASE ONSET (t=0 = this cell's own anaphase) instead of since first ablation, so every
    cell's anaphase lines up at the same x position -- this is the comparison she asked for: does intensity
    behavior track the TIME-SINCE-ABLATION clock or the TIME-TO-ANAPHASE clock. Panel B (unmodified, vs
    time since first ablation, full N=44) is kept alongside it for that comparison.
"""
import sys; sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import csv, os, numpy as np, matplotlib.pyplot as plt
from collections import defaultdict
from scipy import stats
import lib

OUT4 = "/Volumes/4 MB/ablation_figures_20260625/group4"
SCRIPT = __file__
lib.apply_style()

DATA = "/Volumes/4 MB/ablation_plots/data/G4_kt_intensity_time.csv"
series = defaultdict(list)
for r in csv.DictReader(open(DATA)):
    try:
        series[r["batch"].strip()].append((float(r["t_min_since_first_abl"]), float(r["kt_fluor_au"])))
    except Exception:
        pass
series = {b: sorted(v) for b, v in series.items() if len(v) >= 4 and not lib.plot_excluded(b)}
N_ALL_TRACES = len(series)
print(f"kinetochores with a usable intensity trace: {N_ALL_TRACES}")

data, _ = lib.load_master(); mr = {r["Batch Name"]: r for r in data}
def gv(b, c): return (mr.get(b, {}).get(c, "") or "").strip()

EPOCH_JUNK = 100000.0   # any 'First Ablation (s)'/'Anaphase Onset (s)' this large is a raw epoch stamp, not relative
ANATOL = 8.0            # +-min window counted as "at anaphase"
EARLY_FRAC = 0.30        # first 30% of a KT's own pre-anaphase span = "early"

def infocus(pts):
    """keep the brighter half of THIS kinetochore's own timepoints — the z-defocus screen."""
    if len(pts) < 4:
        return pts
    med = float(np.median([v for _, v in pts]))
    kept = [(t, v) for t, v in pts if v >= med]
    return kept if len(kept) >= 3 else pts

def ana_offset(b):
    """Minutes from first-ablation to anaphase-onset.

    2026-08-09 FIX. This used to compute `Anaphase Onset - First Ablation`, and then throw the batch away
    whenever `First Ablation (s)` looked like a raw Unix epoch -- which discarded 22 of 28 kinetochores and
    left this figure with 2 complete triplets and a ZERO-ROW data CSV while still placed on supplemental.

    The subtraction was never needed: the master's event columns are ALREADY on an ablation=0 clock.
    Verified across the master -- `Ablation->Meta (s)` equals `Metaphase Start (s)` on 125 of 138 rows
    (91%), which is only true if ablation is t0. So anaphase-onset IS the offset from ablation, and
    `First Ablation (s)` (a Unix absolute timestamp, per NOTES section 8) must not enter the arithmetic
    at all.

    Only Anaphase Onset is still epoch-guarded, since a stray absolute stamp there would be real junk.
    """
    ao = lib.parse_time(gv(b, 'Anaphase Onset (s)'))
    if ao is None or ao > EPOCH_JUNK:
        return None
    off = ao / 60.0
    return off if off >= 0 else None

n_epoch_junk = sum(1 for b in series
                   if (lib.parse_time(gv(b, 'Anaphase Onset (s)')) or 0) > EPOCH_JUNK)
sane = {b: ana_offset(b) for b in series if ana_offset(b) is not None}
print(f"kinetochores with a SANE ablation->anaphase offset: {len(sane)}  "
      f"(dropped {n_epoch_junk} with an epoch-timestamp 'Anaphase Onset (s)')")

# ---- three-point extraction, per kinetochore, for the sane-timing subset ----
triplets = []   # (batch, early_med_or_None, polar_med_or_None, ana_med_or_None, n_early,n_polar,n_ana)
aligned_traces = {}   # batch -> [(t_since_ana, val), ...] raw (unfiltered) for panel C
for b, off in sane.items():
    pts = series[b]
    aligned_traces[b] = [(t - off, v) for t, v in pts]
    f = infocus(pts)
    ts = [t for t, _ in f]
    if len(f) < 4:
        continue
    span = off - ts[0]
    if span <= 0:      # this KT's tracked window starts AFTER its own anaphase -> no pre-anaphase data at all
        continue
    e_cut = ts[0] + EARLY_FRAC * span
    early = [v for t, v in f if t <= e_cut]
    ana = [v for t, v in f if abs(t - off) <= ANATOL]
    polar = [v for t, v in f if (t > e_cut) and (t < off - ANATOL)]
    if early or ana:
        triplets.append((b,
                          float(np.median(early)) if early else None,
                          float(np.median(polar)) if polar else None,
                          float(np.median(ana)) if ana else None,
                          len(early), len(polar), len(ana)))

n_early = sum(1 for t in triplets if t[1] is not None)
n_polar = sum(1 for t in triplets if t[2] is not None)
n_ana = sum(1 for t in triplets if t[3] is not None)
n_full = sum(1 for t in triplets if t[1] is not None and t[2] is not None and t[3] is not None)
print(f"3-point stages available: early N={n_early}, polar N={n_polar}, polar-at-anaphase N={n_ana}; "
      f"complete early+polar+ana triplets N={n_full}")

fig, axes = plt.subplots(1, 3, figsize=(16.6, 5.0))

# ---- Panel A: three-point per-kinetochore, early / polar / polar-at-anaphase ----
ax = axes[0]
STAGES = [("early", 0, "#b2182b"), ("polar", 1, "#762a83"), ("ana", 2, "#2166ac")]
for b, e, p, a, ne, npo, na in triplets:
    vals = [e, p, a]
    xs = [i for i, v in enumerate(vals) if v is not None]
    ys = [v for v in vals if v is not None]
    ax.plot(xs, ys, "-", color="#999", lw=.9, alpha=.6, zorder=1)
for key, x, col in STAGES:
    idx = {"early": 1, "polar": 2, "ana": 3}[key]
    v = [t[idx] for t in triplets if t[idx] is not None]
    if v:
        ax.scatter(np.full(len(v), x), v, s=42, color=col, zorder=3, edgecolor="white", lw=.4)
        ax.text(x, max(v) * 1.03 + 1, f"n={len(v)}", ha="center", fontsize=8.5, color=col, fontweight="bold")
ax.set_xticks([0, 1, 2])
ax.set_xticklabels([f"early\n(just after ablation)", f"polar\n(settled, pre-anaphase)",
                     f"polar at anaphase\n(±{ANATOL:.0f} min)"], fontsize=8.5)
ax.set_ylabel("Kinetochore eYFP-Cdc20 (a.u.)")
ax.set_title(f"3-point per-KT, sane-timing subset (N complete triplets={n_full}; descriptive only, N too small\nfor a formal paired test)",
             loc="left", fontweight="bold", fontsize=9)

# ---- Panel B: unmodified population trace vs time-since-first-ablation, filtered vs unfiltered (full N) ----
ax = axes[1]
def binned(getpts, pop):
    xs, ys = [], []
    allp = [p for b in pop for p in getpts(pop[b])]
    if not allp: return xs, ys
    ts = np.array([t for t, _ in allp]); vs = np.array([v for _, v in allp])
    edges = np.arange(0, min(40, ts.max()) + 2, 2.0)
    for i in range(len(edges) - 1):
        m = (ts >= edges[i]) & (ts < edges[i + 1])
        if m.sum() >= 5:
            xs.append(.5 * (edges[i] + edges[i + 1])); ys.append(float(np.median(vs[m])))
    return xs, ys

x0, y0 = binned(lambda p: p, series)
x1, y1 = binned(infocus, series)
if x0: ax.plot(x0, y0, "-o", color="#999", lw=1.6, ms=4, label="all timepoints")
if x1: ax.plot(x1, y1, "-o", color="#762a83", lw=2.2, ms=5, label="in-focus only (brighter half per KT)")
ax.set_xlabel("Minutes since first ablation"); ax.set_ylabel("Kinetochore eYFP-Cdc20 (a.u.)")
ax.set_title(f"Population trace vs time SINCE ABLATION (N={N_ALL_TRACES} KTs)", loc="left", fontweight="bold", fontsize=9)
ax.legend(fontsize=8)

# ---- Panel C (NEW): ALIGNED to anaphase onset -- same sane-timing subset, t=0 = this cell's own anaphase ----
# in-focus-filtered per KT (same z-defocus screen as panels B/A) so one out-of-plane spike doesn't blow up the axis
ax = axes[2]
aligned_infocus = {b: infocus(tr) for b, tr in aligned_traces.items()}
for b, tr in aligned_infocus.items():
    tt = [t for t, _ in tr]; vv = [v for _, v in tr]
    ax.plot(tt, vv, "-", color="#bbb", lw=1.0, alpha=.6, zorder=1)
x2, y2 = binned(lambda p: p, aligned_infocus)
if x2: ax.plot(x2, y2, "-o", color="#b2182b", lw=2.2, ms=5, zorder=3, label="binned median (in-focus)")
ax.axvline(0, color="k", ls="--", lw=1.4, zorder=2)
ax.axvspan(-ANATOL, ANATOL, color="#2166ac", alpha=.08, zorder=0)
ax.set_xlabel(f"Minutes since anaphase onset\n(0 = anaphase; shaded = ±{ANATOL:.0f} min 'at anaphase' window)", fontsize=8.5)
ax.set_ylabel("Kinetochore eYFP-Cdc20 (a.u.)")
ax.set_title(f"ALIGNED to anaphase — sane-timing subset (N={len(aligned_traces)} KTs)\nfor comparison against panel B's ablation-aligned view",
             loc="left", fontweight="bold", fontsize=9)
if x2: ax.legend(fontsize=8)

fig.suptitle("Sisterless-kinetochore fluorescence: early / polar / polar-at-anaphase, ablation-aligned vs anaphase-aligned (plots-to-make #5, rebuilt 2026-08-03)",
             fontweight="bold", fontsize=11, x=.01, ha="left")
plt.tight_layout(rect=[0, 0, 1, .90])
fig.savefig(f"{OUT4}/G4_sisterless_fluor_postabl_vs_pole.png", bbox_inches="tight", dpi=130)
PDF = "/Volumes/4 MB/ablation_figures_20260625/_ai_relink/pdf"
fig.savefig(f"{PDF}/G4_sisterless_fluor_postabl_vs_pole.pdf", bbox_inches="tight")
plt.close(fig)

lib.record_plot("G4_sisterless_fluor_postabl_vs_pole",
                ["batch", "median_early_au", "median_polar_au", "median_polar_at_anaphase_au", "n_early", "n_polar", "n_ana"],
                [[b, e, p, a, ne, npo, na] for b, e, p, a, ne, npo, na in triplets],
                {"N_all_traces": N_ALL_TRACES, "N_sane_anaphase_timing": len(sane), "N_early": n_early,
                 "N_polar": n_polar, "N_ana": n_ana, "N_complete_triplet": n_full,
                 "ana_window_min": ANATOL, "early_frac_of_own_span": EARLY_FRAC,
                 "zfilter": "per-KT median split (brighter half kept)",
                 "data_quality_note": "First Ablation (s) is a raw epoch timestamp for many batches; "
                                       f"values >{EPOCH_JUNK:.0f} dropped as junk ({n_epoch_junk} batches)"},
                SCRIPT,
                "Sisterless KT fluorescence: early / polar / polar-at-anaphase (3-point) + anaphase-aligned trace (plots-to-make #5)")
print(f"#5 rebuilt | full traces N={N_ALL_TRACES}; sane-timing N={len(sane)}; "
      f"3-point stages early={n_early} polar={n_polar} ana={n_ana}; complete triplets={n_full}")
