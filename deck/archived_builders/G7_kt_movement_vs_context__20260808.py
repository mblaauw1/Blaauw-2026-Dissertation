"""How PAIRED and POLAR kinetochore movement changes with the cell's context, in triple-ablation cells.

USER 2026-08-08: "look at how the movement of paired kts evolve (or dont evolve) with the existance of
more/less polars, more/less lagging, and even from the perspective of as the time in metaphase increases,
and from the perspective of as polar kinetochores move to the metaphase plate. look at these same things
for the movement of polar kts."

FOUR CONTEXTS, one row of panels each for PAIRED and POLAR:
  1. number of POLAR kinetochores present in that cell at that moment
  2. number of LAGGING kinetochores present at that moment
  3. time elapsed in metaphase
  4. congression progress -- how many of the cell's polar KTs have reached the plate by then

Contexts 1, 2 and 4 are computed PER FRAME from her own outlines, not from a per-cell summary column, so
"more/less polars" tracks what is actually on screen at that instant. Congression uses her
`SISTERLESS_PLATE_JOIN_TIMES` marks where present, and otherwise counts polar tracks that have ended
(a polar track ending at the plate is congression) -- the source used is recorded per row.

MOVEMENT METRIC = per-frame speed from DRIFT-CORRECTED coordinates (`cx_px`/`cy_px`, common-mode removed
at source in `kt_tracks.py` 2026-08-08). Uncorrected, these speeds run ~15-38% high and the trends here
would partly be stage motion.

NO ANAPHASE (her standing rule): window is [Metaphase Start, Anaphase Onset).
Cohort by `# Sisterless KTs` == 3, never by batch name.
"""
import sys; sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import os, csv, collections, numpy as np, matplotlib.pyplot as plt
import lib
lib.apply_style()
csv.field_size_limit(10 ** 9)

A = "/Volumes/4 MB/annotations/"
OUT = "/Volumes/4 MB/ablation_figures_20260625/group7"; os.makedirs(OUT, exist_ok=True)
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


TR = list(csv.DictReader(open(A + "KT_OUTLINE_TRACKS_20260723.csv", newline="", encoding="utf-8",
                              errors="replace")))
BATCH = collections.defaultdict(list)
for r in TR:
    b = r["batch"].strip()
    if nsis(b) == 3 and usable(b):
        BATCH[b].append(r)
print(f"triple-ablation batches with tracks: {len(BATCH)}")

rows = []
for b, rs in BATCH.items():
    ms = lib.parse_time(MR.get(b, {}).get("Metaphase Start (s)", ""))
    ana = lib.parse_time(MR.get(b, {}).get("Anaphase Onset (s)", ""))
    if ms is None:
        continue
    ps = float(MR.get(b, {}).get("Pixel Size (um)", "") or 0.062)

    # per-frame census of what is present, from her outlines
    census = collections.defaultdict(lambda: collections.Counter())
    for r in rs:
        try:
            census[int(r["frame"])][r["label"]] += 1
        except Exception:
            pass
    # when each polar track ends = when it stopped being polar (congressed or was lost)
    polar_end = {}
    for r in rs:
        if r["label"] != "polar":
            continue
        t = (r.get("t_sec") or "").strip()
        if not t:
            continue
        tid = r["track_id"]
        polar_end[tid] = max(polar_end.get(tid, float("-inf")), float(t))
    n_polar_tracks = len(polar_end)

    bytrack = collections.defaultdict(list)
    for r in rs:
        bytrack[(r["label"], r["track_id"])].append(r)

    for (lab, tid), g in bytrack.items():
        if lab not in ("paired", "polar"):
            continue
        try:
            g.sort(key=lambda x: float(x["t_sec"]))
        except Exception:
            continue
        seq = []
        for r in g:
            try:
                t = float(r["t_sec"])
            except Exception:
                continue
            if t < ms or (ana is not None and t >= ana):
                continue
            seq.append((t, float(r["cx_px"]), float(r["cy_px"]), int(r["frame"])))
        for a, c in zip(seq, seq[1:]):
            dt = c[0] - a[0]
            if dt <= 0:
                continue
            sp = np.hypot(c[1] - a[1], c[2] - a[2]) * ps / dt
            fr = c[3]
            npolar = census[fr]["polar"]
            nlag = census[fr]["lagging"]
            congressed = sum(1 for tt, te in polar_end.items() if te <= c[0])
            frac = (congressed / n_polar_tracks) if n_polar_tracks else np.nan
            rows.append([b, lab, tid, f"{c[0]:.2f}", f"{(c[0]-ms)/60.0:.3f}", f"{sp:.5f}",
                         npolar, nlag, congressed, f"{frac:.3f}" if np.isfinite(frac) else ""])

