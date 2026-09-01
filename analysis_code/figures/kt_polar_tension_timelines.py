#!/usr/bin/env python3
"""Per-BATCH polar-KT relative-tension TIMELINES (user 2026-07-23).

y = polar KT RELATIVE TENSION (equivalent k-k from the sister-calibrated strain, divided by the paired
metaphase-sister baseline k-k -> dimensionless; 1.0 = a normal bioriented sister's metaphase tension).
x = minutes from METAPHASE ONSET (00:00 = metaphase start for that batch; negative = prometaphase).
One line per batch. On each line:
  * ANAPHASE ONSET  -> filled diamond (from master Anaphase Onset, same t_sec clock).
  * CHROMOSOME CONGRESSION TO THE PLATE -> star, for the batches whose Notes log a plate-join (with time);
    a batch that congresses but has no logged time is drawn with an open star at anaphase + flagged.
Colour = FATE from the user's Notes: stays polar / congresses-to-plate / becomes-lagging.

Calibration mirrors kt_tension.py exactly (metaphase sisters: k-k = a + b*spindle_strain). Mad1_ablation_10
is already dropped upstream (lib.kt_outline_excluded). four_ablation_57 metaphase uses the plate/Ablation->Meta
value (993 s) because its master Metaphase Start (2157 s) is a known mislog (handoff-5 §2).
"""
import sys, os, csv, collections
sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import numpy as np, matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import lib
lib.apply_style()
ROOT = "/Volumes/4 MB"; csv.field_size_limit(10 ** 9)
OUT = f"{ROOT}/ablation_figures_20260625/group6_tracks"
TEN = f"{ROOT}/annotations/KT_TENSION_20260723.csv"
KKF = f"{ROOT}/annotations/KT_SISTER_KK_20260723.csv"
SRC = [TEN, KKF]

# --- FATE + congression from the user's master Notes (handoff-5; reviewed 2026-07-23) ---
# value = logged plate-join time (HH:MM:SS on the same clock as Metaphase/Anaphase) or "" if congresses
# without a logged time. Batches not listed here STAY POLAR (default), except LAGGING below.
CONGRESS = {
    "20250401 ptk_yfpcdc20_28": "0:31:16",
    "20260420 ptk2 eyfp cdc20 1 ablation_13": "0:31:39",
    "20260420 ptk2 eyfp cdc20 1 ablation_30": "",   # "congresses to plate", time not logged
}
LAGGING = {"20250409 ptk_yfpcdc20_6"}               # never joins plate; polar -> midzone -> lagging

FATE_COLOR = {"polar": "#e6820e", "congress": "#2f7fb8", "lagging": "#d1495b"}
FATE_LABEL = {"polar": "stays polar", "congress": "congresses to plate", "lagging": "becomes lagging"}


def fate(b):
    if b in LAGGING: return "lagging"
    if b in CONGRESS: return "congress"
    return "polar"


def load_events(batches):
    # Use phase_times() so the ANTIQUED-master correction (annotation (+0s) times for 20260420 _22/_30, whose
    # master anaphase falls after the movie ends) is applied consistently with the rest of the analysis.
    from kt_landmark_analysis import phase_times
    return phase_times(sorted(batches))


def calibrate(rows):
    """k-k = a + b*strain on METAPHASE sisters (identical to kt_tension.py step 1). Returns (a,b,baseline)."""
    metaframe = {(r["batch"], int(r["frame"])) for r in csv.DictReader(open(KKF)) if r["phase"] == "metaphase"}
    pair = [r for r in rows if r["label"] == "paired" and r["pair_kk_um"] not in ("", None)
            and (r["batch"], int(r["frame"])) in metaframe]
    byf = collections.defaultdict(list)
    for r in pair:
        byf[(r["batch"], int(r["frame"]))].append(float(r["spindle_strain"]))
    X, Y = [], []
    for key, ss in byf.items():
        X.append(np.mean(ss))
        Y.append(next(float(r["pair_kk_um"]) for r in pair if (r["batch"], int(r["frame"])) == key))
    b_fit, a_fit = np.polyfit(X, Y, 1)
    baseline = float(np.median(Y))   # paired metaphase actual k-k
    return a_fit, b_fit, baseline


def series(rows, a, b, baseline, ev):
    """Per-batch sorted (x_min, rel_tension) for polar tracks, plus x of anaphase / congression."""
    pol = collections.defaultdict(list)
    for r in rows:
        if r["label"] != "polar":
            continue
        try:
            t = float(r["t_sec"]); strain = float(r["spindle_strain"])
        except Exception:
            continue
        pol[r["batch"]].append((t, (a + b * strain) / baseline))
    out = {}
    for bch, pts in pol.items():
        meta = ev.get(bch, (None, None))[0]
        ana = ev.get(bch, (None, None))[1]
        if meta is None:
            continue
        pts = sorted(pts)
        xs = [(t - meta) / 60.0 for t, _ in pts]
        ys = [y for _, y in pts]
        x_ana = (ana - meta) / 60.0 if ana is not None else None
        cong = CONGRESS.get(bch)
        x_cong = None
        if cong not in (None,):           # batch congresses
            if cong:                      # has a logged time
                cs = lib.parse_time(cong)
                x_cong = (cs - meta) / 60.0 if cs is not None else None
            else:                         # congresses, no logged time -> mark at anaphase (open star)
                x_cong = x_ana
        out[bch] = dict(xs=xs, ys=ys, x_ana=x_ana, x_cong=x_cong,
                        cong_logged=(bch in CONGRESS and bool(CONGRESS[bch])), fate=fate(bch))
    return out


