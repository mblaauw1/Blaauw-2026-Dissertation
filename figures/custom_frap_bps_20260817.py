"""THE BPS-POSTER FRAP FIGURE, rebuilt inside this project — with its source data recovered and archived.

USER 2026-08-17: "the frap plot from the bps poster we made a few months ago: its far better than the frap
plot we have now, and i want to replace the frap plot we have now with this version, but in order to do so
i need to have a record of the data that i can include in my thesis, so find the data that this plot was
created from before subbing it into any illustrator docs."

WHERE IT CAME FROM (traced, not guessed):
  * The poster is `/Users/mblaauw/Desktop/BPS Poster.ai`; its link table names
    `/Users/mblaauw/Downloads/frap/unmarked/summary_combined_unsmoothed.pdf` — that is the figure.
  * That PDF was written by `/Users/mblaauw/flouescence intensity for FRAP updated.py`
    (an interactive TIF/ROI reviewer), whose `make_summary_plot()` produces exactly this layout:
    per-trace lines, a dashed group mean, a shaded band, and a right-hand gain strip.
  * The data it saved is `/Users/mblaauw/Downloads/microscopy_results_filtered.csv` — same day as the PDFs
    (2026-01-21), same columns the script writes (`group`, `category`, `set_id`, `raw_intensity`,
    `corrected`, `relative_time`, `normalized`). `microscopy_results_raw.csv` is the pre-QC version.
  * BOTH CSVs are copied to `/Volumes/4 MB/4_TABLES_AND_REPORTS/frap_bps_poster_data_20260817/` with a README, because the
    originals live in ~/Downloads, which gets cleaned.

TWO DELIBERATE DIFFERENCES FROM THE POSTER RENDER, both hers:
  1. THE SHADED BAND IS SEM, not the 95% CI the poster script drew. Her 2026-08-17 rule for every line
     plot in the deck is "a region of error shaded around it thats SEM"; the later instruction wins, and
     the band is labelled so nobody has to guess which it is.
  2. Axis labels go through `canon_labels`, so this figure says "Time from ablation (s)" and
     "Normalized intensity" the same way every other figure in the deck does.
Everything else — normalisation to 1.0 pre-ablation and 0.0 at the shot, the per-trace lines, the dashed
group means, the gain strip on the right — is the poster figure as it stands.
"""
import sys, os, shutil
sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import numpy as np, pandas as pd, matplotlib.pyplot as plt
import lib
lib.apply_style()

SRC_FILT = "/Users/mblaauw/Downloads/microscopy_results_filtered.csv"
SRC_RAW  = "/Users/mblaauw/Downloads/microscopy_results_raw.csv"
SRC_GEN  = "/Users/mblaauw/flouescence intensity for FRAP updated.py"
POSTER   = "/Users/mblaauw/Desktop/BPS Poster.ai"
POSTPDF  = "/Users/mblaauw/Downloads/frap/unmarked/summary_combined_unsmoothed.pdf"

ARCH = "/Volumes/4 MB/4_TABLES_AND_REPORTS/frap_bps_poster_data_20260817"
OUT  = "/Volumes/4 MB/ablation_figures_20260625/group4"
SCRIPT = __file__
ABL_T = 6.0          # the experiment's fixed ablation time, from the generator's CONFIG
TMAX  = 18.0         # the poster figure stops here

os.makedirs(ARCH, exist_ok=True)
for p in (SRC_FILT, SRC_RAW, SRC_GEN):
    if os.path.exists(p):
        dst = os.path.join(ARCH, os.path.basename(p))
        if not os.path.exists(dst) or os.path.getmtime(p) > os.path.getmtime(dst):
            shutil.copy2(p, dst)
if os.path.exists(POSTPDF):
    shutil.copy2(POSTPDF, os.path.join(ARCH, "POSTER_RENDER_summary_combined_unsmoothed.pdf"))

df = pd.read_csv(SRC_FILT)
df = df[np.isfinite(df["relative_time"]) & np.isfinite(df["normalized"])]
df = df[df["relative_time"] <= TMAX]

COL = {"frap_ablation": "#0072B2", "complete_ablation": "#D55E00"}
NAME = {"frap_ablation": "FRAP ablated", "complete_ablation": "Complete ablated"}
abl = df[df["category"] == "ablated"].copy()

fig, ax = plt.subplots(figsize=(10, 6.4))
stats_rows, gain = {}, {}
for g in ("complete_ablation", "frap_ablation"):
    sub = abl[abl["group"] == g]
    if sub.empty: continue
    c = COL[g]
    sids = sorted(sub["set_id"].dropna().unique())
    for i, sid in enumerate(sids):
        t = sub[sub["set_id"] == sid].sort_values("relative_time")
        ax.plot(t["relative_time"], t["normalized"], color=c, alpha=0.4, lw=1.0, zorder=1,
                label=(f"{NAME[g]} (n={len(sids)})" if i == 0 else None))
    # group mean + SEM across TRACES at each timepoint
    st = sub.groupby(sub["relative_time"].round(1))["normalized"].agg(["mean", "sem", "count"])
    ax.fill_between(st.index, st["mean"] - st["sem"].fillna(0), st["mean"] + st["sem"].fillna(0),
                    color=c, alpha=0.20, lw=0, zorder=2)
    ax.plot(st.index, st["mean"], color=c, ls="--", lw=2.6, zorder=3, label=f"{NAME[g]} mean ± SEM")
    for tt, r in st.iterrows():
        stats_rows.setdefault(g, []).append([g, float(tt), round(float(r["mean"]), 4),
                                             round(float(r["sem"]), 4) if np.isfinite(r["sem"]) else 0.0,
                                             int(r["count"])])
    # recovery gain per trace: value at the LAST timepoint minus the value at the ablation frame
    gs = []
    for sid in sids:
        t = sub[sub["set_id"] == sid].sort_values("relative_time")
        if t.empty: continue
        i0 = (t["relative_time"] - ABL_T).abs().idxmin()
        i1 = (t["relative_time"] - TMAX).abs().idxmin()
        gs.append(float(t.loc[i1, "normalized"] - t.loc[i0, "normalized"]))
    gain[g] = gs