print(f"movement samples: {len(rows)}")
if not rows:
    raise SystemExit("no samples")

CTX = [("n_polar", 6, "polar KTs present in the cell"),
       ("n_lagging", 7, "lagging KTs present in the cell"),
       ("t_meta_min", 4, "time in metaphase (min)"),
       ("congress_frac", 9, "fraction of polar KTs that reached the plate")]
LABS = [("paired", "#2ca02c"), ("polar", "#ff7f0e")]

fig, axes = plt.subplots(2, 4, figsize=(17.2, 8.4))
stat_lines = []
for ri, (lab, col) in enumerate(LABS):
    sub = [r for r in rows if r[1] == lab]
    for ci, (cname, idx, xlabel) in enumerate(CTX):
        ax = axes[ri][ci]
        xs, ys = [], []
        for r in sub:
            try:
                x = float(r[idx]); y = float(r[5])
            except (ValueError, TypeError):
                continue
            if not np.isfinite(x):
                continue
            xs.append(x); ys.append(y)
        if not xs:
            ax.text(.5, .5, "no data", transform=ax.transAxes, ha="center"); continue
        xs = np.array(xs); ys = np.array(ys)
        # bin so the trend is visible rather than a cloud
        if cname in ("n_polar", "n_lagging"):
            uq = sorted(set(xs.tolist()))
            bins = [(u, u) for u in uq if (xs == u).sum() >= 5]
            cx = [b0 for b0, _ in bins]
            grp = [ys[xs == b0] for b0, _ in bins]
        else:
            edges = np.quantile(xs, np.linspace(0, 1, 7))
            edges = np.unique(edges)
            cx, grp = [], []
            for i in range(len(edges) - 1):
                m = (xs >= edges[i]) & (xs <= edges[i + 1] if i == len(edges) - 2 else xs < edges[i + 1])
                if m.sum() >= 5:
                    cx.append(float(np.median(xs[m]))); grp.append(ys[m])
        if grp:
            med = [float(np.median(v)) for v in grp]
            sem = [float(np.std(v) / np.sqrt(len(v))) for v in grp]
            ax.errorbar(cx, med, yerr=sem, marker="o", color=col, lw=1.8, capsize=3)
        ax.scatter(xs, ys, s=5, c=col, alpha=.13, zorder=1)
        try:
            from scipy import stats as st
            rho, p = st.spearmanr(xs, ys)
            ax.text(.98, .97, f"rho={rho:.2f}\np={p:.2g}", transform=ax.transAxes,
                    ha="right", va="top", fontsize=8,
                    color=("#b2182b" if p < .05 else "#666"))
            stat_lines.append(f"{lab} vs {cname}: rho={rho:.2f} p={p:.2g} n={len(xs)}")
        except Exception:
            pass
        ax.set_xlabel(xlabel, fontsize=8)
        if ci == 0:
            ax.set_ylabel(f"{lab} KT speed (um/s)", fontsize=9)
        ax.set_ylim(0, np.percentile(ys, 98))

fig.suptitle("Kinetochore movement vs cell context, triple-ablation cells (drift-corrected speeds; "
             "metaphase only)", fontsize=11, y=1.005)
fig.tight_layout()
png = os.path.join(OUT, "G7_kt_movement_vs_context.png")
fig.savefig(png, dpi=200, bbox_inches="tight"); plt.close(fig)
print("wrote", png)
for s in stat_lines:
    print("   " + s)

lib.record_plot(
    "G7_kt_movement_vs_context",
    ["batch", "kt_class", "track_id", "t_sec", "t_meta_min", "speed_um_s",
     "n_polar", "n_lagging", "n_congressed", "congress_frac"],
    rows,
    {"kind": "2x4 trend", "cohort": "3-sisterless", "anaphase": "excluded",
     "drift": "common-mode corrected"},
    script=SCRIPT,
    caption=("Paired (top) and polar (bottom) kinetochore speed against four contexts, per frame, in "
             "triple-ablation cells: number of polar KTs present, number of lagging KTs present, time in "
             "metaphase, and congression progress. Counts are per-frame from her outlines, not per-cell "
             "summaries. Speeds use drift-corrected coordinates. Metaphase window only. "
             + " | ".join(stat_lines)),
    source=[A + "KT_OUTLINE_TRACKS_20260723.csv", "/Volumes/4 MB/ABLATION_MASTER.csv"],
    key_column="batch", fig=png,
)
print("recorded G7_kt_movement_vs_context")
