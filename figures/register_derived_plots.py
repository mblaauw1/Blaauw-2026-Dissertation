"""Register DERIVED plots (trend-scaled companions, contact sheets, combined-trace plots) in PLOT_SETTINGS
so every deck plot has a filterable data CSV + SOURCE lineage — WITHOUT re-rendering the slow TIF scripts.
A derived plot replots (a subset of) a PARENT plot's points, so it points at the parent's data CSV; its
SOURCE is inherited from the parent. This keeps the 'built from plot spreadsheet, derived from source' tie."""
import json, os
BASE="/Volumes/4 MB/ablation_plots"; SP=f"{BASE}/PLOT_SETTINGS.json"
MASTER="/Volumes/4 MB/ABLATION_MASTER.csv"; KT="/Volumes/4 MB/annotations/kt_points.csv"
allset=json.load(open(SP)) if os.path.isfile(SP) else {}

# derived_plot -> (parent_plot_id_for_data, subset_note)
DERIVED={
 # trend-scaled companions replot their parent's exact points (different axes only) -> share parent CSV
 "G4_kt_intensity_time_trendscaled":("G4_kt_intensity_time","same points, axes fit to the trend"),
 "G4_plate_distance_time_trendscaled":("G4_plate_distance_time","same points, axes fit to the trend"),
 "G4_plate_distance_time_normalized_trendscaled":("G4_plate_distance_time_normalized","same points, axes fit"),
 "G4_plate_distance_tracking_trendscaled":("G4_plate_distance_tracking","same points, axes fit"),
 "G4_fluor_over_time_trendscaled":("G4_fluor_over_time","same points, trend only, axes fit"),
 # contact sheets = every individual ablation in the parent measurement CSV
 "G4_frap_individual_contactsheet":("G4_frap","one panel per FRAP ablation (all sequences)"),
 "G4_frap_both_individual_contactsheet":("G4_frap","one panel per ablation, targeted+sister"),
 "G4_ablation_individual_contactsheet":("G4_ablation_intensity","one panel per successful ablation"),
 # combined-trace plots = a SELECTED SUBSET of the parent measurement CSV (filter parent by the pick list)
 "G4_ablation_intensity_combined":("G4_ablation_intensity","selected picks (see settings.picks)"),
 "G4_ablation_intensity_selected_combined":("G4_ablation_intensity","selected successful-ablation picks"),
 "G4_frap_both":("G4_frap","all ablations, targeted+sister each start=1"),
 "G4_frap_both_combined":("G4_frap","selected picks, both-normalized"),
 # duration combined = the four per-cohort duration violins (each has its own G2_dur_* CSV)
 "G2_duration_combined":("G2_dur_meta_to_ana","4-panel; other panels: G2_dur_align_to_meta / _neb_to_meta / _ana_to_cyto"),
 # helper
 "G1_roundness_traces":("G1_roundness_combined","per-cell roundness traces feeding the combined plot"),
}
# Fix the SOURCE of existing plots that actually derive from the annotation spreadsheets (not just master),
# so the lineage/staleness check watches the RIGHT source. (default record_plot source is [MASTER].)
OUT_C="/Volumes/4 MB/annotations/cell_outlines.csv"; PLATE="/Volumes/4 MB/annotations/SISTERLESS_PLATE_JOIN_TIMES.csv"
SRC_FIX={  # plot_id substring -> the source files it truly derives from
 "frap":[KT], "ablation_intensity":[KT], "cdc20":[KT], "kt_intensity":[KT], "oscillation":[KT],
 "plate_distance":[KT], "distance_vs_fluor":[KT], "velocity":[KT], "prepost":[KT],
 "lagging_position":[KT], "lagging_shape":[KT], "kk_distance":[MASTER,KT], "chromo_length":[MASTER,KT],
 "origin_position":[MASTER,KT], "plate_join":[PLATE,MASTER], "kt_fate":[PLATE,MASTER],
 "congression":[PLATE,MASTER], "roundness":[MASTER,OUT_C], "area":[MASTER,OUT_C],
 "start_rounded":[MASTER,OUT_C],
}
fixed=0
for pid,info in list(allset.items()):
    cur=info.get("source",{}).get("files",[])
    if cur and cur!=[MASTER]: continue      # already has a specific source
    for kw,files in SRC_FIX.items():
        if kw in pid.lower():
            mt={f:(round(os.path.getmtime(f),1) if os.path.isfile(f) else None) for f in files}
            info.setdefault("source",{}).update({"files":files,"mtimes_at_build":mt,
                                                 "key_column":info.get("source",{}).get("key_column","batch")})
            fixed+=1; break
