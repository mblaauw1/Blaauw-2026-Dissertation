"""Does triple-sisterless behaviour APPROACH single-sisterless as its polar chromosomes congress?

USER 2026-08-08: "Does difference in kinetochore movement, k-k, speed at anaphase, oscillation pattern, etc
of 3 sisterless approach that of single with less polar / as more polar congress?"

THE DESIGN. Each metric is plotted for 3-sisterless cells against how far congression has got, with the
SINGLE-sisterless value drawn as a horizontal reference BAND (median +/- IQR). Convergence is then readable
directly: if the 3-sisterless trend moves toward the band as polars disappear, the answer is yes.

Two x-axes, because "less polar" and "as more polar congress" are not the same statement:
  * number of polar KTs still present in the cell at that moment (from her outlines, per frame)
  * fraction of that cell's polar tracks that have already ended (congressed)

ANAPHASE: her standing rule is no anaphase data "unless it specifically calls for it". "Speed at anaphase"
DOES call for it, so that one metric is measured in the anaphase window on purpose and is labelled as such;
every other metric here stays inside [Metaphase Start, Anaphase Onset).

DRIFT: all speeds come from `cx_px`/`cy_px`, which are common-mode corrected at source (kt_tracks.py,
2026-08-08). The stage barely moves, so this is near-identical to raw.
"""
import sys; sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import os, csv, collections, numpy as np, matplotlib.pyplot as plt
import lib
# 2026-08-09: the 2026-08-08 'common mode' stage correction is RETIRED -- the microscope's own
# per-frame XPositionUm/YPositionUm show the stage does not drift during acquisition (1,901 of
# 2,071 source files never move). These plots use HER TRACED coordinates, uncorrected. Measured
# stage offsets, where they exist at all, are available as cx_px_stagecorr in the tracks store.
from kt_oscillation import dominant_period   # same Lomb-Scargle as every other oscillation figure
lib.apply_style()
csv.field_size_limit(10 ** 9)

A = "/Volumes/4 MB/annotations/"
OUT = "/Volumes/4 MB/ablation_figures_20260625/group7"; os.makedirs(OUT, exist_ok=True)
PLOT_ID = "G7_triple_converges_on_single"
SCRIPT = __file__

full, _ = lib.load_master(); MR = {r["Batch Name"]: r for r in full}
_dbl = lib.double_chromosome_batches()


def nsis(b):
    v = (MR.get(b, {}).get("# Sisterless KTs", "") or "").strip()
    try:
        return int(float(v))
    except Exception:
        return None


def usable(b):
    return not (lib.plot_excluded(b) or lib.is_mad1(b) or b in _dbl)


def win(b):
    return (lib.parse_time(MR.get(b, {}).get("Metaphase Start (s)", "")),
            lib.parse_time(MR.get(b, {}).get("Anaphase Onset (s)", "")))


PLATE = {}
for _r in csv.DictReader(open(A + "META_PLATE_NORMALIZED_20260728.csv", newline="", encoding="utf-8",
                              errors="replace")):
    try:
        PLATE[(_r["batch"].strip(), int(_r["frame"]))] = (float(_r["norm_x1"]), float(_r["norm_y1"]),
                                                          float(_r["norm_x2"]), float(_r["norm_y2"]))
    except Exception:
        pass

TR = list(csv.DictReader(open(A + "KT_OUTLINE_TRACKS_20260723.csv", newline="", encoding="utf-8",
                              errors="replace")))
BY = collections.defaultdict(list)
for r in TR:
    b = r["batch"].strip()
    if usable(b) and nsis(b) in (1, 3):
        BY[b].append(r)

# ---- per-batch context: polar census per frame, polar track ends -------------------------------
CTX = {}
for b, rs in BY.items():
    census = collections.defaultdict(collections.Counter)
    for r in rs:
        try:
            census[int(r["frame"])][r["label"]] += 1
        except Exception:
            pass
    pend = {}
    for r in rs:
        if r["label"] != "polar":
            continue
        t = (r.get("t_sec") or "").strip()
        if t:
            pend[r["track_id"]] = max(pend.get(r["track_id"], float("-inf")), float(t))
    CTX[b] = (census, pend, len(pend))

