"""SINGLE sisterless-kinetochore (on-target, #Sisterless==1) cells only.
Relationship between how long the cell spends in metaphase and how long the targeted (sisterless) chromosome
takes to congress to the metaphase plate, with the targeted chromosome's LENGTH encoded as colour.

x = metaphase duration for that cell (MM:SS)             [Metaphase Start -> Anaphase, master]
y = time from metaphase onset to congression of the sisterless chromosome (min)
      = (plate-join time  -  Metaphase Start) for cells whose chromosome rejoined the plate
      = 0 (open square)   for chromosomes AT the plate from metaphase onset
      = censored (open triangle at top)  for chromosomes that STAYED POLAR until anaphase (never congressed)
colour = targeted chromosome length (um) from data/G3_chromo_length.csv (grey if unavailable)

Congression + behaviour: annotations/SISTERLESS_PLATE_JOIN_TIMES.csv. Trend/Spearman on the rejoined cells."""
import sys; sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import csv, os
import numpy as np, matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from scipy import stats as _st
import lib
lib.apply_style()

OUT = "/Volumes/4 MB/ablation_figures_20260625/group1"; SCRIPT = __file__
data, _ = lib.load_master_plots()
_DBL = lib.double_chromosome_batches(); mr = {r["Batch Name"]: r for r in data}

# chromosome length per batch (targeted chromosome) from the processed G3 table
length = {}
for row in csv.DictReader(open("/Volumes/4 MB/ablation_plots/data/G3_chromo_length.csv")):
    try: length[row["batch"].strip()] = float(row["length_um"])
    except (ValueError, KeyError): pass

pj = {row["batch"].strip(): row for row in csv.DictReader(open("/Volumes/4 MB/annotations/SISTERLESS_PLATE_JOIN_TIMES.csv"))}

rejoin = []   # (dur, congress_min, length_or_None, batch)
atplate = []  # (dur, length)
polar = []    # (dur, length)
for r in data:
    b = r["Batch Name"]
    if r.get("On-Target / Off-Target", "").lower() != "on-target": continue
    if str(r.get("# Sisterless KTs", "")).strip() != "1": continue
    if r.get("Exclude") in ("Yes", "yes"): continue
    if lib.plot_excluded(r["Batch Name"]): continue   # USER 2026-07-16: metaphase/4-sis/drug/excluded out
    if lib.is_mad1(b) or b in _DBL: continue
    dur, ok = lib.mitotic_duration_min(r)
    if not ok: continue
    row = pj.get(b)
    if not row: continue
    v = (row.get("chromosome_1_plate_join") or "").strip().lower()
    L = length.get(b)
    if v == "anaphase":
        polar.append((dur, L))
    elif v in ("0", "0:00", "0:00:00", "plate"):
        atplate.append((dur, L))
    elif v not in ("", "n/a", "na"):
        try: js = float(row.get("chromosome_1_plate_join_s"))
        except (TypeError, ValueError): js = lib.parse_time(v)
        ms = lib.parse_time(r.get("Metaphase Start (s)", ""))
        if js is None or ms is None: continue
        congress = (js - ms) / 60.0
        rejoin.append((dur, congress, L, b))

fig, ax = plt.subplots(figsize=(9.2, 6.0))
# colour scale from all available lengths
Ls = [L for _, _, L, _ in rejoin if L is not None] + [L for _, L in atplate + polar if L is not None]
vmin, vmax = (min(Ls), max(Ls)) if Ls else (0, 1)
import matplotlib.cm as cm
from matplotlib.colors import Normalize
norm = Normalize(vmin, vmax); cmap = cm.viridis
def col(L): return cmap(norm(L)) if L is not None else "#bbbbbb"

rx = [d for d, c, L, b in rejoin]; ry = [c for d, c, L, b in rejoin]
ax.scatter(rx, ry, s=70, c=[col(L) for _, _, L, _ in rejoin], edgecolor="#333", linewidth=0.5, zorder=4, label="rejoined plate")
# at-plate-from-onset at y=0 (open squares)
if atplate:
    ax.scatter([d for d, _ in atplate], [0] * len(atplate), s=70, marker="s", facecolor=[col(L) for _, L in atplate],
               edgecolor="#333", linewidth=0.8, zorder=4, label="at plate from onset (y=0)")