def interp_y(xs, ys, x):
    if x is None or not xs:
        return None
    xs = np.asarray(xs, float); ys = np.asarray(ys, float)
    if x <= xs[0]: return float(ys[0])
    if x >= xs[-1]: return float(ys[-1])
    return float(np.interp(x, xs, ys))


def _save(fig, name, cap):
    fig.savefig(f"{OUT}/{name}.png", dpi=200, bbox_inches="tight"); plt.close(fig)
    try:
        lib.record_plot(name, ["x"], [], {"family": "tension"}, script=__file__, caption=cap,
                        source=SRC, key_column=None, fig=fig)
    except Exception:
        pass
    print("  " + name)


def short(b):
    return b.replace("ptk2 eyfp cdc20 1 ", "").replace("ptk_yfpcdc20_", "yfp_").replace(" ptk", " ")


def main():
    rows = list(csv.DictReader(open(TEN)))
    ev = load_events({r["batch"] for r in rows})
    a, b, baseline = calibrate(rows)
    S = series(rows, a, b, baseline, ev)
    print(f"calibration k-k = {a:.2f} + {b:.3f}*strain ; baseline paired metaphase k-k = {baseline:.2f} um")
    print(f"{len(S)} polar batches plotted")

    # ---------- 1) OVERLAY, coloured by fate ----------
    fig, ax = plt.subplots(figsize=(9.2, 6.0))
    for bch, s in sorted(S.items()):
        c = FATE_COLOR[s["fate"]]
        ax.plot(s["xs"], s["ys"], "-", color=c, lw=1.3, alpha=0.75)
        ya = interp_y(s["xs"], s["ys"], s["x_ana"])
        if ya is not None:
            ax.plot(s["x_ana"], ya, marker="D", color=c, ms=6, mec="white", mew=0.6, zorder=5)
        if s["x_cong"] is not None:
            yc = interp_y(s["xs"], s["ys"], s["x_cong"])
            ax.plot(s["x_cong"], yc, marker="*", color=c, ms=15,
                    mec="white", mew=0.7, fillstyle=("full" if s["cong_logged"] else "none"), zorder=6)
    ax.axhline(1.0, ls=":", color="#888", lw=1)
    ax.axvline(0, ls="--", color="#444", lw=1)
    ax.text(0.1, ax.get_ylim()[1], "metaphase\nonset", fontsize=7, va="top", color="#444")
    ax.set_xlabel("time from metaphase onset (min)")
    ax.set_ylabel("polar KT relative tension  (× paired metaphase sister)")
    ax.set_title("Polar-KT relative tension over time, per cell", loc="left", fontweight="bold", fontsize=12)
    leg = [Line2D([0], [0], color=FATE_COLOR[k], lw=2, label=FATE_LABEL[k]) for k in FATE_COLOR]
    leg += [Line2D([0], [0], marker="D", color="#444", lw=0, label="anaphase onset", mfc="#444", ms=6),
            Line2D([0], [0], marker="*", color="#444", lw=0, label="congression to plate (logged)", mfc="#444", ms=12),
            Line2D([0], [0], marker="*", color="#444", lw=0, label="congression (time not logged)", mfc="none", ms=12)]
    ax.legend(handles=leg, fontsize=8, loc="upper left", framealpha=0.9)
    _save(fig, "G6ten_polar_tension_timelines", "polar relative tension timelines (overlay, by fate)")

    # ---------- 2) SMALL MULTIPLES, one batch per panel ----------
    items = sorted(S.items())
    n = len(items); ncol = 4; nrow = int(np.ceil(n / ncol))
    fig, axes = plt.subplots(nrow, ncol, figsize=(ncol * 3.1, nrow * 2.2), sharex=False)
    axes = np.atleast_1d(axes).ravel()
    ymax = max((max(s["ys"]) for _, s in items if s["ys"]), default=2)
    for ax, (bch, s) in zip(axes, items):
        c = FATE_COLOR[s["fate"]]
        ax.plot(s["xs"], s["ys"], "-o", color=c, lw=1.2, ms=2.5)
        ax.axhline(1.0, ls=":", color="#aaa", lw=0.8)
        ax.axvline(0, ls="--", color="#444", lw=0.8)
        if s["x_ana"] is not None:
            ax.axvline(s["x_ana"], ls="-", color="#333", lw=0.9)
            ax.text(s["x_ana"], ymax * 1.02, "ana", fontsize=6, ha="center", va="bottom", color="#333")
        if s["x_cong"] is not None:
            ax.axvline(s["x_cong"], ls=":", color=FATE_COLOR["congress"], lw=1.4)
            ax.text(s["x_cong"], ymax * 1.02, "cong" + ("" if s["cong_logged"] else "?"),
                    fontsize=6, ha="center", va="bottom", color=FATE_COLOR["congress"])
        ax.set_ylim(0, ymax * 1.15)
        ax.set_title(f"{short(bch)}\n[{FATE_LABEL[s['fate']]}]", fontsize=6.8, loc="left")
        ax.tick_params(labelsize=6)
    for ax in axes[n:]:
        ax.axis("off")
    fig.supxlabel("time from metaphase onset (min)", fontsize=9)
    fig.supylabel("polar KT relative tension (× paired metaphase sister)", fontsize=9)
    fig.suptitle("Polar-KT relative tension per cell (anaphase + congression marked)",
                 fontweight="bold", fontsize=12, x=0.01, ha="left")
    fig.tight_layout(rect=(0.02, 0.02, 1, 0.98))
    _save(fig, "G6ten_polar_tension_timelines_grid", "polar relative tension timelines (per-cell grid)")


if __name__ == "__main__":
    main()
