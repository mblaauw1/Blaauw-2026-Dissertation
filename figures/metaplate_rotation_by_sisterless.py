"""metaplate_rotation_by_sisterless — RECONSTRUCTED 2026-07-17.

The original builder was an unsaved inline/heredoc script: the rendered PNG/PDF/SVG (2026-07-13/14) and the
data CSV survived, but the generating code did not. This rebuilds a proper, archived builder from the preserved
data CSV so the plot is a first-class figure again (record_plot archives this code + the data).

Plot: per-cell NET metaphase-plate rotation over time, grouped by # sisterless KTs.
Data CSV columns: batch, sisterless, t_min, degrees_turned_net
  (plate axis = PCA of the drawn meta_plate polygon; rotation is UNDIRECTED with ±90° step unwrapping,
   accumulated to a net degrees-turned trace per cell; t_min = time from first plate observation).

NOTE ON LINEAGE: the PCA/±90°-unwrap computation itself was NOT recovered, so this builder reads the PRESERVED
computed values from the CSV rather than recomputing from meta_plates. `source` is set to the annotation +
master files so the staleness system will FLAG (not silently ignore) if those upstream sources change — i.e.
it will warn that a true recompute is needed. Wiring the rotation computation back to meta_plates is a
follow-up if live-recompute is wanted."""
import sys; sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import os, csv
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from collections import defaultdict
import lib
try: lib.apply_style()
except Exception: pass

OUT = "/Volumes/4 MB/ablation_figures_20260625/custom_collagen_vs_triple"
os.makedirs(os.path.join(OUT, "illustrator"), exist_ok=True)
DATA_CSV = "/Volumes/4 MB/ablation_plots/data/metaplate_rotation_by_sisterless.csv"

rows = list(csv.DictReader(open(DATA_CSV)))
EXCL = lib.manual_plot_exclusions("metaplate_rotation_by_sisterless")  # per-plot manual drops (MANUAL_PLOT_EXCLUSIONS.csv)
def parse_sis(v):
    v = (v or "").strip()
    return int(float(v)) if v else 0   # blank sisterless == unmodified / 0
cells = defaultdict(list); sis = {}
for r in rows:
    b = r["batch"]
    if b in EXCL:
        continue
    try:
        t = float(r["t_min"]); d = float(r["degrees_turned_net"])
    except Exception:
        continue
    cells[b].append((t, d)); sis[b] = parse_sis(r.get("sisterless"))

# ITEM M2-11 (2026-08-03): "make sure plots of centroid movement, plate rotation etc are just of the
# metaphase to anaphase time region" -- this plot used to show the WHOLE traced range (no upper bound).
# Restrict to Metaphase Start -> Anaphase Onset.
#
# This builder reads a PRESERVED data CSV (t_min only, no frame column -- the original PCA/unwrap code was
# lost, see module docstring). CORRECTION (2026-08-03): the module docstring's claim that t_min is "time
# from first plate observation" does NOT match the data -- empirically t_min lines up with the master's
# elapsed-from-ablation clock directly (verified against the pre-existing metaplate_rotation_by_sisterless_
# win_meta_to_ana companion, which filters this same preserved CSV with a direct t_min*60-vs-master-seconds
# comparison and keeps a sensible 479/642 rows). A first attempt here re-based each cell's window using its
# own first meta_plates.csv frame as a per-cell zero -- that is WRONG (it assumes the false "since first
# plate observation" baseline) and silently dropped 7 of 12 cells to zero in-window points. Reverted to the
# same direct-comparison convention the companion already uses (elapsed seconds from first ablation, /60 for
# minutes) so the parent and companion agree, and so as not to invent a different, unvalidated time base.
_master, _ = lib.load_master()
_mr = {r["Batch Name"]: r for r in _master}


def _window_bounds_tmin(b):
    """Return (lo_t_min, hi_t_min) -- Metaphase Start / Anaphase Onset converted straight to minutes on the
    master's elapsed-from-ablation clock (same convention as make_window_companions_20260729.py's win_bounds
    / the pre-existing _win_meta_to_ana companion for this same plot) -- or None if undetermined."""
    r = _mr.get(b, {})
    m = lib.parse_time(r.get("Metaphase Start (s)", "")) or lib.parse_time(r.get("Metaphase Onset (s)", ""))
    a = lib.parse_time(r.get("Anaphase Onset (s)", ""))
    if m is None or a is None or a <= m:
        return None
    return m / 60.0, a / 60.0


_dropped_batches, _dropped_points = [], 0
# USER 2026-08-10: the standing cohort exclusion was never applied here, so prophase ablations reached
# the figure. Drop them before any window/rotation work.
for b in [x for x in cells if lib.plot_excluded(x) or lib.is_mad1(x)]:
    lib.log_review("metaplate_rotation_cohort_excluded", b, "prophase/drug/metaphase-abl/4-sis/Mad1",
                   "standing rule, user 2026-08-10")
    cells.pop(b, None)
