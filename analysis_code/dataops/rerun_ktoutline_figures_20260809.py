#!/usr/bin/env python3
"""Re-run every kt-outline-dependent figure on the corrected data, and report before/after N.

WHY: today's corrections change what these figures are built from --
  * KT_SISTER_KK rebuilt: 32 -> 41 of 46 outlined cells (the prophase pre-filter was a PLOT rule wrongly
    applied inside a DATA STORE), and 20250826 test_ablation_14 now carries her reviewed sister pairs.
  * kt_outlines.csv gained 98 traces recovered from localStorage for 20260108 two_sisterless_kinetochores_14.
  * contradictory manual/proximity sister rows are gone (manual branch no longer falls through).

She asked for the change to be VISIBLE, not assumed, so this captures the per-figure cell count from each
figure's recorded data CSV before and after, and prints only what actually moved.

Order matters: the KT chain regenerates the derived stores first, then the other annotation-dependent
builders run against them.
"""
import csv, json, os, subprocess, sys, time, collections

csv.field_size_limit(10 ** 9)
ROOT = "/Volumes/4 MB"
DATA = f"{ROOT}/ablation_plots/data"
PROV = f"{ROOT}/ablation_plots/PLOT_DATA_PROVENANCE_20260809.csv"
KT_STORES = ("kt_outlines.csv", "KT_OUTLINE_TRACKS", "KT_SISTER_KK", "kt_shape_metrics")


def snapshot():
    """plot_id -> (n_rows, n_cells) from each figure's recorded data CSV."""
    out = {}
    for f in os.listdir(DATA):
        if not f.endswith(".csv"):
            continue
        p = os.path.join(DATA, f)
        try:
            rows = list(csv.DictReader(open(p, newline="", encoding="utf-8", errors="replace")))
        except Exception:
            continue
        cells = ""
        if rows and "batch" in rows[0]:
            cells = len({(r.get("batch") or "").strip() for r in rows if (r.get("batch") or "").strip()})
        out[f[:-4]] = (len(rows), cells)
    return out


# ---- which builders are kt-outline dependent -----------------------------------------------------
builders = collections.OrderedDict()
try:
    for r in csv.DictReader(open(PROV, newline="", encoding="utf-8", errors="replace")):
        stores = r.get("stores_read_by_builder", "") or ""
        if any(k in stores for k in KT_STORES) and r.get("builder"):
            builders.setdefault(r["builder"], set()).add(r["plot_id"])
except FileNotFoundError:
    sys.exit(f"missing {PROV} — run build_plot_provenance_20260809.py first")
print(f"kt-outline-dependent builders: {len(builders)}")

before = snapshot()
print(f"snapshot before: {len(before)} figure data CSVs\n")

# ---- 1. the KT chain regenerates the derived stores ------------------------------------------------
print("=== KT chain ===", flush=True)
t0 = time.time()
r = subprocess.run([sys.executable, "-u", f"{ROOT}/dataops/rerun_kt_chain_20260803.py"],
                   capture_output=True, text=True, cwd=f"{ROOT}/ablation_figures_20260625")
tail = [l for l in (r.stdout or "").splitlines() if l.strip()][-3:]
for l in tail:
    print("   " + l)
print(f"   chain rc={r.returncode} in {time.time()-t0:.0f}s\n")

# ---- 2. the remaining annotation-dependent builders -------------------------------------------------
SEARCH = [f"{ROOT}/ablation_figures_20260625", f"{ROOT}/ablation_plots/code"]
ok = fail = skip = 0
failed = []
print("=== other kt-outline-dependent builders ===", flush=True)
for name in sorted(builders):
    path = next((os.path.join(d, name) for d in SEARCH if os.path.isfile(os.path.join(d, name))), None)
    if not path:
        skip += 1
        continue
    # the chain already ran these
    if os.path.basename(path).startswith("kt_") and "ablation_figures" in path:
        continue
    t = time.time()
    rr = subprocess.run([sys.executable, "-u", path], capture_output=True, text=True,
                        cwd=os.path.dirname(path))
    if rr.returncode == 0:
        ok += 1
        print(f"   [ OK ] {name:56s} {time.time()-t:5.1f}s", flush=True)
    else:
        fail += 1
        failed.append((name, (rr.stderr or "").strip().splitlines()[-1:] or [""]))
        print(f"   [FAIL] {name:56s} {time.time()-t:5.1f}s", flush=True)
print(f"\n{ok} ok, {fail} failed, {skip} not found on disk")
for n, e in failed:
    print(f"   FAILED {n}: {e[0][:150]}")

# ---- 3. what actually moved -------------------------------------------------------------------------
after = snapshot()
print("\n=== FIGURES WHOSE DATA CHANGED ===")
moved = []
for pid, (nr, nc) in sorted(after.items()):
    b = before.get(pid)
    if b is None:
        moved.append((pid, "NEW", f"{nr} rows / {nc} cells")); continue
    if b != (nr, nc):
        moved.append((pid, f"{b[0]} rows / {b[1]} cells", f"{nr} rows / {nc} cells"))
gone = [p for p in before if p not in after]
if not moved and not gone:
    print("   nothing changed")
for pid, b, a in moved:
    print(f"   {pid[:52]:52s} {b:>26s}  ->  {a}")
if gone:
    print(f"\n   figures whose data CSV disappeared: {len(gone)}")
    for p in gone[:10]:
        print(f"      {p}")
print(f"\n{len(moved)} figures changed, {len(gone)} disappeared")
json.dump({"moved": moved, "gone": gone},
          open(f"{ROOT}/_claude_tmp/ktoutline_rerun_delta_20260809.json", "w"), indent=1)
print("delta -> /Volumes/4 MB/_claude_tmp/ktoutline_rerun_delta_20260809.json")
