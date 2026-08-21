"""custom_sisterless_vs_trackmate_plate_20260722.py — plots-to-make #8.

Sisterless-kinetochore distance from the metaphase plate, plotted against the distance of the PLATE-RESIDENT
kinetochores in the same cell.

  sisterless  = the user's MANUAL polar/sisterless marks (ground truth, per the manual-over-TrackMate rule)
  plate KTs   = TrackMate spots, because manual `paired_kt` marks exist in only ONE cell that also has
                sisterless marks — the known paired_kt annotation gap. User explicitly asked for the
                TrackMate version here (2026-07-22).

MIXED-SOURCE PLOT: NOTES §1 rule 1 normally forbids manual+TrackMate on one figure. This one is an
explicit, user-requested exception and is labelled as such on the figure itself.

Batches: only those with output from the LATEST TrackMate run (`results_v6long`, per-frame threshold +
targetspf=20 + extended anaphase+15min window). No new TrackMate runs are launched.

Plate-KT selection copies group4_tracking_dist.py: of the TrackMate spots present at a timepoint, the ones
that sit CLOSEST to the drawn meta_plate line are the plate-resident kinetochores.
"""
import sys; sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import csv, json, os, numpy as np, matplotlib.pyplot as plt
from collections import defaultdict
from scipy import stats
import lib

OUT4 = "/Volumes/4 MB/ablation_figures_20260625/group4"
SCRIPT = __file__
RES = "/Volumes/4 MB/kt_tracking/results_v6long"
STACKS = "/Volumes/4 MB/kt_tracking/stacks_long"
lib.apply_style()

data, _ = lib.load_master(); mr = {r["Batch Name"]: r for r in data}
def ps(b):
    try:
        v = float((mr.get(b, {}).get("Pixel Size (um)", "") or "").strip()); return v if v > 0 else 0.062
    except Exception: return 0.062

# manual sisterless/polar marks, with the repaired real t_sec
man = defaultdict(list)
_kp = list(csv.reader(open("/Volumes/4 MB/annotations/kt_points.csv")))
kx = {c: i for i, c in enumerate(_kp[0])}
for r in _kp[1:]:
    if r[kx['label']].strip() not in ("polar", "sisterless"): continue
    if not r[kx['t_hms']].strip(): continue
    b = r[kx['batch']].strip()
    try: man[b].append((float(r[kx['t_sec']]), int(float(r[kx['frame']])), float(r[kx['x']]), float(r[kx['y']])))
    except Exception: pass

# metaphase plate
plates = defaultdict(dict)
_mp = list(csv.reader(open("/Volumes/4 MB/annotations/meta_plates.csv")))
jx = {c: i for i, c in enumerate(_mp[0])}
for r in _mp[1:]:
    try:
        b = r[jx['batch']].strip(); p = np.array(json.loads(r[jx['points']]), float)
        if len(p) >= 2: plates[b][int(float(r[jx['frame']]))] = p
    except Exception: pass


def plate_at(b, f):
    pl = plates.get(b)
    if not pl: return None
    return pl[f] if f in pl else pl[min(pl, key=lambda k: abs(k - f))]


def pt_line_um(pt, poly, pxs):
    p = np.array(pt, float); d = 1e18
    for i in range(len(poly) - 1):
        a, bb = poly[i], poly[i + 1]; ab = bb - a; L = float(np.dot(ab, ab))
        t = 0 if L < 1e-9 else float(np.clip(np.dot(p - a, ab) / L, 0, 1))
        d = min(d, float(np.hypot(*(a + t * ab - p))))
    return d * pxs


def timing(b):
    p = os.path.join(STACKS, b.replace(" ", "_") + "_timing.csv")
    if not os.path.isfile(p): return None
    m = {}
    for r in csv.DictReader(open(p)):
        try: m[int(r["stitched_frame"])] = float(r["t_sec"])
        except Exception: pass
    return m


def tm_spots(b):
    """(t_sec, x_px, y_px) for every TrackMate spot in the latest run."""
    safe = b.replace(" ", "_")
    f = os.path.join(RES, safe + ".spots.csv")
    if not os.path.isfile(f): return []
    tm = timing(b)
    if not tm: return []
    pxs = ps(b); out = []
    for s in csv.DictReader(open(f)):
        try:
            fr = int(float(s["frame"]))
            if fr in tm: out.append((tm[fr], float(s["x_um"]) / pxs, float(s["y_um"]) / pxs))
        except Exception: pass
    return out