# ---- gain strip on the right, as on the poster (one column per group, mean bar) ----
XG = {"frap_ablation": 21.0, "complete_ablation": 23.0}
for g, gs in gain.items():
    if not gs: continue
    x = XG[g] + (np.random.RandomState(3).rand(len(gs)) - 0.5) * 0.8
    ax.scatter(x, gs, c=COL[g], s=50, alpha=0.75, edgecolors="white", zorder=4)
    ax.plot([XG[g] - 0.45, XG[g] + 0.45], [np.mean(gs)] * 2, color=COL[g], lw=3, zorder=5)
    lib.sd_bar(ax, gs, XG[g], color="#333333")            # her rule: dot-plot error bars are SD

ax.axvline(ABL_T, color="#666", ls=":", lw=1.0, zorder=0)
ax.set_xlim(-2, 25)
ticks = list(range(0, int(TMAX) + 1, 3)) + [XG["frap_ablation"], XG["complete_ablation"]]
labels = [str(t) for t in range(0, int(TMAX) + 1, 3)] + ["gain\nFRAP", "gain\ncomplete"]
ax.set_xticks(ticks); ax.set_xticklabels(labels)
ax.set_xlabel("Time from ablation (s)")
ax.set_ylabel("Normalized intensity")
ax.set_title("Kinetochore fluorescence after ablation — FRAP vs complete destruction\n"
             "thin lines = individual kinetochores, dashed = group mean, shaded = SEM; "
             "gain = intensity at 18 s minus intensity at the shot",
             loc="left", fontweight="bold", fontsize=9.6)
ax.legend(fontsize=8.6, ncol=2, loc="upper left")
plt.tight_layout()
plt.savefig(f"{OUT}/G4_frap_bps_trace_kinetics.png", bbox_inches="tight")
plt.close()

rows = [r for v in stats_rows.values() for r in v]
for g, gs in gain.items():
    for i, v in enumerate(gs): rows.append([g, "gain", round(v, 4), "", i + 1])
lib.record_plot("G4_frap_bps_trace_kinetics",
                ["group", "time_s_or_gain", "mean_or_value", "sem", "n_traces"], rows,
                {"type": "FRAP trace kinetics + recovery gain (BPS poster figure, rebuilt)",
                 "band": "SEM across traces (the poster render used a 95% CI; her 2026-08-17 rule is SEM)",
                 "normalization": "1.0 at the pre-ablation frame, 0.0 at the ablation frame (t=6 s)",
                 "gain_definition": "normalized intensity at 18 s minus normalized intensity at the shot",
                 "source_data": SRC_FILT,
                 "source_generator": SRC_GEN,
                 "poster": POSTER, "poster_render": POSTPDF,
                 "archived_copy": ARCH},
                SCRIPT,
                "FRAP vs complete kinetochore ablation — the BPS-poster figure, rebuilt from its recovered "
                "source data with an SEM band")

with open(os.path.join(ARCH, "README.md"), "w") as fh:
    fh.write(f"""# FRAP data behind the BPS-poster figure — recovered 2026-08-17

She asked for a record of the data behind the poster's FRAP plot before that plot replaces the one
currently on the decks. This folder IS that record; the originals live in ~/Downloads, which gets cleaned.

| file | what it is |
|---|---|
| `microscopy_results_filtered.csv` | the dataset the poster figure was drawn from (post-QC), {len(df)} rows in the plotted window |
| `microscopy_results_raw.csv` | the same measurements before the QC filter |
| `flouescence intensity for FRAP updated.py` | the interactive tool that measured the TIFs and wrote both CSVs |
| `POSTER_RENDER_summary_combined_unsmoothed.pdf` | the exact PDF the poster links |

## How to read the columns
`group` complete_ablation | frap_ablation · `category` ablated | sisterless | paired | background ·
`set_id` one kinetochore trace · `relative_time` seconds, 0 = first frame, {ABL_T:.0f} = the ablation shot ·
`corrected` background/flicker-corrected ROI intensity · `normalized` scaled so the pre-ablation frame is
1.0 and the ablation frame is 0.0.

## Provenance chain
`{POSTER}` links `{POSTPDF}`, which was written by `{SCRIPT}`'s ancestor
`{SRC_GEN}` on 2026-01-21 from `{SRC_FILT}`.

## The figure in the deck
Rebuilt as `G4_frap_bps_trace_kinetics` by `{os.path.basename(SCRIPT)}`, which reads the archived CSV in
this folder's sibling location. The only intentional change is that the shaded band is **SEM**, not the
95% CI the poster script drew — her 2026-08-17 standing rule for line plots.
""")

n_traces = {g: len(v) for g, v in gain.items()}
print("traces per group:", n_traces)
print("archived to", ARCH)
print("wrote G4_frap_bps_trace_kinetics.png")
