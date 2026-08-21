"""TrackMate detector iteration 1: mergedist 0.5 -> 1.2um (collapse a stretched KT's multiple LoG detections
into ONE spot, fixing the '1 polar KT -> 2/3 spots' problem; sister k-k ~2.5um stays separate). Re-tracks the
11 annotated triples into results_iter1/ so it can be scored against the manual KT marks WITHOUT touching the
live tracks."""
import os, subprocess, datetime
BASE="/Volumes/4 MB/kt_tracking"
STACKS=os.path.join(BASE,"stacks"); RES=os.path.join(BASE,"results_iter1"); LOG=os.path.join(BASE,"logs")
os.makedirs(RES,exist_ok=True); os.makedirs(LOG,exist_ok=True)
FIJI="/Users/mblaauw/Downloads/Fiji/fiji"
GROOVY="/Users/mblaauw/ablation-pipeline/kt_tracking/kt_trackmate.groovy"
P=dict(diameter=0.5,quality=-1,linkdist=0.8,gapdist=1.0,maxgap=2,minTrackSpots=3,mergedist=1.2,targetspf=5)  # <-- mergedist bumped
batches=[l.strip() for l in open(os.path.join(BASE,"iter1_batches.txt")) if l.strip()]
lg=open(os.path.join(LOG,"iter1_run.log"),"w")
def pr(m): lg.write(m+"\n"); lg.flush(); print(m,flush=True)
pr(f"=== TrackMate iter1 (mergedist={P['mergedist']}) {datetime.datetime.now()} — {len(batches)} batches ===")
ok=0
for i,b in enumerate(batches,1):
    stk=os.path.join(STACKS, b.replace(" ","_")+"_KTmon.tif")
    if not os.path.isfile(stk): pr(f"[{i}] MISSING stack {b}"); continue
    args="imgPath='%s',outDir='%s',"%(stk,RES)+",".join(f"{k}={v}" for k,v in P.items())
    base=b.replace(" ","_")
    blog=os.path.join(LOG,f"iter1_{base}.log")
    with open(blog,"w") as f:
        subprocess.run([FIJI,"--headless","--run",GROOVY,args],stdout=f,stderr=subprocess.STDOUT,timeout=1200)
    # pull the spots/tracks summary line
    line=""
    for L in open(blog,errors='ignore'):
        if "spots," in L and "tracks" in L: line=L.strip()
    pr(f"[{i}/{len(batches)}] {b}: {line[-60:] if line else 'NO OUTPUT'}")
    ok+=1
pr(f"=== DONE: {ok} tracked -> {RES} ===")