for b in list(cells):
    wb = _window_bounds_tmin(b)
    if wb is None:
        lib.log_review("metaplate_rotation_by_sisterless_window", b, "no Metaphase Start / Anaphase Onset",
                        "cannot determine a metaphase->anaphase window for this batch -- dropped "
                        "entirely instead of showing its full un-windowed rotation trace")
        _dropped_batches.append(b); del cells[b]; del sis[b]
        continue
    lo, hi = wb
    before = len(cells[b])
    cells[b] = [(t, d) for (t, d) in cells[b] if lo <= t <= hi]
    _dropped_points += before - len(cells[b])
    if len(cells[b]) < 2:
        lib.log_review("metaplate_rotation_by_sisterless_window", b, f"{len(cells[b])} pts in window",
                        "fewer than 2 rotation points fall inside the metaphase->anaphase window -- dropped")
        _dropped_batches.append(b); del cells[b]; del sis[b]

# color + label per # sisterless KTs (only 0/1/3 present, but keep the full map for robustness)
PAL = {0: ("#8c8c8c", "unmodified/0"), 1: ("#2e9e3f", "1-sisterless"),
       2: ("#d68f00", "2-sisterless"), 3: ("#8e44ad", "3-sisterless"), 4: ("#b2182b", "4-sisterless")}
groups = defaultdict(list)
for b in cells: groups[sis[b]].append(b)

fig, ax = plt.subplots(figsize=(9, 5.6))
ax.axhline(0, color="#bbbbbb", ls=":", lw=1, zorder=1)
for s in sorted(groups):
    col, lab = PAL.get(s, ("#333333", f"{s}-sisterless"))
    for b in groups[s]:
        arr = sorted(cells[b])
        ax.plot([p[0] for p in arr], [p[1] for p in arr], color=col, lw=1.2,
                marker="o", ms=2.5, alpha=.85, zorder=3)
    ax.plot([], [], color=col, lw=2, marker="o", ms=4, label=f"{lab} (N={len(groups[s])})")

ncell = len(cells)
nrows = sum(len(v) for v in cells.values())
# ITEM M2-11 CORRECTION: x-axis label used to say "time from first plate observation" -- that baseline does
# not match the data (see comment above _window_bounds_tmin); it is elapsed time from the first ablation,
# the same clock as t_sec everywhere else in this codebase.
ax.set_xlabel("Time from first ablation (min)")
ax.set_ylabel("Metaphase-plate rotation (degrees turned, net)")
ax.set_title("Metaphase-plate rotation by # sisterless KTs\n"
             f"metaphase onset -> anaphase onset only, N={ncell} cells\n"
             f"(plate axis = PCA of drawn meta_plate; line is undirected ±90° steps)", fontsize=11)
ax.legend(loc="upper left", fontsize=9, framealpha=.9, title="# sisterless KTs")
fig.tight_layout()
png = os.path.join(OUT, "metaplate_rotation_by_sisterless.png")
fig.savefig(png, dpi=150, bbox_inches="tight")
fig.savefig(os.path.join(OUT, "illustrator", "metaplate_rotation_by_sisterless.svg"), bbox_inches="tight")
plt.close(fig); print("wrote", png, f"({ncell} cells, {nrows} rows)")

# ITEM M2-11: provenance now reflects the WINDOWED points actually plotted (cells dict), not the raw
# unfiltered CSV rows -- previously this list was built straight from `rows`, ignoring the window entirely.
prov = [[b, sis[b], round(t, 3), round(d, 3)] for b in sorted(cells) for (t, d) in sorted(cells[b])]
_src = [p for p in ["/Volumes/4 MB/annotations/meta_plates.csv", "/Volumes/4 MB/ABLATION_MASTER.csv"]
        if os.path.isfile(p)]
lib.record_plot("metaplate_rotation_by_sisterless",
    ["batch", "sisterless", "t_min", "degrees_turned_net"], prov,
    {"type": "per-cell metaphase-plate net rotation over time, grouped by # sisterless KTs",
     "window": "meta_to_ana (item M2-11, 2026-08-03) -- restricted to Metaphase Start -> Anaphase Onset, "
               "elapsed-from-ablation clock (same convention as t_sec / the master event columns); "
               "previously showed the whole traced range (n=642 rows / 12 cells)",
     "n_rows_kept": nrows, "n_cells_kept": ncell,
     "dropped_batches_no_window": sorted(set(_dropped_batches)),
     "x": "time from first ablation (min) -- CORRECTED 2026-08-03, previously mislabeled 'time from first "
          "plate observation'",
     "y": "net degrees turned (PCA of drawn meta_plate polygon, undirected ±90° unwrap)",
     "groups": "# sisterless KTs (0/1/3 present)",
     "reconstructed": "2026-07-17 from preserved data CSV; original builder was an unsaved inline script; "
                      "rotation values read from CSV (PCA/unwrap not recomputed)",
     "manual_exclusions": "per MANUAL_PLOT_EXCLUSIONS.csv — dropped: " + (", ".join(sorted(EXCL)) or "(none)")},
    __file__, "Metaphase-plate rotation over time by # sisterless KTs, metaphase to anaphase only",
    source=_src or None, key_column="batch")
print("recorded provenance (code + data now archived)")
lib.flush_review("/Volumes/4 MB/ablation_figures_20260625/_review/metaplate_rotation_by_sisterless_review.csv")