PLATE_TOL_UM = 2.5      # a TrackMate spot within this of the drawn plate line is plate-resident
X, Y, C, NP = [], [], [], []
avail = sorted({f.split(".")[0] for f in os.listdir(RES)} ) if os.path.isdir(RES) else []
print(f"batches with latest-TrackMate output: {len(avail)}")
for b, marks in man.items():
    if lib.plot_excluded(b) or lib.is_mad1(b): continue
    sp = tm_spots(b)
    if not sp or not plates.get(b): continue
    pxs = ps(b)
    # sisterless distance (manual)
    ds = []
    for (t, f, x, y) in marks:
        poly = plate_at(b, f)
        if poly is None or len(poly) < 2: continue
        ds.append(pt_line_um((x, y), poly, pxs))
    if len(ds) < 3: continue
    # plate KTs (TrackMate): spots that sit within PLATE_TOL of the plate line
    dp = []
    fr_by_t = sorted(plates[b])
    for (t, x, y) in sp:
        # nearest plate drawing in FRAME space is fine — the plate is a fixed spatial reference
        poly = plates[b][fr_by_t[len(fr_by_t) // 2]]
        d = pt_line_um((x, y), poly, pxs)
        if d <= PLATE_TOL_UM: dp.append(d)
    if len(dp) < 5: continue
    X.append(float(np.median(dp))); Y.append(float(np.median(ds))); C.append(b); NP.append(len(dp))

print(f"cells with BOTH manual sisterless and TrackMate plate KTs: {len(X)}")
if len(X) < 3:
    print("#8 still too few — not plotted"); sys.exit()

X = np.array(X); Y = np.array(Y)
rho, pv = stats.spearmanr(X, Y) if len(X) >= 4 else (float("nan"), float("nan"))
w = stats.wilcoxon(X, Y)[1] if len(X) >= 6 else float("nan")
fig, ax = plt.subplots(figsize=(6.6, 5.6))
for x, y in zip(X, Y):
    ax.plot([0, 1], [x, y], "-", color="#bbb", lw=1, alpha=.8, zorder=1)
ax.scatter(np.zeros(len(X)), X, s=46, color="#1b7837", zorder=3, label="plate KTs (TrackMate)")
ax.scatter(np.ones(len(Y)), Y, s=46, color="#b2182b", zorder=3, label="sisterless KT (manual)")
for i, b in enumerate(C):
    ax.annotate(b.split()[-1], (1, Y[i]), fontsize=6, color="#555", xytext=(6, 0), textcoords="offset points")
ax.set_xticks([0, 1]); ax.set_xticklabels(["plate kinetochores", "sisterless kinetochore"])
ax.set_ylabel("Median distance to the metaphase plate (µm)")
ax.set_title(f"Sisterless KT vs the cell's plate-resident KTs — distance from the plate\n"
             f"N={len(X)} cells; Wilcoxon p={w:.3g}"
             f"    [MIXED SOURCE: sisterless = manual marks, plate = TrackMate {os.path.basename(RES)}]",
             loc="left", fontweight="bold", fontsize=9)
ax.legend(fontsize=8)
plt.tight_layout()
fig.savefig(f"{OUT4}/G4_sisterless_vs_trackmate_plate_dist.png", bbox_inches="tight", dpi=130)
plt.close(fig)
lib.record_plot("G4_sisterless_vs_trackmate_plate_dist",
                ["batch", "plate_kt_median_um", "sisterless_median_um", "n_plate_spots"],
                [[c, round(a, 3), round(b2, 3), n] for c, a, b2, n in zip(C, X, Y, NP)],
                {"N": len(X), "wilcoxon_p": float(w), "rho": float(rho),
                 "plate_tol_um": PLATE_TOL_UM, "trackmate_run": os.path.basename(RES)}, SCRIPT,
                "Sisterless vs TrackMate plate-KT distance from the plate (plots-to-make #8)")
print(f"#8 N={len(X)} wilcoxon p={w:.3g}")