# stayed-polar = censored, plotted in a band above the data (open triangles)
ytop = (max(ry) if ry else 10) * 1.12 + 1
if polar:
    ax.scatter([d for d, _ in polar], [ytop] * len(polar), s=70, marker="^", facecolor=[col(L) for _, L in polar],
               edgecolor="#333", linewidth=0.8, zorder=4)
    ax.axhline(ytop * 0.995, color="#ccc", lw=0.8, ls=":")
    ax.text(ax.get_xlim()[1], ytop, " stayed polar\n (never congressed)", va="center", ha="left", fontsize=7.5, color="#777")

# trend + correlation on rejoined cells
if len(rx) >= 3:
    rho, p = _st.spearmanr(rx, ry)
    sl, ic = np.polyfit(rx, ry, 1); xx = np.linspace(min(rx), max(rx), 50)
    ax.plot(xx, sl * xx + ic, color="#444", lw=1.4, ls="--", zorder=2)
    ax.text(0.98, 0.03, f"rejoined cells: Spearman ρ={rho:.2f}, p={p:.2g} (n={len(rx)})",
            transform=ax.transAxes, ha="right", va="bottom", fontsize=8.5, color="#222")

sm = cm.ScalarMappable(norm=norm, cmap=cmap); sm.set_array([])
cb = fig.colorbar(sm, ax=ax, fraction=0.045, pad=0.02); cb.set_label("Targeted chromosome length (µm)", fontsize=9)
ax.set_xlabel("Metaphase duration for the cell (MM:SS)")
ax.set_ylabel("Time from metaphase onset to sisterless-chromosome congression (min)")
from matplotlib.ticker import FuncFormatter
ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: lib.mmss(v) if v >= 0 else ""))
ax.set_title("Single sisterless kinetochore: metaphase duration vs sisterless-chromosome congression time\n"
             "(colour = targeted chromosome length; triangles = stayed polar / never congressed; squares = at plate from onset)",
             loc="left", fontweight="bold", fontsize=10)
_lh = [Line2D([0], [0], marker="o", color="none", markerfacecolor="#4c9a70", markeredgecolor="#333", markersize=8, label="rejoined plate"),
       Line2D([0], [0], marker="s", color="none", markerfacecolor="#4c9a70", markeredgecolor="#333", markersize=8, label="at plate from onset (y=0)"),
       Line2D([0], [0], marker="^", color="none", markerfacecolor="#4c9a70", markeredgecolor="#333", markersize=8, label="stayed polar / never congressed (top band)")]
ax.legend(handles=_lh, loc="upper left", fontsize=8)
plt.tight_layout(); plt.savefig(f"{OUT}/single_sisterless_length_congression.png", bbox_inches="tight"); plt.close()

rec = [["rejoined", round(d, 3), round(c, 3), ("" if L is None else round(L, 2)), b] for d, c, L, b in rejoin]
rec += [["at_plate_onset", round(d, 3), 0.0, ("" if L is None else round(L, 2)), ""] for d, L in atplate]
rec += [["stayed_polar", round(d, 3), "", ("" if L is None else round(L, 2)), ""] for d, L in polar]
lib.record_plot("single_sisterless_length_congression",
    ["behavior", "metaphase_duration_min", "congress_from_metaphase_onset_min", "chromo_length_um", "batch"], rec,
    {"type": "scatter+trend", "population": "on-target single-sisterless (#Sisterless==1)",
     "y": "plate-join minus metaphase-onset (min)", "colour": "targeted chromo length um",
     "censored": "stayed-polar plotted in a top band"}, SCRIPT,
    "Single sisterless: metaphase duration vs congression time (colour=chromosome length)")
print("single_sisterless_length_congression -> rejoined=%d at_plate=%d polar=%d | length-coloured=%d" %
      (len(rejoin), len(atplate), len(polar), len(Ls)))
