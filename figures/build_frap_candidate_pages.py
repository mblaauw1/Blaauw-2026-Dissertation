"""Extra FRAP candidate pages (user 2026-07-15: "the ones shown now aren't ideal … two more candidate pngs for
~18 total"). Keeps the existing frap_candidates.png (page 1) and adds frap_candidates_2/3.png by STACKING
already-rendered per-cell FRAP strips (group1/frap_timestrips/<batch>_frap0.png) via candidate_compose — no
re-render. Picks valid (non-drug, non-excluded) cells not already on page 1, spread across dates for variety."""
import sys; sys.path.insert(0,"/Volumes/4 MB/ablation_figures_20260625")
import lib, glob, os, candidate_compose
OUT="/Volumes/4 MB/ablation_figures_20260625/group1/frap_timestrips"
data,_=lib.load_master()
name_by_stem={r["Batch Name"].replace(" ","_"):r["Batch Name"] for r in data}
PAGE1=["20250411 ptk_yfpcdc20_13","20260417 ptk2 eyfp cdc20 ablation_18",
       "20250826 test_ablation_14","20250402 ptk_yfpcdc20_2","20250409 ptk_yfpcdc20_6"]
strips={}
for p in sorted(glob.glob(f"{OUT}/*_frap0.png")):
    b=os.path.basename(p)
    if "_aligned" in b or "_notext" in b: continue
    stem=b[:-len("_frap0.png")]
    batch=name_by_stem.get(stem)
    if not batch or batch in PAGE1: continue
    if lib.plot_excluded(batch): continue          # drop drug / Exclude=Yes / REVIEW_EXCLUDE
    strips.setdefault(batch,p)
cells=sorted(strips)
# spread evenly across the pool for date/type variety, then take 12 -> two pages of 6
if len(cells)>12:
    step=len(cells)/12.0
    cells=[cells[int(i*step)] for i in range(12)]
pages=[cells[:6],cells[6:12]]
for i,pg in enumerate(pages,start=2):
    items=[(b,strips[b]) for b in pg]
    n=candidate_compose.compose(items, f"{OUT}/frap_candidates_{i}.png",
                                sup_title=f"FRAP candidates (page {i}) - pick one")
    print(f"frap_candidates_{i}.png: {n} candidates -> "+", ".join(pg))
print(f"total FRAP candidates now: {len(PAGE1)} (page1) + {sum(len(p) for p in pages)} (new) = {len(PAGE1)+sum(len(p) for p in pages)}")
