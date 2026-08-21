#!/usr/bin/env python3
"""Join scraped acquisition settings to CELL TYPE and write the Methods-ready exposure table.

Sidecar -> raw file name -> (date, source_file) in RAW_FILE_MAP_20260818.csv -> cell(s) -> master
Cell Type.  Where the map has no row (files never mapped, e.g. calibration or unbatched acquisitions)
the row is still reported, under cell type "(unmapped)", so nothing is silently dropped.
"""
import csv, io, os, sys, collections, statistics as stt
sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625"); import lib

RAW = "/Volumes/4 MB/_claude_tmp/methods_20260818/EXPOSURES_RAW.csv"
MAP = "/Volumes/4 MB/4_TABLES_AND_REPORTS/RAW_FILE_MAP_20260818/RAW_FILE_MAP_20260818.csv"
OUTDIR = "/Volumes/4 MB/4_TABLES_AND_REPORTS/METHODS_20260818"
os.makedirs(OUTDIR, exist_ok=True)

def rd(p):
    with io.open(p, encoding="utf-8", errors="replace") as f: return list(csv.DictReader(f))

M, HDR = lib.load_master()
MB = {r["Batch Name"].strip(): r for r in M if (r.get("Batch Name") or "").strip()}
rows = rd(RAW)
m = rd(MAP)
bykey = {}
for r in m:
    bykey[(r["date"].strip(), r["source_file"].strip())] = r

def cells_for(date, raw):
    r = bykey.get((date, raw))
    if not r: return []
    return [c.strip() for c in (r.get("cells") or "").split(";") if c.strip()]

def celltype(b):
    r = MB.get(b)
    return ((r or {}).get("Cell Type") or "").strip() or "(unknown)"

out = []
for r in rows:
    cs = cells_for(r["date"], r["raw_file"])
    cts = sorted({celltype(c) for c in cs}) or ["(unmapped)"]
    for ct in cts:
        out.append(dict(cell_type=ct, date=r["date"], raw_file=r["raw_file"],
                        channel_index=r["channel_index"], channel_name=r["channel_name"],
                        ttl_state=r["ttl_state"], exposure_ms=r["exposure_ms"],
                        interval_ms=r["interval_ms"], pixel_um=r["pixel_um"], binning=r["binning"],
                        camera=r["camera"], z_step_um=r["z_step_um"],
                        n_planes=r["n_planes_this_combo"], n_cells=len(cs),
                        cells=";".join(cs[:4])))
with open(OUTDIR + "/EXPOSURES_BY_CELLTYPE.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(out[0].keys())); w.writeheader(); w.writerows(out)

# ------------------------------------------------------------------ summary the Methods can quote
def f(x):
    try: return float(x)
    except Exception: return None

agg = collections.defaultdict(lambda: collections.defaultdict(list))   # (celltype, channel) -> {}
for r in out:
    e = f(r["exposure_ms"]); n = int(f(r["n_planes"]) or 0)
    if e is None: continue
    k = (r["cell_type"], r["channel_name"] or f"ch{r['channel_index']}")
    agg[k]["exp"] += [e] * max(1, min(n, 500))
    iv = f(r["interval_ms"])
    if iv: agg[k]["int"].append(iv)
    px = f(r["pixel_um"])
    if px: agg[k]["px"].append(px)
    agg[k]["files"].append(r["raw_file"])

summ = []
for (ct, ch), d in sorted(agg.items()):
    e = d["exp"]
    summ.append(dict(cell_type=ct, channel=ch, n_files=len(set(d["files"])),
                     exposure_ms_median=round(stt.median(e), 1),
                     exposure_ms_min=round(min(e), 1), exposure_ms_max=round(max(e), 1),
                     exposure_ms_values=";".join(str(v) for v in sorted(set(round(x, 1) for x in e))[:8]),
                     interval_s_median=round(stt.median(d["int"]) / 1000, 1) if d["int"] else "",
                     interval_s_min=round(min(d["int"]) / 1000, 1) if d["int"] else "",
                     interval_s_max=round(max(d["int"]) / 1000, 1) if d["int"] else "",
                     pixel_um_values=";".join(str(v) for v in sorted(set(d["px"]))[:4]) if d["px"] else ""))
with open(OUTDIR + "/EXPOSURES_SUMMARY.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(summ[0].keys())); w.writeheader(); w.writerows(summ)

print(f"rows={len(out)}  cell-type x channel combinations={len(summ)}")
print(f"{'cell type':34s} {'channel':22s} files  exposure ms (med/min-max)   interval s (med/range)")
for s in summ:
    if s["n_files"] < 2: continue
    print(f"{s['cell_type'][:33]:34s} {s['channel'][:21]:22s} {s['n_files']:5d}  "
          f"{s['exposure_ms_median']:>6} / {s['exposure_ms_min']}-{s['exposure_ms_max']:<8}  "
          f"{s['interval_s_median']} / {s['interval_s_min']}-{s['interval_s_max']}")
print(f"\n[done] -> {OUTDIR}/EXPOSURES_BY_CELLTYPE.csv + EXPOSURES_SUMMARY.csv")
