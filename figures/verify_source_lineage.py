"""SOURCE-LINEAGE VERIFIER. Each plot's data CSV ('plot spreadsheet') is DERIVED FROM one or more SOURCE
spreadsheets (the master / annotation CSVs). record_plot stamps the source mtimes at build time; this script
compares them to the CURRENT source mtimes and flags any plot whose source changed since the plot was built —
i.e. a source edit (rows added/updated) that has NOT yet been re-derived into the plot. Run after editing the
master or annotations to see exactly which plots must be regenerated."""
import json, os, datetime
BASE="/Volumes/4 MB/ablation_plots"
SP=f"{BASE}/PLOT_SETTINGS.json"
def hm(t): return datetime.datetime.fromtimestamp(t).strftime("%m-%d %H:%M") if t else "—"
def run():
    if not os.path.isfile(SP):
        print("no PLOT_SETTINGS.json"); return 0
    allset=json.load(open(SP))
    stale=[]; nolineage=[]; missing_csv=[]
    for pid,info in sorted(allset.items()):
        csv=f"{BASE}/{info.get('data','')}"
        if not os.path.isfile(csv): missing_csv.append(pid); continue
        csv_mt=os.path.getmtime(csv)
        src=info.get("source")
        if not src or not src.get("files"): nolineage.append(pid); continue
        # STALE = the source file's CONTENT changed since this plot was built. Content HASH is authoritative
        # (an annotation-server autosave bumps mtime without changing data; a hash ignores that). Falls back
        # to mtime only when no hash was recorded (older builds).
        hashes=src.get("hashes_at_build",{}) or {}
        import sys as _sys; _sys.path.insert(0,"/Volumes/4 MB/ablation_figures_20260625")
        import lib as _lib
        for f in src.get("files",[]):
            if not os.path.isfile(f): continue
            cur_hash=_lib.source_hash(f)
            stamped_hash=hashes.get(f)
            if stamped_hash is not None:
                if cur_hash!=stamped_hash:
                    stale.append((pid,os.path.basename(f),"content changed","hash mismatch",hm(csv_mt))); break
            else:
                stamped_mt=src.get("mtimes_at_build",{}).get(f)
                if stamped_mt and os.path.getmtime(f)>stamped_mt+1:
                    stale.append((pid,os.path.basename(f),hm(os.path.getmtime(f)),hm(stamped_mt),hm(csv_mt))); break
    print(f"=== SOURCE LINEAGE ({len(allset)} plots) ===")
    print(f"\n[STALE vs SOURCE] source edited since plot built -> REGENERATE: {len(stale)}")
    for pid,f,cur,stamped,csvm in stale:
        print(f"   {pid}: source {f} changed ({cur}) after build (stamp {stamped}, csv {csvm})")
    print(f"\n[NO LINEAGE RECORDED] (older record_plot / no source): {len(nolineage)}")
    for p in nolineage: print(f"   {p}")
    print(f"\n[DATA CSV MISSING]: {len(missing_csv)}")
    for p in missing_csv: print(f"   {p}")
    ok=not stale and not missing_csv
    print(f"\n=== {'ALL PLOTS IN SYNC WITH THEIR SOURCE' if ok else 'ACTION NEEDED (above)'} ===")
    return len(stale)
if __name__=="__main__":
    run()
