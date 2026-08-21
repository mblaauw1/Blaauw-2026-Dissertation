"""Run the NEWEST TrackMate (per-frame merge + density-adaptive targetspf) on the 2/3-sisterless on-target
cohort, output to 4 MB (5 MB is unmounted), and update KT_TRACKING_MASTER so the multi-KT markup tool's
snapping resolves. Reuses kt_track_prep.build_stack + kt_finalize.finalize. Run in background.
"""
import os, sys, csv, glob, json, subprocess, datetime
sys.path.insert(0, "/Users/mblaauw/ablation-pipeline/kt_tracking")
import kt_track_prep as prep, kt_finalize as fin

# ---- redirect all output to 4 MB (mounted) ----
BASE = "/Volumes/4 MB/kt_tracking"
STACKS = os.path.join(BASE, "stacks"); RES = os.path.join(BASE, "results")
os.makedirs(STACKS, exist_ok=True); os.makedirs(RES, exist_ok=True)
prep.STACKS = STACKS; prep.OUT_BASE = BASE
fin.RES = RES
FIJI = "/Users/mblaauw/Downloads/Fiji/fiji"
GROOVY = "/Users/mblaauw/ablation-pipeline/kt_tracking/kt_trackmate.groovy"
MASTER = "/Volumes/4 MB/ABLATION_MASTER.csv"
KTM = "/Volumes/4 MB/annotations/KT_TRACKING_MASTER.csv"
# newest-version params
P = dict(diameter=0.5, quality=-1, linkdist=0.8, gapdist=1.0, maxgap=2, minTrackSpots=3, mergedist=0.5, targetspf=5)

def anaphase_of(name):
    rows = list(csv.reader(open(MASTER))); hdr=[h.strip() for h in rows[1]]; ci={h:i for i,h in enumerate(hdr)}
    ai = ci.get("Anaphase Onset (s)")
    for r in rows[2:]:
        if r and r[0].strip()==name:
            v = r[ai].strip() if ai is not None and ai<len(r) else ""
            s = prep.hms_to_sec(v) if v else None
            return s
    return None

def run_fiji(stk):
    base = os.path.basename(stk).replace("_KTmon.tif","")
    args = "imgPath='%s',outDir='%s'," % (stk, RES) + ",".join(f"{k}={v}" for k,v in P.items())
    blog = os.path.join(BASE, "logs", f"track_{base}.log"); os.makedirs(os.path.dirname(blog), exist_ok=True)
    with open(blog,"w") as lf:
        subprocess.run([FIJI,"--headless","--run",GROOVY,args], stdout=lf, stderr=subprocess.STDOUT, timeout=1200)
    return base, blog

def update_master(base, summ):
    rows=list(csv.reader(open(KTM))); hdr=rows[0]
    idx={h:i for i,h in enumerate(hdr)}
    batch = base  # kt_track_id form
    # find the real batch name (spaces) = base with first underscore group kept; match by kt_track_id col
    newrow={h:"" for h in hdr}
    newrow.update({"batch":summ.get("batch_display",base),"kt_track_id":base,
        "n_tracks":summ.get("n_tracks",""),"n_spots":summ.get("n_spots",""),
        "median_kt_speed_um_per_min":summ.get("median_kt_speed_um_per_min",""),
        "spots_timed_csv":base+".spots_timed.csv","tracks_timed_csv":base+".tracks_timed.csv",
        "overlay_mp4":"","trackmate_xml":base+".trackmate.xml","results_dir":RES})
    out=[r for r in rows if not (len(r)>idx["kt_track_id"] and r[idx["kt_track_id"]]==base)]
    out.append([newrow[h] for h in hdr])
    tmp=KTM+".tmp"; csv.writer(open(tmp,"w",newline="")).writerows(out); os.replace(tmp,KTM)

def main():
    cohort=[l.strip() for l in open(os.path.join(BASE,"cohort_23sis.txt")) if l.strip()]
    log=open(os.path.join(BASE,"logs","multi23_run.log"),"w")
    def pr(m): log.write(m+"\n"); log.flush(); print(m, flush=True)
    pr(f"=== 2/3-sisterless newest-TrackMate run ({datetime.datetime.now()}) — {len(cohort)} batches, params {P} ===")
    ok=built=skip=0
    for i,name in enumerate(cohort,1):
        base=name.replace(" ","_"); stk=os.path.join(STACKS, base+"_KTmon.tif")
        ana=anaphase_of(name)
        cutoff_ana = ana if ana is not None else 1e9   # no anaphase reviewed -> full monitoring
        if not os.path.isfile(stk):
            path,msg=prep.build_stack(name, cutoff_ana)
            if not path: pr(f"[{i}/{len(cohort)}] SKIP {name} :: {msg}"); skip+=1; continue
            built+=1
        base,blog=run_fiji(stk)
        sc=os.path.join(RES, base+".spots.csv")
        if not os.path.isfile(sc): pr(f"[{i}/{len(cohort)}] FIJI-NO-OUTPUT {name} (see {blog})"); continue
        summ=fin.finalize(sc) or {}
        summ["batch_display"]=name
        update_master(base, summ)
        pr(f"[{i}/{len(cohort)}] OK {name}: tracks={summ.get('n_tracks')} spots={summ.get('n_spots')}")
        ok+=1
    pr(f"=== DONE: {ok} tracked, {built} stacks built, {skip} skipped -> {RES} ; KT_TRACKING_MASTER updated ===")

if __name__=="__main__": main()
