"""TRIPLE ablation, PROMETAPHASE group only: time from the first ablation to metaphase onset vs metaphase
duration. Prometaphase group = Phase of Ablations startswith 'promet' OR a 'v2=prometaphase' note in the
master Notes (the reclassification tag). Population: 3-sisterless on-target OR name contains 'triple_ablation'
(mad1 + double-chromosome excluded).

x = metaphase duration (MM:SS)                       [Metaphase Start -> Anaphase]
y = time from first ablation to metaphase onset (min) = Ablation->Meta   (well-covered; no NEB needed)
Cells missing Ablation->Meta or a usable duration are written to data/triple_prometa_needs_NEB.csv."""
import sys; sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import csv, os
import numpy as np, matplotlib.pyplot as plt
from scipy import stats as _st
import lib
lib.apply_style()

OUT = "/Volumes/4 MB/ablation_figures_20260625/group1"; SCRIPT = __file__
DATADIR = "/Volumes/4 MB/ablation_plots/data"
data, _ = lib.load_master()
_DBL = lib.double_chromosome_batches()

def sec(x):
    x = (x or "").strip()
    if not x: return None
    if x.replace('.', '', 1).replace(',', '').isdigit(): return float(x.replace(',', ''))
    return lib.parse_time(x)

pts = []; missing = []
for r in data:
    b = r["Batch Name"]
    # HER STANDING RULE: bin ablation number by the master "# Sisterless KTs" column, NEVER by the batch or
    # file name. The `or "triple_ablation" in b.lower()` that used to be here pulled in 9 batches whose master
    # value is 0, 1, 2, 4 or blank purely because the ACQUISITION was named triple_ablation -- the name records
    # what was attempted, the column records what actually happened.
    is_triple = (str(r.get("# Sisterless KTs", "")).strip() == "3"
                 and r.get("On-Target / Off-Target", "").lower() == "on-target")
    if not is_triple: continue
    if r.get("On-Target / Off-Target", "").lower() != "on-target": continue
    if r.get("Exclude") in ("Yes", "yes"): continue
    if lib.is_mad1(b) or b in _DBL: continue
    ph = r.get("Phase of Ablations", "").lower(); notes = r.get("Notes", "").lower()
    if not (ph.startswith("promet") or "v2=prometaphase" in notes or "v2 = prometaphase" in notes): continue
    a2m = sec(r.get("Ablation->Meta (s)")) or sec(r.get("Ablation->Meta (min)"))
    dur, ok = lib.mitotic_duration_min(r)
    v2 = "v2=prometaphase" in notes
    if a2m is not None and ok:
        y = a2m / 60.0    # time from first ablation to metaphase onset (min)
        pts.append((dur, y, v2, b))
    else:
        miss = [k for k, v in (("Abl->Meta", a2m), ("duration", dur if ok else None)) if v is None]
        missing.append((b, r.get("Phase of Ablations", ""), "v2" if v2 else "", ";".join(miss)))

fig, ax = plt.subplots(figsize=(8.4, 5.6))
if pts:
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    cols = ["#b2182b" if p[2] else "#2166ac" for p in pts]
    ax.scatter(xs, ys, s=60, c=cols, edgecolor="#333", linewidth=0.5, zorder=4)
    if len(xs) >= 3:
        rho, p = _st.spearmanr(xs, ys)
        sl, ic = np.polyfit(xs, ys, 1); xx = np.linspace(min(xs), max(xs), 40)
        ax.plot(xx, sl * xx + ic, color="#444", lw=1.4, ls="--", zorder=2)
        ax.text(0.98, 0.03, f"Spearman ρ={rho:.2f}, p={p:.2g} (n={len(xs)})", transform=ax.transAxes, ha="right", va="bottom", fontsize=8.5, color="#222")
from matplotlib.lines import Line2D
ax.legend(handles=[Line2D([0], [0], marker="o", color="none", markerfacecolor="#2166ac", markeredgecolor="#333", markersize=8, label="Phase=prometaphase"),
                   Line2D([0], [0], marker="o", color="none", markerfacecolor="#b2182b", markeredgecolor="#333", markersize=8, label="v2=prometaphase note")],
          loc="upper left", fontsize=8)
ax.set_xlabel("Metaphase duration for the cell (MM:SS)")
ax.set_ylabel("Time from first ablation to metaphase onset (min)")
from matplotlib.ticker import FuncFormatter
ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: lib.mmss(v) if v >= 0 else ""))
ax.set_title(f"Triple ablation (prometaphase group): ablation-to-metaphase-onset time vs metaphase duration\n"
             f"n={len(pts)} plotted" + (f"; {len(missing)} lack ablation-to-meta/duration" if missing else ""), loc="left", fontweight="bold", fontsize=10)
plt.tight_layout(); plt.savefig(f"{OUT}/triple_prometa_ablation_to_mitosis.png", bbox_inches="tight"); plt.close()

os.makedirs(DATADIR, exist_ok=True)
with open(f"{DATADIR}/triple_prometa_needs_NEB.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["batch", "phase_of_ablations", "prometa_source", "missing_fields"])
    for row in sorted(missing): w.writerow(row)
lib.record_plot("triple_prometa_ablation_to_mitosis", ["metaphase_duration_min", "ablation_to_meta_onset_min", "v2note", "batch"],
    [[round(d, 3), round(y, 3), int(v2), b] for d, y, v2, b in pts],
    {"type": "scatter+trend", "population": "triple/3-sisterless on-target, prometaphase group (Phase or v2 note)",
     "y": "Ablation->Meta = time from first ablation to metaphase onset (min)"},
    SCRIPT, "Triple prometaphase: ablation-to-metaphase-onset vs metaphase duration")
print(f"triple_prometa_ablation_to_mitosis -> plotted {len(pts)} | missing timing {len(missing)} -> data/triple_prometa_needs_NEB.csv")
