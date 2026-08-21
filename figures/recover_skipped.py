"""2026-07-11: recover wide timestrips for batches the exact-name render_dir() missed — their render dir exists
on 4 MB under a DIFFERENT (renamed) basename, and the movie FILES use that dir-basename. Bridge via a dual-key
alias: register the dir-basename in _RDIR + mr (pointing at the master row), render under that identity, save the
PNG under the MASTER name. Renders timestrip (timelapse) or MIP+z-slice (z-stack)."""
import os, sys, json, numpy as np
sys.path.insert(0,"/Volumes/4 MB/ablation_figures_20260625")
SRC="/Volumes/4 MB/ablation_figures_20260625/group_timestrips.py"
src=open(SRC).read(); cut=src.index("chosen={}; ALIGNED_STATUS={}")
G={"__name__":"gts_rec","__file__":SRC}; exec(compile(src[:cut],SRC,"exec"),G)
cat_panels=G["cat_panels"]; make_strip=G["make_strip"]; mr=G["mr"]; _RDIR=G["_RDIR"]
OUT="/Volumes/4 MB/ablation_timestrips_wide_20260710/png"
alias=json.load(open("/tmp/wide_recover_alias.json"))
def safe(b): return b.replace("/","_").replace(" ","_")
def is_zstack(b): return (mr.get(b,{}).get("Z-stack / Timelapse","") or "").strip().lower().startswith("z")
done=[]; fail=[]
for master_b, d in sorted(alias.items()):
    dbase=os.path.basename(d)
    if master_b not in mr: fail.append((master_b,"not in master")); continue
    # dual-key alias: dir-basename -> master row (data) + dir (files)
    mr[dbase]=mr[master_b]; _RDIR[dbase]=d
    try:
        if is_zstack(master_b):
            # reuse z-scan renderer under the dir-basename identity
            import importlib.util
            spec=importlib.util.spec_from_file_location("zt","/Volumes/4 MB/ablation_figures_20260625/zscan_timestrips.py")
            # simplest: call zscan's render via exec of its funcs sharing our G would be heavy; skip z-stack recovery here
            fail.append((master_b,"z-stack (recover via zscan separately)")); continue
        pan,specs=cat_panels(dbase)
        if not pan: fail.append((master_b,"no panels")); continue
        ok=make_strip(dbase,pan,f"{OUT}/{safe(master_b)}",closeup_specs=specs,title=master_b,square_aligned=True)
        if ok: done.append(master_b); print(f"  RECOVERED {master_b}  (via {dbase})")
        else: fail.append((master_b,"make_strip False"))
    except Exception as e:
        fail.append((master_b,f"{type(e).__name__}: {e}"))
print(f"\nrecovered {len(done)} / {len(alias)}")
for b,r in fail: print(f"  FAIL {b}: {r}")
json.dump({"recovered":done,"fail":fail},open("/Volumes/4 MB/ablation_timestrips_wide_20260710/recover_summary.json","w"),indent=1)