print(f"corrected source lineage on {fixed} existing plots (declare kt_points/outlines/plate as source)")
n=0
for pid,(parent,note) in DERIVED.items():
    if pid in allset and allset[pid].get("source",{}).get("files"): continue  # already has real lineage
    pinfo=allset.get(parent,{})
    pdata=pinfo.get("data",f"data/{parent}.csv")
    psrc=pinfo.get("source",{}) or {"files":[MASTER],"key_column":"batch"}
    allset[pid]={"caption":f"[derived] {pid}","settings":{"derived_from":parent,"note":note},
                 "n_rows":pinfo.get("n_rows",0),"data":pdata,"code":pinfo.get("code",""),
                 "source":{"files":psrc.get("files",[MASTER]),
                           "mtimes_at_build":psrc.get("mtimes_at_build",{}),
                           "key_column":psrc.get("key_column")},
                 "derived_from":parent}
    n+=1
# any remaining plot without a source (cohort/violin plots recorded before the lib change) derives from the
# MASTER — declare it so the whole set has lineage.
dflt=0
for pid,info in allset.items():
    if not info.get("source",{}).get("files"):
        info["source"]={"files":[MASTER],
                        "mtimes_at_build":{MASTER:(round(os.path.getmtime(MASTER),1) if os.path.isfile(MASTER) else None)},
                        "key_column":info.get("source",{}).get("key_column","batch")}
        dflt+=1
print(f"defaulted {dflt} remaining plots to MASTER source")
# Re-baseline hashes_at_build to CURRENT normalized-data hashes. This runs at the END of a full re-render
# (build_pdfs_feedback chain), when every plot IS current with the source, so it establishes a clean baseline;
# only source edits made AFTER the chain will then flag stale. Uses lib.source_hash (normalized: immune to the
# annotation servers' whitespace/row-order re-serialization, sensitive to real data edits).
import sys as _sys; _sys.path.insert(0,"/Volumes/4 MB/ablation_figures_20260625")
import lib as _lib
_hc={}; _hb=0
for pid,info in allset.items():
    src=info.get("source",{})
    if src.get("files"):
        src["hashes_at_build"]={f:_hc.setdefault(f,_lib.source_hash(f)) for f in src["files"]}; _hb+=1
print(f"re-baselined normalized-data hashes on {_hb} plots (clean baseline post-render)")
_tmp=f"{SP}.reg.tmp"; json.dump(allset,open(_tmp,"w"),indent=1); os.replace(_tmp,SP)
print(f"registered {n} derived plots (share parent data CSV + inherit source lineage)")
# refresh the human-readable lineage from the merged allset
inv={}
for pid,info in allset.items():
    for s in info.get("source",{}).get("files",[]): inv.setdefault(s,[]).append(pid)
with open(f"{BASE}/PLOT_LINEAGE.md","w") as f:
    f.write("# Source-spreadsheet -> plot lineage (incl. derived plots)\n\n")
    for s in sorted(inv): f.write(f"## {s}\n"+"".join(f"- {p}\n" for p in sorted(inv[s]))+"\n")
print("PLOT_LINEAGE.md refreshed")
