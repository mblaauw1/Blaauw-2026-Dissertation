"""Wide square-aligned timestrip build (2026-07-10, user autonomous task).
Renders a square-aligned timestrip for EVERY eligible batch (selection in /tmp/wide_eligible.json, derived from
the master's Cell Type + Exclude + Phase-of-Ablations columns). Reuses group_timestrips.py's EXACT method
(cat_panels + make_strip(square_aligned=True)) by exec-ing only its function/data definitions — the module's
heavy curated-example driver loop is NOT run (we cut the source before it). Separate deliverable: does NOT touch
the current .ai figure set. Serialized (single exFAT drive). Resumable (skips already-rendered). Robust per-batch.
"""
import os, sys, json, time, traceback
sys.path.insert(0,"/Volumes/4 MB/ablation_figures_20260625")
SRC="/Volumes/4 MB/ablation_figures_20260625/group_timestrips.py"
src=open(SRC).read()
cut=src.index("chosen={}; ALIGNED_STATUS={}")   # everything before = defs + data loads (no driver loop)
G={"__name__":"gts_wide","__file__":SRC}
exec(compile(src[:cut],SRC,"exec"),G)
cat_panels=G["cat_panels"]; make_strip=G["make_strip"]; render_dir=G["render_dir"]; mr=G["mr"]

OUTDIR="/Volumes/4 MB/ablation_timestrips_wide_20260710"
PNGDIR=OUTDIR+"/png"; os.makedirs(PNGDIR,exist_ok=True)
LOG=OUTDIR+"/build.log"
elig=json.load(open("/tmp/wide_eligible.json"))
TESTN=int(os.environ.get("WIDE_TESTN","0"))
if TESTN: elig=elig[:TESTN]
def safe(b): return b.replace("/","_").replace(" ","_")
def logline(s):
    with open(LOG,"a") as f: f.write(s+"\n")
    print(s,flush=True)

done=[]; skipped=[]; failed=[]
logline(f"=== WIDE BUILD START {time.strftime('%Y-%m-%d %H:%M:%S')}  eligible={len(elig)} ===")
t0=time.time()
for i,b in enumerate(elig):
    prefix=f"{PNGDIR}/{safe(b)}"
    if os.path.exists(prefix+".png"):
        done.append(b); continue
    if not render_dir(b):
        skipped.append([b,"no render dir on 4 MB"]); continue
    try:
        pan,specs=cat_panels(b)
        if not pan:
            skipped.append([b,"no panels (no ablation events / no monitoring range)"]); continue
        ok=make_strip(b,pan,prefix,closeup_specs=specs,title=b,square_aligned=True)
        if ok: done.append(b)
        else: skipped.append([b,"make_strip returned False (no readable movies/frames/outline)"])
    except Exception as e:
        failed.append([b, f"{type(e).__name__}: {e}"])
        logline(f"  FAIL {b}: {type(e).__name__}: {e}")
    if (i+1)%20==0:
        el=time.time()-t0; rate=(i+1)/el
        eta=(len(elig)-(i+1))/rate/60 if rate>0 else 0
        logline(f"{time.strftime('%H:%M:%S')} {i+1}/{len(elig)} done={len(done)} skip={len(skipped)} fail={len(failed)} | {rate*60:.1f}/min ETA {eta:.0f}min")
        json.dump({"done":done,"skipped":skipped,"failed":failed,"progress":f"{i+1}/{len(elig)}"},
                  open(OUTDIR+"/build_summary.json","w"),indent=1)
json.dump({"done":done,"skipped":skipped,"failed":failed,"progress":"COMPLETE"},
          open(OUTDIR+"/build_summary.json","w"),indent=1)
logline(f"=== WIDE BUILD DONE {time.strftime('%H:%M:%S')}  rendered={len(done)} skipped={len(skipped)} failed={len(failed)} ===")