# ---- metric samples ----------------------------------------------------------------------------
# rows: batch, nsis, metric, value, n_polar_now, congress_frac
samples = []
for b, rs in BY.items():
    ms, ana = win(b)
    if ms is None:
        continue
    ps = float(MR.get(b, {}).get("Pixel Size (um)", "") or 0.062)
    census, pend, npt = CTX[b]
    bytrack = collections.defaultdict(list)
    for r in rs:
        bytrack[(r["label"], r["track_id"])].append(r)
    for (lab, tid), g in bytrack.items():
        if lab != "paired":
            continue                      # spindle behaviour read off the aligned population
        seq = []
        for r in g:
            try:
                t = float(r["t_sec"])
            except Exception:
                continue
            seq.append((t, float(r["cx_px"]), float(r["cy_px"]), int(r["frame"])))
        seq.sort()
        for a_, c_ in zip(seq, seq[1:]):
            dt = c_[0] - a_[0]
            if dt <= 0:
                continue
            sp = np.hypot(c_[1] - a_[1], c_[2] - a_[2]) * ps / dt
            in_meta = c_[0] >= ms and (ana is None or c_[0] < ana)
            in_ana = ana is not None and c_[0] >= ana
            npol = census[c_[3]]["polar"]
            frac = (sum(1 for t_ in pend.values() if t_ <= c_[0]) / npt) if npt else np.nan
            if in_meta:
                samples.append([b, nsis(b), "paired KT speed (um/s)", sp, npol, frac])
            elif in_ana:
                # SHE ASKED FOR THIS ONE IN ANAPHASE -- the only metric here that uses anaphase frames
                samples.append([b, nsis(b), "speed at anaphase (um/s)", sp, npol, frac])

        # ---- OSCILLATION, per track, in the metaphase window ----------------------------------
        # She asked for "oscillation pattern" explicitly and the first version of this figure omitted it
        # entirely. Oscillation is measured along HER metaphase-plate normal (drift-immune: both the KT and
        # the plate are her marks in the same frame), with the same Lomb-Scargle period used everywhere
        # else on this project so the numbers are comparable to the other oscillation figures.
        seg = [s for s in seq if s[0] >= ms and (ana is None or s[0] < ana)]
        proj = []
        for (t_, x_, y_, fr_) in seg:
            pl = PLATE.get((b, fr_))
            if pl is None:
                continue
            x1, y1, x2, y2 = pl
            vx, vy = x2 - x1, y2 - y1
            Lp = np.hypot(vx, vy)
            if Lp <= 0:
                continue
            nx, ny = -vy / Lp, vx / Lp
            proj.append((t_, ((x_ - x1) * nx + (y_ - y1) * ny) * ps, fr_))
        if len(proj) >= 6:
            ts = np.array([p[0] for p in proj]); ys = np.array([p[1] for p in proj])
            per_s, _pw = dominant_period(ts, ys)
            det = ys - np.polyval(np.polyfit(ts, ys, 1), ts)      # remove net drift toward/away from plate
            # context is taken at the MIDPOINT of the track's metaphase window, since these are per-track
            mid = proj[len(proj) // 2]
            npol_m = census[mid[2]]["polar"]
            frac_m = (sum(1 for t_ in pend.values() if t_ <= mid[0]) / npt) if npt else np.nan
            if per_s:
                samples.append([b, nsis(b), "oscillation period (s)", float(per_s), npol_m, frac_m])
            samples.append([b, nsis(b), "oscillation amplitude (um)", float(det.std()), npol_m, frac_m])
            # "kinetochore movement" as distinct from instantaneous speed: how far it ranges along the
            # plate normal over its whole metaphase window
            samples.append([b, nsis(b), "movement range along plate normal (um)",
                            float(ys.max() - ys.min()), npol_m, frac_m])

# k-k distance, metaphase only
for r in csv.DictReader(open(A + "KT_SISTER_KK_20260723.csv", newline="", encoding="utf-8",
                             errors="replace")):
    b = r["batch"].strip()
    if b not in BY:
        continue
    ms, ana = win(b)
    if ms is None:
        continue
    try:
        t = float(r["t_sec"]); v = float(r["kk_dist_um"])
    except Exception:
        continue
    if t < ms or (ana is not None and t >= ana):
        continue
    census, pend, npt = CTX[b]
    fr = int(r["frame"]) if str(r.get("frame", "")).strip().isdigit() else None
    npol = census[fr]["polar"] if fr is not None else 0
    frac = (sum(1 for t_ in pend.values() if t_ <= t) / npt) if npt else np.nan
    samples.append([b, nsis(b), "k-k distance (um)", v, npol, frac])

# ONE VALUE PER CELL PER METRIC PER CONTEXT-BIN. 2026-08-09: `samples` holds one row per frame-step, so a
# cell contributing hundreds of steps dominated every test -- the same pseudo-replication that turned noise
# into p=8e-06 in the movement-vs-context figure. Collapse to per-cell medians within each context bin
# before anything is tested or plotted, so the independent unit is the CELL.
_agg = {}
for b, n, m, v, npol, frac in samples:
    fb = round(float(frac), 2) if (frac == frac) else float("nan")
    _agg.setdefault((b, n, m, npol, fb), []).append(v)
samples = [[b, n, m, float(np.median(vals)), npol, fb]
           for (b, n, m, npol, fb), vals in _agg.items()]
print(f"samples after per-cell collapse: {len(samples)} "
      f"(from {sum(len(v) for v in _agg.values())} frame-steps, "
      f"{len({r[0] for r in samples})} cells)")
METRICS = ["paired KT speed (um/s)", "k-k distance (um)", "speed at anaphase (um/s)",
           "oscillation period (s)", "oscillation amplitude (um)",
           "movement range along plate normal (um)"]
for m in METRICS:
    s1 = [x for x in samples if x[2] == m and x[1] == 1]
    s3 = [x for x in samples if x[2] == m and x[1] == 3]
    print(f"   {m:28s} 1-sis n={len(s1):5d}  3-sis n={len(s3):5d}")

# ---- figure: rows = metric, cols = the two x-axes -----------------------------------------------
XAXES = [(4, "polar KTs still present in the cell", True),
         (5, "fraction of polar KTs that have congressed", False)]
fig, axes = plt.subplots(len(METRICS), 2, figsize=(12.4, 4.1 * len(METRICS)))
stat_lines = []
for ri, m in enumerate(METRICS):
    ref = np.array([x[3] for x in samples if x[2] == m and x[1] == 1], float)
    s3 = [x for x in samples if x[2] == m and x[1] == 3]
    for ci, (idx, xlabel, discrete) in enumerate(XAXES):
        ax = axes[ri][ci] if len(METRICS) > 1 else axes[ci]
        if len(ref):
            lo, md, hi = np.percentile(ref, [25, 50, 75])
            ax.axhspan(lo, hi, color="#2166ac", alpha=.15, zorder=0)
            ax.axhline(md, color="#2166ac", lw=1.6, ls="--", zorder=1,
                       label=f"single-sisterless (n={len(ref)})")
        xs = np.array([x[idx] for x in s3], float)
        ys = np.array([x[3] for x in s3], float)
        ok = np.isfinite(xs) & np.isfinite(ys)
        xs, ys = xs[ok], ys[ok]
        if not len(xs):
            ax.text(.5, .5, "no data", transform=ax.transAxes, ha="center"); continue
        ax.scatter(xs, ys, s=6, c="#b2182b", alpha=.12, zorder=2)
        if discrete:
            uq = sorted(set(xs.tolist()))
            cx = [u for u in uq if (xs == u).sum() >= 5]
            grp = [ys[xs == u] for u in cx]
        else:
            edges = np.unique(np.quantile(xs, np.linspace(0, 1, 6)))
            cx, grp = [], []
            for i in range(len(edges) - 1):
                mm = (xs >= edges[i]) & (xs <= edges[i + 1] if i == len(edges) - 2 else xs < edges[i + 1])
                if mm.sum() >= 5:
                    cx.append(float(np.median(xs[mm]))); grp.append(ys[mm])
        if grp:
            md3 = [float(np.median(v)) for v in grp]
            se = [float(np.std(v) / np.sqrt(len(v))) for v in grp]
            ax.errorbar(cx, md3, yerr=se, marker="o", color="#b2182b", lw=2, capsize=3, zorder=3,
                        label="triple-sisterless")
            # does it get CLOSER to the single-sisterless median as polars go away?
            if len(ref) and len(cx) >= 2:
                d0 = abs(md3[0] - md)      # most polar present / least congressed
                d1 = abs(md3[-1] - md)     # fewest polar / most congressed
                if discrete:
                    d0, d1 = abs(md3[-1] - md), abs(md3[0] - md)   # x descends in meaning
                verdict = "converges" if d1 < d0 else "diverges"
                ax.set_title(f"{verdict} ({d0:.3g} -> {d1:.3g} from single)", fontsize=8.5,
                             color=("#1b7837" if verdict == "converges" else "#b2182b"))
                stat_lines.append(f"{m} vs {xlabel}: {verdict} ({d0:.3g} -> {d1:.3g})")
        try:
            from scipy import stats as st
            rho, p = st.spearmanr(xs, ys)
            ax.text(.98, .04, f"rho={rho:.2f} p={p:.2g}", transform=ax.transAxes, ha="right",
                    va="bottom", fontsize=7, color=("#b2182b" if p < .05 else "#666"))
        except Exception:
            pass
        ax.set_xlabel(xlabel, fontsize=8)
        ax.set_ylabel(m, fontsize=8)
        if ri == 0 and ci == 0:
            ax.legend(frameon=False, fontsize=7)
        ax.set_ylim(0, np.percentile(np.concatenate([ys, ref]) if len(ref) else ys, 97))

fig.suptitle("Does triple-sisterless behaviour approach single-sisterless as polar chromosomes congress?\n"
             "(blue band = single-sisterless median +/- IQR)", fontsize=11, y=1.005)
# THE TWO COLUMNS DISAGREE, AND THAT MATTERS -- say so on the figure rather than let the reader assume
# both verdicts are equally solid.
fig.text(.5, -0.012,
         "*** THE converges/diverges LABELS ARE DESCRIPTIVE, NOT STATISTICAL. *** They compare binned\n"
         "medians at the two ends of the axis with NO significance test behind them, over 29 cells spread\n"
         "across the bins. They are unstable: collapsing the data from frame-steps to one value per cell\n"
         "(the correct independent unit) FLIPPED three of the six -- anaphase speed, oscillation period and\n"
         "oscillation amplitude all reversed. Read the trend lines, not the labels.\n"
         "RIGHT column treats 'polar track ended' as congression, which also catches tracks that merely "
         "stopped being annotated — where the two columns disagree, trust the left.\n"
         "Trends are also non-monotonic (e.g. paired speed is closest to single-sisterless at ONE remaining "
         "polar, not zero), so endpoint verdicts are indicative, not conclusive.",
         ha="center", va="top", fontsize=7.5, color="#444")
fig.tight_layout()
png = os.path.join(OUT, PLOT_ID + ".png")
fig.savefig(png, dpi=200, bbox_inches="tight"); plt.close(fig)
print("wrote", png)
for s in stat_lines:
    print("   " + s)

lib.record_plot(
    PLOT_ID, ["batch", "n_sisterless", "metric", "value", "n_polar_now", "congress_frac"],
    [[x[0], x[1], x[2], f"{x[3]:.5f}", x[4], (f"{x[5]:.3f}" if np.isfinite(x[5]) else "")] for x in samples],
    {"kind": "convergence", "reference": "single-sisterless median+IQR", "stage_correction": "none (traced coordinates)"},
    script=SCRIPT,
    caption=("Triple-sisterless metrics plotted against remaining polar count and congression fraction, "
             "with the single-sisterless distribution as a reference band, so convergence is directly "
             "readable. Speeds are from her traced coordinates (uncorrected). Metaphase window except 'speed at anaphase', which she "
             "asked for explicitly and is therefore measured in anaphase. CAVEAT: the two x-axes disagree. "
             "Polar count is a direct per-frame census of her outlines and is the reliable axis; "
             "congression fraction infers congression from a polar track ENDING, which also catches tracks "
             "that merely stopped being annotated. Trends are non-monotonic (paired speed sits closest to "
             "single-sisterless at ONE remaining polar, not zero), so endpoint verdicts are indicative "
             "only. " + " | ".join(stat_lines)),
    source=[A + "KT_OUTLINE_TRACKS_20260723.csv", A + "KT_SISTER_KK_20260723.csv",
            "/Volumes/4 MB/ABLATION_MASTER.csv"],
    key_column="batch", fig=png,
)
print("recorded", PLOT_ID)
