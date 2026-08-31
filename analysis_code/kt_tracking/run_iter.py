"""run_iter.py — run one TrackMate parameter set over the benchmark batches and score it.

Usage: python3 run_iter.py <label> <groovy> key=val key=val ...
Writes results to results_<label>/ and prints the recall/spots-per-frame score.
"""
import os, subprocess, sys, time

BASE = "/Volumes/4 MB/kt_tracking"
STACKS = os.environ.get("KT_STACKS", f"{BASE}/stacks")   # KT_STACKS=stacks_long to test the extended window
FIJI = "/Users/mblaauw/Downloads/Fiji/fiji"
LOG = f"{BASE}/logs"

label = sys.argv[1]
groovy = sys.argv[2]
P = dict(diameter=0.5, quality=-1, linkdist=0.8, gapdist=1.0, maxgap=2,
         minTrackSpots=3, mergedist=1.2, targetspf=12)
for a in sys.argv[3:]:
    if "=" in a:
        k, v = a.split("=", 1)
        P[k] = float(v) if ("." in v or k in ("diameter", "quality", "linkdist", "gapdist", "mergedist", "targetspf")) else int(v)

RES = f"{BASE}/results_{label}"
os.makedirs(RES, exist_ok=True); os.makedirs(LOG, exist_ok=True)
LIST = os.environ.get("KT_BATCH_LIST", f"{BASE}/bench_batches.txt")
batches = [l.strip() for l in open(LIST) if l.strip()]

print(f"=== {label}: {P}  ({len(batches)} batches) ===", flush=True)
t0 = time.time()
for i, b in enumerate(batches, 1):
    stk = os.path.join(STACKS, b.replace(" ", "_") + "_KTmon.tif")
    if not os.path.isfile(stk):
        print(f"[{i}] MISSING stack {b}", flush=True); continue
    args = "imgPath='%s',outDir='%s'," % (stk, RES) + ",".join(f"{k}={v}" for k, v in P.items())
    blog = os.path.join(LOG, f"{label}_{b.replace(' ','_')}.log")
    with open(blog, "w") as f:
        try:
            subprocess.run([FIJI, "--headless", "--run", groovy, args],
                           stdout=f, stderr=subprocess.STDOUT, timeout=1800)
        except subprocess.TimeoutExpired:
            print(f"[{i}] TIMEOUT {b}", flush=True); continue
    tail = ""
    for L in open(blog, errors="ignore"):
        if "spots," in L and "tracks" in L:
            tail = L.strip()
    print(f"[{i}/{len(batches)}] {b}: {tail[-55:]}", flush=True)
print(f"--- ran in {time.time()-t0:.0f}s ---", flush=True)
subprocess.run([sys.executable, f"{BASE}/score_vs_manual.py", RES,
                "--batches", f"{BASE}/bench_batches.txt", "--label", label])
