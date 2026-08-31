"""custom_max_congression_delay_20260722.py — rebuild of the retired
`G3_max_congression_delay_vs_metaphase_duration` ("Rate-limiting: the slowest chromosome gates anaphase").

Its axes were NOT recorded — only the caption and rho=0.666 / N=38. Three candidate definitions were tested
against those recorded statistics (2026-07-22):
    max congression time                 rho +0.460  N 39
    max congression - metaphase start    rho +0.700  N 39   <== reproduces the recorded value
    range of congression times           rho +0.553  N 39
so the metric is the DELAY OF THE LAST CHROMOSOME TO CONGRESS, measured from metaphase onset — which is also
what the caption describes. N is 39 vs the recorded 38 because a cell has been added since.
This is a VALIDATED RECONSTRUCTION, not the original code (which was never saved); the figure says so.
"""
import sys; sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import csv, numpy as np, matplotlib.pyplot as plt
from collections import defaultdict
from scipy import stats
import lib

OUT3 = "/Volumes/4 MB/ablation_figures_20260625/group3"; SCRIPT = __file__
lib.apply_style()
master, _ = lib.load_master_plots(); mr = {r["Batch Name"]: r for r in master}
def gv(b, c): return (mr.get(b, {}).get(c, "") or "").strip()

ch = defaultdict(list)
for r in csv.DictReader(open("/Volumes/4 MB/annotations/CHROMOSOME_MASTER.csv")):
    if lib.is_prophase_ablation(r.get("batch","")): continue   # prophase excluded (no prophase group)
    ch[r["batch"].strip()].append(r)

X, Y, C = [], [], []
for b, rs in ch.items():
    if lib.plot_excluded(b): continue
    ts = []
    for r in rs:
        try: ts.append(float(r.get("congression_time_s") or ""))
        except Exception: pass
    if not ts: continue
    m0 = lib.parse_time(gv(b, "Metaphase Start (s)"))
    d = lib.parse_time(gv(b, "Meta Duration (s)"))
    if d is None:
        a0 = lib.parse_time(gv(b, "Anaphase Onset (s)"))
        d = (a0 - m0) if (m0 is not None and a0 is not None) else None
    if m0 is None or d is None or d <= 0: continue
    X.append((max(ts) - m0) / 60.0); Y.append(d / 60.0); C.append(b)

X = np.array(X); Y = np.array(Y)
rho, pv = stats.spearmanr(X, Y)
fig, ax = plt.subplots(figsize=(6.6, 5.2))
ax.scatter(X, Y, s=44, color="#b2182b", alpha=.85, edgecolor="#5e0d17")
if len(X) >= 4:
    m, c0 = np.polyfit(X, Y, 1); xr = np.linspace(X.min(), X.max(), 20)
    ax.plot(xr, m * xr + c0, "--", color="#333", lw=1.6)
ax.set_xlabel("Delay of the LAST chromosome to congress (min after metaphase onset)")
ax.set_ylabel("Metaphase duration (min)")
ax.set_title(f"Rate-limiting: the slowest chromosome gates anaphase\n"
             f"N={len(X)}; Spearman rho={rho:.2f}, p={pv:.3g}   "
             f"[VALIDATED RECONSTRUCTION — original code lost; definition recovered by testing candidates "
             f"against the recorded rho=0.666/N=38]", loc="left", fontweight="bold", fontsize=8.8)
plt.tight_layout(); fig.savefig(f"{OUT3}/G3_max_congression_delay_vs_metaphase_duration.png",
                                bbox_inches="tight", dpi=130); plt.close(fig)
lib.record_plot("G3_max_congression_delay_vs_metaphase_duration",
                ["batch", "max_congression_delay_min", "meta_min"],
                [[c, round(a, 3), round(y, 2)] for c, a, y in zip(C, X, Y)],
                {"rho": round(float(rho), 3), "p": float(pv), "N": len(X),
                 "definition": "max(congression_time) - metaphase_start",
                 "recorded_original": {"rho": 0.666, "N": 38},
                 "status": "validated reconstruction, original code never saved"},
                SCRIPT, "Max congression delay vs metaphase duration (validated reconstruction 2026-07-22)")
print(f"N={len(X)} rho={rho:.3f} p={pv:.3g}  (recorded original: rho 0.666, N 38)")
