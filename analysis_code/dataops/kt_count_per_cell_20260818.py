#!/usr/bin/env python3
"""How many kinetochores does each cell show?  Looking for cells above the PtK2 norm.

PtK2 carries 14 chromosomes -> 28 kinetochores in mitosis (Chong et al. 2024, Dumont lab).  A tetraploid or
otherwise abnormal cell would show materially more.

THREE INDEPENDENT COUNTS, because no single one sees every kinetochore:
  A  TrackMate spots per frame (kt_tracking/results/*.spots_timed.csv) -- detection on the fluorescence
     channel; the 95th-percentile per-frame count is used, so one noisy frame cannot set the number
  B  TrackMate tracks per cell (KT_TRACKING_MASTER n_tracks)
  C  her own marks: distinct kinetochore identities she drew (kt_outlines `grp`, kt_points labels)
Cdc20 marks only a SUBSET of kinetochores (it concentrates at unattached ones), so a LOW count means
nothing; only a HIGH count is informative.  That asymmetry is the whole point of this script.
"""
import csv, io, os, re, sys, glob, collections
import numpy as np
sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625"); import lib

RES = "/Volumes/4 MB/kt_tracking/results"
OUT = "/Volumes/4 MB/4_TABLES_AND_REPORTS/KT_COUNT_PER_CELL_20260818.csv"
# 2026-08-18, CORRECTED: her own lab's papers and the cell-line references say PtK2 has **14**
# chromosomes (Chong et al. 2024 JCB 223:e202310010, Dumont lab: "PtK2 cells ... just 14 chromosomes";
# the ATCC/Zeiss/Olympus PtK2 pages say the same). The local karyotype reference in
# 4_TABLES_AND_REPORTS/PTK2_CHROMOSOME_LENGTHS_REFERENCE.md quotes male 2n = 13 from Lorenz &
# Ainsworth 1972 - the two numbers are both in the literature and SHE has to pick one for the thesis.
# The screen below uses 14 / 28, the more conservative (higher) threshold.
EXPECTED_CHROMOSOMES, EXPECTED_KT = 14, 28

def rd(p):
    with io.open(p, encoding="utf-8", errors="replace") as f: return list(csv.DictReader(f))

M, HDR = lib.load_master()
MB = {r["Batch Name"].strip(): r for r in M if (r.get("Batch Name") or "").strip()}
KTM = rd("/Volumes/4 MB/annotations/KT_TRACKING_MASTER.csv")

def norm(s):
    return re.sub(r"[^a-z0-9]+", "", (s or "").lower())

spot_files = {norm(os.path.basename(p).replace(".spots_timed.csv", "")): p
              for p in glob.glob(RES + "/*.spots_timed.csv")}

rows = []
for r in KTM:
    b = (r.get("batch") or "").strip()
    if not b: continue
    mrow = MB.get(b) or {}
    ct = (mrow.get("Cell Type") or "").strip()
    p = spot_files.get(norm(b)) or spot_files.get(norm(b.replace(" ", "_")))
    p95 = pmax = nframes = None
    if p:
        sp = rd(p)
        fcol = next((c for c in ("FRAME", "frame", "POSITION_T", "t_frame") if sp and c in sp[0]), None)
        if fcol:
            per = collections.Counter(x[fcol] for x in sp)
            v = np.array(sorted(per.values()))
            p95 = float(np.percentile(v, 95)); pmax = int(v.max()); nframes = len(per)
    rows.append(dict(batch=b, cell_type=ct,
                     n_tracks=r.get("n_tracks", ""), n_spots=r.get("n_spots", ""),
                     spots_per_frame_p95=p95, spots_per_frame_max=pmax, n_frames=nframes,
                     has_spot_file=int(bool(p))))

# ---- her own marks: distinct kinetochore identities per cell
ko = rd("/Volumes/4 MB/annotations/kt_outlines.csv")
grp = re.compile(r"grp:(\d+)")
own = collections.defaultdict(set)
for x in ko:
    m = grp.search(x.get("notes") or "")
    if m: own[(x.get("batch") or "").strip()].add((x.get("label") or "").strip() + ":" + m.group(1))
for row in rows:
    row["her_distinct_kt_identities"] = len(own.get(row["batch"], ()))

with open(OUT, "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)

withsp = [r for r in rows if r["spots_per_frame_p95"] is not None]
cdc = [r for r in withsp if "cdc20" in r["cell_type"].lower()]
print(f"cells in KT_TRACKING_MASTER: {len(rows)}   with TrackMate spot files: {len(withsp)}   cdc20: {len(cdc)}")
if cdc:
    v = np.array([r["spots_per_frame_p95"] for r in cdc])
    print(f"cdc20 detected kinetochores per frame (95th pct within each cell): "
          f"median {np.median(v):.1f}, IQR {np.percentile(v,25):.1f}-{np.percentile(v,75):.1f}, max {v.max():.0f}")
    print(f"expected for PtK2: {EXPECTED_CHROMOSOMES} chromosomes / {EXPECTED_KT} kinetochores\n")
    over = sorted([r for r in cdc if r["spots_per_frame_p95"] > EXPECTED_KT],
                  key=lambda r: -r["spots_per_frame_p95"])
    print(f"cdc20 cells whose 95th-percentile per-frame spot count EXCEEDS {EXPECTED_KT}: {len(over)}")
    for r in over[:25]:
        print(f"   {r['batch'][:58]:60s} p95={r['spots_per_frame_p95']:5.1f}  max={r['spots_per_frame_max']:4d} "
              f"tracks={r['n_tracks']:>4}")
    hers = [r for r in rows if r["her_distinct_kt_identities"] > EXPECTED_KT]
    print(f"\ncells where SHE traced more than {EXPECTED_KT} distinct kinetochore identities: {len(hers)}")
    for r in hers[:10]:
        print(f"   {r['batch'][:58]:60s} {r['her_distinct_kt_identities']}")
print(f"\n[done] -> {OUT}")
