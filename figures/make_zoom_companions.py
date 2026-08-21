#!/usr/bin/env python3
"""FIX_PLAN 12c — outlier-cleaned '_zoom' COMPANION plots.

For EVERY plot in the figure set (enumerated from ablation_plots/PLOT_SETTINGS.json), read its recorded
data CSV, reconstruct the PLOTTED y-values, and test whether a few extreme points stretch the y-axis so the
bulk is crushed (robust IQR fence via lib.zoom_trim). When they do, write an OUTLIER-TRIMMED companion:

  * <plot_id>_zoom.png  written ALONGSIDE the original group{N}/<plot_id>.png  (never overwrites v1)
  * data/<plot_id>_zoom.csv  the same rows with a `zoom_outlier_removed` flag column (kept in sync)
  * every removed point/batch logged to the review list (reason 'outlier trimmed for zoom companion')

v1 (the original) is left untouched — it already carries the user's definitive remove-everywhere points.
The v2 trims here are COMPANION-ONLY readability trims. Re-runnable: `python3 make_zoom_companions.py`.

Removed points appear as hollow (open) markers placed ON the trend (interpolated from the retained neighbours
onto the line/scatter at the point's OWN x; strip plots have no x-trend, so they sit just above the group's
retained data edge) = the missing-point convention. Never pinned to the top/bottom axis frame.
Whole batches that are ENTIRELY outliers are flagged as a batch (not per-point).
"""
import os, csv, json, sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.lines as mlines
import lib

FIG="/Volumes/4 MB/ablation_figures_20260625"
PLOTS="/Volumes/4 MB/ablation_plots"
DATA=f"{PLOTS}/data"
REVIEW_OUT=f"{FIG}/_review/zoom_companion_review.csv"
lib.apply_style()

# ---- column-role vocabularies -------------------------------------------------------------------
# time / index / x-position columns — never the distortion target, never rendered as the trimmed axis
X_TIME={"t_min","t_sec","rel_time_s","time_from_ablation_s","time_s","x","frac_meta_to_ana",
        "t_min_from_meta","t_min_since_first_abl","panel_t_sec","frame","t_since_ana_min",
        "t_since_ana_s","time"}
# pure identifiers / counts / frame indices — not plotted metrics
ID_COLS={"batch","track","ann_id","chromosome","kt","abl_pre_frame","flash_tif_pos","tif_pos",
         "is_pre_ablation","seq","frap_seq","abl_seq","n_frames","n_sisterless","n_pairs",
         "n_chromosomes","n_seen","n_reached_plate","n","N","n_yes","n_no","n_neither","n_other",
         "frame_gap","censored","in_metaphase_at_start","is_hole_marker","off_scale","present",
         # counts, not metrics - picking one as y makes the outlier scan test the wrong column and
         # report "no distorting outliers" for a plot whose actual metric has a long tail (2026-07-29:
         # G4_sisterless_cdc20_vs_bleaching scanned n_plate_kt instead of paired_plate_kt_pct_per_min).
         "n_plate_kt","n_polar_kt","n_kt","n_tracks","n_outlines","n_points","n_cells","n_batches"}
GROUP_COLS=["cohort","group","phase","series","location","marker","kt_type","sisterless_group",
            "panel","fate"]
# skip whole plot when its settings.type contains any of these (no continuous y-axis to distort)
SKIP_TYPE_KW=["timestrip","significance matrix","correlation table","statgrid","bar","km-style",
              "km ","dumbbell","z-stack","zstack","point + 95","fraction-congressed","stacked bar",
              "significance","mip","dot-intensity",
              # 2026-07-11 (user): multi-metric / per-track plots have NO single continuous y-axis for the generic
              # single-column zoom — it mis-picked area_um2 for the 2-panel length+aspect G4_lagging_shape and drew
              # only hollow outlier markers ("all-hollow"). Skip; build a proper per-panel zoom in-builder if wanted.
              "tracks tied","shape vs time"]
SKIP_ID_SUFFIX=("_statgrid",)
SKIP_IDS={"G2_metaphase_ablated",       # USER 2026-07-16: keep ALL points; _zoom = full parent
          # USER 2026-07-30: "G4_fluor_vs_duration_zoom scale from 0-1, and add trendline and legend as in
          # G4_fluor_vs_duration_scaled01". The generic zoom companion cannot do that - it re-plots the
          # parent's raw axis with outliers trimmed. group4_fluor.py now BUILDS this figure itself, so the
          # generic builder must not overwrite it.
          "G4_fluor_vs_duration",
          # USER 2026-08-04 (ITEM 31): "rename x-axis on this for clarity as right now it says there are two
          # panels but there's just one". The real fault is worse than the label: the parent's data CSV pools
          # panel A (ablation->NEBD) and panel B (ablation->metaphase) into one `x_min` column separated by a
          # '--B--' marker row, which this generic builder ignores -- so the single-panel zoom plotted two
          # DIFFERENT quantities on one axis. group2_prophase_dynamics.py now builds a panel-B-only zoom with
          # the correct axis title; the generic builder must not overwrite it.
          "G2_prophase_dynamics"}

def is_num(s):
    try: float(s); return True
    except (TypeError,ValueError): return False

def load_csv(pid):
    p=f"{DATA}/{pid}.csv"
    if not os.path.isfile(p): return None,None,None
    with open(p) as f:
        r=csv.reader(f); hdr=next(r,None)
        rows=[row for row in r if row]
    return p,hdr,rows

def numeric_metric_cols(hdr,rows):
    """columns that are numeric in >=80% of rows AND are candidate PLOT METRICS (not id/time)."""
    out=[]
    for i,c in enumerate(hdr):
        vals=[row[i] for row in rows if i<len(row)]
        if not vals: continue
        nnum=sum(is_num(v) for v in vals)
        if nnum < 0.8*len(vals): continue
        if c in ID_COLS or c in X_TIME: continue
        # A GROUPING column is never the plotted metric. `cohort` holds 1/2/3, passes the numeric
        # test, and was being chosen as y for the intensity plots - so the outlier scan ran on
        # "max 3 vs p95 3", found nothing, and silently stopped emitting their _zoom companions while
        # PRE-FIX _zoom figures stayed placed in the deck (found 2026-07-29).
        if c in GROUP_COLS: continue
        out.append(c)
    return out

def col_floats(hdr,rows,c):
    i=hdr.index(c)
    return np.array([float(row[i]) if i<len(row) and is_num(row[i]) else np.nan for row in rows])

def first_present(hdr,cands):
    for c in cands:
        if c in hdr: return c
    return None

def group_dir(pid):
    g=pid[1] if len(pid)>1 and pid[0]=="G" and pid[1].isdigit() else None
    return f"{FIG}/group{g}" if g else FIG

# ---- special raw-sum plots: reconstruct the NORMALIZED plotted y from raw sums ------------------
def frap_plotted(hdr,rows):
    """G4_frap main: per (batch,frap_seq) ratio targeted/sister, normalized so pre-ablation=1.
    Mirrors v1 exclusions: drop the whole sequence if max|Q|>8 (residual-spike rule in the builder),
    so the companion starts from EXACTLY the set v1 plots, then trims the readability tail on top."""
    idx={c:hdr.index(c) for c in hdr}
    xs,ys,batches=[],[],[]
    from collections import defaultdict
    seqs=defaultdict(list)
    for row in rows:
        seqs[(row[idx["batch"]],row[idx["frap_seq"]])].append(row)
    for (b,s),rs in seqs.items():
        rs=sorted(rs,key=lambda r:float(r[idx["rel_time_s"]]))
        base=next((r for r in rs if r[idx["is_pre_ablation"]]=="1"),rs[0])
        tb=float(base[idx["targeted_bgsub_sum"]]); sb=float(base[idx["sister_bgsub_sum"]])
        if sb==0 or tb==0: continue
        r0=tb/sb
        if r0==0: continue
        sx,sy=[],[]
        for r in rs:
            si=float(r[idx["sister_bgsub_sum"]])
            if si==0: continue
            q=(float(r[idx["targeted_bgsub_sum"]])/si)/r0
            sx.append(float(r[idx["rel_time_s"]])); sy.append(q)
        if not sy or max(abs(v) for v in sy)>8: continue   # v1 residual-spike drop
        xs+=sx; ys+=sy; batches+=[b]*len(sy)
    return np.array(xs),np.array(ys),np.array(batches)

def ablint_plotted(hdr,rows):
    """G4_ablation_intensity main: each (batch,abl_seq,series) start-normalized so pre-ablation=1.
    Mirrors v1 norm_series(): drop non-positive baselines, reject per-frame artifacts outside
    [NEG_FLOOR=-2, NORM_CAP=5] (start anchor always kept), drop series with <2 good points."""
    NEG_FLOOR,NORM_CAP=-2.0,5.0
    idx={c:hdr.index(c) for c in hdr}
    from collections import defaultdict
    xs,ys,batches=[],[],[]
    for col in ("targeted_bgsub_sum","sister_bgsub_sum"):
        seqs=defaultdict(list)
        for row in rows:
            seqs[(row[idx["batch"]],row[idx["abl_seq"]])].append(row)
        for (b,s),rs in seqs.items():
            rs=sorted(rs,key=lambda r:float(r[idx["rel_time_s"]]))
            v0=float(rs[0][idx[col]])
            if not np.isfinite(v0) or v0<=0: continue     # baseline drop
            sx,sy=[],[]
            for j,r in enumerate(rs):
                n=float(r[idx[col]])/v0
                if j==0 or (np.isfinite(n) and NEG_FLOOR<=n<=NORM_CAP):   # keep anchor + in-range frames
                    sx.append(float(r[idx["rel_time_s"]])); sy.append(n)
            if len(sy)<2: continue
            xs+=sx; ys+=sy; batches+=[b]*len(sy)
    return np.array(xs),np.array(ys),np.array(batches)

SPECIAL={"G4_frap":frap_plotted,"G4_ablation_intensity":ablint_plotted}

# 2026-08-03 (user: "Review what this is plotting"). These parents are PAIRED COLUMN plots: four categorical
# columns (targeted pre, targeted post, paired pre, paired post) on a SYMLOG y, with no trend line anywhere.
# The generic picker saw two numeric metric columns (pre_over_cytosol / post_over_cytosol), classified them as
# `scatter`, drew pre-vs-post as an xy cloud and captioned it "-> hollow markers on the trend" — a trend that
# does not exist in the parent. Render these in the parent's own 4-column layout instead.
PAIRED_PREPOST={"G4_prepost_intensity","G4_prepost_intensity_nolines"}

# Storage column name -> the axis title a reader can actually understand. Used only as a fallback: a builder
# that publishes "x_label"/"y_label" in its record_plot metadata overrides this.
AXIS_LABELS={
    "x_min":                  "Time from ablation (min)",
    "min_to_event":           "Minutes relative to the event",
    "t_min":                  "Time (min)",
    "t_sec":                  "Time (s)",
    "rel_time_s":             "Time relative to ablation (s)",
    "time_from_ablation_s":   "Time from ablation (s)",
    "mitotic_duration_min":   "Metaphase duration (min)",
    "metaphase_duration_min": "Metaphase duration (min)",
    "duration_min":           "Duration (min)",
    "fluor_mean_au":          "Cell fluorescence at metaphase (a.u.)",
    "fluor_scaled01":         "Cell fluorescence at metaphase (min-max scaled 0-1)",
    "disp_um_per_20s":        "Displacement per 20 s (um)",
    "major_um":               "Major-axis length (um)",
    "minor_um":               "Minor-axis length (um)",
    "aspect_ratio":           "Aspect ratio (major/minor)",
    "pre_over_cytosol":       "KT intensity before ablation (background-subtracted)",
    "post_over_cytosol":      "KT intensity after ablation (background-subtracted)",
}

def _pretty_col(c):
    """Last-resort axis title from a column name: strip unit suffixes, unslug, sentence-case."""
    if not c: return c
    UNITS={"um":"(um)","min":"(min)","sec":"(s)","s":"(s)","au":"(a.u.)","pct":"(%)"}
    parts=c.split("_"); unit=""
    if len(parts)>1 and parts[-1] in UNITS:
        unit=" "+UNITS[parts[-1]]; parts=parts[:-1]
    txt=" ".join(parts).strip()
    return (txt[:1].upper()+txt[1:] if txt else c)+unit
PP_PRE,PP_POST,PP_KT="pre_over_cytosol","post_over_cytosol","kt"
PP_COLORS={"targeted":"#d62728","paired":"#1f77b4"}

def render_paired_prepost(pid,hdr,rows):
    """4-column paired pre/post zoom companion, matching the parent's layout and symlog axis.
    Trims only the points beyond the IQR fence of their own column; trimmed points are NOT drawn (a
    categorical column has no trend to interpolate a hollow marker onto) and the count is printed under
    the column label, so nothing is hidden."""
    ik={c:i for i,c in enumerate(hdr)}
    # rows are PAIRS (one KT's pre and post). Keep them as pairs so a trim never desynchronises the two
    # columns - the parent guarantees the pre and post columns hold the same kinetochores.
    data={"targeted":[],"paired":[]}
    for r in rows:
        kt=r[ik[PP_KT]].strip()
        if kt not in data: continue
        try: pre=float(r[ik[PP_PRE]]); post=float(r[ik[PP_POST]])
        except (ValueError,IndexError): continue
        data[kt].append((pre,post,r[ik["batch"]] if "batch" in ik else "(no batch col)"))
    if not any(data.values()): return None,0

    allv=np.array([v for arr in data.values() for p,q,_ in arr for v in (p,q)],float)
    trim=lib.zoom_trim(allv,floor_zero=True)
    hi=trim["hi"]; lo=min(0.0,trim["lo"] or 0.0)

    cols=[]   # (label, kt, values, n_dropped)
    for kt in ("targeted","paired"):
        arr=data[kt]
        keep=[(p,q) for p,q,_ in arr if not (p>hi or q>hi)]
        for p,q,b in arr:
            if p>hi or q>hi:
                lib.log_review(f"{pid}_zoom",b,f"pre={p:.4g} post={q:.4g}",
                    f"outlier trimmed for zoom companion: {kt} PAIR has a value > {hi:.3g}; the whole pair is "
                    f"dropped so the pre and post columns stay paired (categorical - not drawn, count under label)")
        nd=len(arr)-len(keep)
        cols.append((f"{kt}\npre",kt,np.array([p for p,_ in keep],float),nd))
        cols.append((f"{kt}\npost",kt,np.array([q for _,q in keep],float),nd))

    fig,ax=plt.subplots(figsize=(7.4,5.6))
    ax.set_yscale("symlog",linthresh=2000)   # identical to the parent - the range genuinely spans orders
    rng=np.random.default_rng(0); tick_lbl=[]
    n_out_total=sum(nd for i,(_,_,_,nd) in enumerate(cols) if i%2==0)   # nd is per PAIR; count each pair once
    for x,(label,kt,kept,nd) in enumerate(cols):
        if not kept.size:
            tick_lbl.append(f"{label}\nN=0"); continue    # keep tick labels aligned with the columns
        c=PP_COLORS[kt]
        ax.scatter(x+rng.uniform(-.13,.13,kept.size),kept,s=12,alpha=.55,color=c,edgecolors="none",zorder=1)
        ax.hlines(np.median(kept),x-.18,x+.18,color=c,lw=2.5,zorder=3)
        ax.hlines(np.mean(kept),x-.14,x+.14,color=c,lw=1.2,ls=(0,(2,1.5)),zorder=3)
        tick_lbl.append(f"{label}\nN={kept.size}"+(f"\n({nd} pair(s) excluded)" if nd else ""))
    ax.set_xticks(range(len(cols))); ax.set_xticklabels(tick_lbl,fontsize=8)
    ax.set_xlim(-.6,len(cols)-.4); ax.set_ylim(lo,hi)
    ax.set_ylabel("KT eYFP intensity (Σ in r=9 disk, background-subtracted)")
    ax.legend(handles=[mlines.Line2D([],[],color="#333",lw=2.5,ls="-"),
                       mlines.Line2D([],[],color="#333",lw=1.2,ls=(0,(2,1.5)))],
              labels=["median","mean"],fontsize=7,ncol=2,loc="upper center",
              bbox_to_anchor=(0.5,0.99),framealpha=.9)
    ax.set_title(f"{pid} — outlier-trimmed zoom companion  "
                 f"(y-axis fit to bulk; {n_out_total} outlier PAIR(s) removed -> not drawn, "
                 f"counts under the column labels)",loc="left",fontweight="bold",fontsize=9.5)
    # footer as the xlabel, not floating text inside the axes - inside, it struck through the targeted-post column
    ax.set_xlabel(f"v2 zoom: {n_out_total} pts > {hi:.3g} trimmed  |  old y-max {trim['vmax']:.3g} -> new {hi:.3g}"
                  f"  |  paired columns, no trend line",fontsize=7,color="#555",labelpad=6)
    gd=group_dir(pid); os.makedirs(gd,exist_ok=True)
    out_png=f"{gd}/{pid}_zoom.png"
    fig.tight_layout(); fig.savefig(out_png,bbox_inches="tight"); plt.close(fig)
    return out_png,n_out_total

# ---- main loop ----------------------------------------------------------------------------------
settings=json.load(open(f"{PLOTS}/PLOT_SETTINGS.json"))
report=[]   # (pid, status, detail)
_REFRESH_PROV=[]   # parents whose _zoom was regenerated this run; their provenance is re-copied at the end

def render_and_log(pid, ycol, yvals, xvals, xlabel, ylabel, batches, groups, trim, hdr, rows, family):
    """draw the zoomed companion, mark trimmed points as hollow, log removals, write _zoom.csv."""
    om=trim["out_mask"]; keep=~om
    gd=group_dir(pid); os.makedirs(gd,exist_ok=True)
    out_png=f"{gd}/{pid}_zoom.png"

    # ---- log removals (whole-batch flag if a batch is ENTIRELY outlier & >1 pt, else per-point) ----
    reason="outlier trimmed for zoom companion"
    if batches is not None:
        from collections import defaultdict
        by=defaultdict(lambda:[0,0]); vals_by=defaultdict(list)
        for b,o,yv in zip(batches,om,yvals):
            by[b][1]+=1
            if o: by[b][0]+=1; vals_by[b].append(yv)
        for b,(nout,ntot) in by.items():
            if nout==0: continue
            if nout==ntot and ntot>1:
                lib.log_review(f"{pid}_zoom",b,
                    f"{np.nanmin(vals_by[b]):.3g}..{np.nanmax(vals_by[b]):.3g}",
                    f"{reason}: whole batch off-scale (all {ntot} pts > {trim['fence_hi']:.3g})")
            else:
                for yv in vals_by[b]:
                    lib.log_review(f"{pid}_zoom",b,f"{yv:.4g}",
                        f"{reason}: point beyond IQR fence [{trim['fence_lo']:.3g},{trim['fence_hi']:.3g}]")
    else:
        for yv in yvals[om]:
            lib.log_review(f"{pid}_zoom","(no batch col)",f"{yv:.4g}",
                f"{reason}: point beyond IQR fence [{trim['fence_lo']:.3g},{trim['fence_hi']:.3g}]")

    # ---- draw ----
    fig,ax=plt.subplots(figsize=(8.5,5.2))
    def gcolor(g):
        return lib.PALETTE.get(g, None)
    hi=trim["hi"]; lo=trim["lo"]
    if family=="line":
        # group polylines by (batch, secondary series key)
        from collections import defaultdict
        key=list(zip(batches, groups if groups is not None else ["_"]*len(batches)))
        lines=defaultdict(list)
        for k,x,y,o in zip(key,xvals,yvals,om): lines[k].append((x,y,o))
        for (b,g),pts in lines.items():
            pts=sorted(pts,key=lambda t:t[0])
            om_line=[bool(p[2]) or p[1]>hi for p in pts]
            c=gcolor(g) or "#c0392b"
            # faint polyline through the KEPT points of THIS line (its trend); the omitted point's hollow
            # marker is interpolated onto exactly this trend at the point's own x (never edge-pinned to hi).
            xk=[p[0] for p,o in zip(pts,om_line) if not o]
            yk=[p[1] for p,o in zip(pts,om_line) if not o]
            if xk: ax.plot(xk,yk,color=c,alpha=.18,lw=.7)
            for p,o in zip(pts,om_line):
                if o:
                    yv=lib.omitted_y(p[0],xk,yk,lo=lo,hi=hi)
                    ax.plot(p[0],yv,marker="o",mfc="none",mec=c,ms=5,mew=1.0,zorder=6)
        # binned median trend of the KEPT points
        xk=xvals[keep]; yk=yvals[keep]
        if xk.size>5:
            lo_x,hi_x=np.nanmin(xk),np.nanmax(xk); nb=12
            edges=np.linspace(lo_x,hi_x,nb+1); bx,bmed=[],[]
            for i in range(nb):
                m=(xk>=edges[i])&(xk<edges[i+1])&np.isfinite(yk)
                if m.sum()>=3: bx.append((edges[i]+edges[i+1])/2); bmed.append(np.median(yk[m]))
            if bx: ax.plot(bx,bmed,color="#111",lw=2.5,marker="o",ms=5,zorder=8,label="median (bulk)")
        ax.set_xlabel(xlabel)
    elif family=="scatter":
        c_all=[gcolor(g) or "#4477aa" for g in (groups if groups is not None else ["_"]*len(yvals))]
        c_all=np.array(c_all,dtype=object)
        ax.scatter(xvals[keep],yvals[keep],c=list(c_all[keep]),s=22,alpha=.7,edgecolors="none")
        # trimmed points -> hollow markers ON the trend at their own x (interpolated from the KEPT scatter),
        # never pinned to the top edge.
        xk=xvals[keep]; yk=yvals[keep]
        for x,cc in zip(xvals[om],c_all[om]):
            yv=lib.omitted_y(x,xk,yk,lo=lo,hi=hi)
            ax.plot(x,yv,marker="o",mfc="none",mec=cc,ms=6,mew=1.1,zorder=6)
        ax.set_xlabel(xlabel)
    else:  # strip (1-D distribution, grouped)
        _dropped_per_group={}
        gnames=list(dict.fromkeys(groups)) if groups is not None else ["all"]
        gpos={g:i for i,g in enumerate(gnames)}
        rng=np.random.default_rng(0)
        for g in gnames:
            gm=np.array([gg==g for gg in groups]) if groups is not None else np.ones(len(yvals),bool)
            xk=gpos[g]+rng.uniform(-.15,.15,gm.sum())
            yk=yvals[gm]; ok=om[gm]
            c=gcolor(g) or "#4477aa"
            ax.scatter(xk[~ok],yk[~ok],s=16,alpha=.55,color=c,edgecolors="none")
            # USER 2026-07-28: on a CATEGORICAL plot (violin / strip) an excluded point has no x-trend to be
            # interpolated onto — every point in the group shares one x — so the old hollow marker sat at a
            # FABRICATED y just above the group max. That cluttered the plot and read as real data. On these
            # plots the excluded points are simply NOT DRAWN. The count is still reported (below the group
            # label and in the axis note), so nothing is silently hidden.
            n_drop_g=int(ok.sum())
            if n_drop_g: _dropped_per_group[g]=n_drop_g
            vv=yvals[gm & keep]
            if vv.size: ax.hlines(np.median(vv),gpos[g]-.28,gpos[g]+.28,color="#111",lw=2,zorder=7)
        ax.set_xticks(range(len(gnames)))
        ax.set_xticklabels([lib.lbl(g)+(f"\n({_dropped_per_group[g]} excluded)" if g in _dropped_per_group else "")
                            for g in gnames],rotation=25,ha="right",fontsize=8)
    ax.set_ylim(lo,hi)
    ax.set_ylabel(ylabel)
    n_out=int(om.sum())
    ax.set_title(f"{pid} — outlier-trimmed zoom companion  "
                 f"(y-axis fit to bulk; {n_out} outlier pt(s) removed"
                 + (" -> not drawn, counts under the group labels)" if family not in ("line", "scatter")
                    else " -> hollow markers on the trend)"),
                 loc="left",fontweight="bold",fontsize=9.5)
    ax.text(0.995,0.02,f"v2 zoom: {n_out} pts > {trim['fence_hi']:.3g} trimmed  |  "
            f"old y-max {trim['vmax']:.3g} -> new {hi:.3g}",transform=ax.transAxes,
            ha="right",va="bottom",fontsize=7,color="#555")
    if ax.get_legend_handles_labels()[0]: ax.legend(fontsize=8,loc="upper right")
    fig.tight_layout(); fig.savefig(out_png,bbox_inches="tight"); plt.close(fig)

    # ---- _zoom.csv: same rows + removed flag ----
    with open(f"{DATA}/{pid}_zoom.csv","w",newline="") as f:
        w=csv.writer(f); w.writerow(hdr+["zoom_outlier_removed"])
        # map removal back to rows: rows align with yvals ONLY for non-special (1 row per point).
        if len(rows)==len(om):
            for row,o in zip(rows,om): w.writerow(row+["1" if o else "0"])
        else:
            for row in rows: w.writerow(row+[""])  # special (normalized) plots: raw rows, flag not 1:1
    return out_png, n_out

# Optional targeted re-run: ZOOM_ONLY="G5shape_,G6trk_" limits the pass to plot ids containing any of the
# comma-separated substrings. Added 2026-08-03 so that re-rendering ONE family's parents can refresh just that
# family's companions — a blanket run rewrites every zoom PNG/PDF/CSV in the deck, which is a large and
# unreviewable side effect when only a handful of parents actually changed. Unset = the full pass, unchanged.
ZOOM_ONLY = [s.strip() for s in os.environ.get("ZOOM_ONLY", "").split(",") if s.strip()]
if ZOOM_ONLY:
    print(f"ZOOM_ONLY active: only plot ids containing any of {ZOOM_ONLY}")

for pid in sorted(settings):
    if not pid or not pid.strip():
        continue   # orphan empty-id entry (no real figure)
    if ZOOM_ONLY and not any(s in pid for s in ZOOM_ONLY):
        continue
    # NEVER zoom a figure that is ALREADY a zoom companion. Doing so wrote <id>_zoom_zoom.png, an
    # artefact nothing places, while the real <id>_zoom.png in the deck was left untouched - so 10
    # placed _zoom figures had NO regenerator and silently kept pre-fix data (found 2026-07-29).
    # A _zoom companion is refreshed by re-running THIS script over its PARENT, which happens in the
    # same pass because the parent is its own entry in PLOT_SETTINGS.
    if pid.endswith("_zoom"):
        report.append((pid, "skip", "already a _zoom companion; refreshed via its parent"))
        continue
    info=settings[pid]; st=info.get("settings",{})
    tkw=(st.get("type","") if isinstance(st,dict) else str(st)).lower()
    nrows=info.get("n_rows",0)
    # 2026-08-03: SKIP_IDS was DEFINED but never referenced, so the guard added on 2026-07-30 ("group4_fluor.py
    # builds G4_fluor_vs_duration_zoom itself, the generic builder must not overwrite it") never actually fired
    # and every run of this script silently clobbered that purpose-built figure with the generic raw-axis one.
    if pid in SKIP_IDS:
        report.append((pid,"skip","on SKIP_IDS: its _zoom companion is built by its own script")); continue
    if pid.endswith(SKIP_ID_SUFFIX) or any(k in tkw for k in SKIP_TYPE_KW):
        report.append((pid,"skip",f"non-continuous type ({tkw[:40]})")); continue
    if nrows and nrows<8:
        report.append((pid,"skip",f"too few rows ({nrows})")); continue
    p,hdr,rows=load_csv(pid)
    if hdr is None or not rows:
        report.append((pid,"skip","no data csv")); continue

    # ---------- special normalized plots ----------
    if pid in SPECIAL:
        try: xv,yv,batches=SPECIAL[pid](hdr,rows)
        except Exception as e:
            report.append((pid,"error",f"special reconstruct: {e}")); continue
        trim=lib.zoom_trim(yv, floor_zero=True)
        if not trim["distorting"]:
            report.append((pid,"none",f"checked; no distorting outliers (y-max {trim['vmax']:.3g})")); continue
        ylabel={"G4_frap":"targeted/sister KT (pre-ablation=1)",
                "G4_ablation_intensity":"KT intensity, start-normalized to 1"}[pid]
        outpng,nout=render_and_log(pid,"norm",yv,xv,"Time from ablation (s)",ylabel,
                                   batches,None,trim,hdr,rows,"line")
        report.append((pid,"zoom",
            f"{nout} outlier pts removed; y-max {trim['vmax']:.3g}->{trim['hi']:.3g}; -> {os.path.basename(outpng)}"))
        continue

    # ---------- paired pre/post column plots (categorical x, no trend line) ----------
    if pid in PAIRED_PREPOST:
        if PP_KT not in hdr or PP_PRE not in hdr or PP_POST not in hdr:
            report.append((pid,"skip",f"paired prepost: expected columns {PP_KT}/{PP_PRE}/{PP_POST}")); continue
        try: outpng,nout=render_paired_prepost(pid,hdr,rows)
        except Exception as e:
            report.append((pid,"error",f"paired prepost: {e}")); continue
        if outpng is None:
            report.append((pid,"skip","paired prepost: no plottable values")); continue
        report.append((pid,"zoom",
            f"paired 4-column layout (matches parent; NOT a scatter); {nout} outlier pts not drawn"
            f" -> {os.path.basename(outpng)}"))
        continue

    # ---------- generic: pick the most-distorted metric column ----------
    mcols=numeric_metric_cols(hdr,rows)
    if not mcols:
        report.append((pid,"skip","no numeric metric column")); continue
    best=None
    for c in mcols:
        yv=col_floats(hdr,rows,c)
        t=lib.zoom_trim(yv)
        if t["vmax"] is not None and abs(t["vmax"]-1.0)<1e-6 and abs(t["vmin"] or 0)<1e-6:
            continue   # structural min-max 0-1 scaled column: its 0/1 endpoints are not outliers
        score=(t["vmax"]-t["vmin"])/max(1e-9,(t["p95"]-t["p50"])) if t["p95"] is not None else 0
        if t["distorting"] and (best is None or score>best[3]):
            best=(c,yv,t,score)
    if best is None:
        # report the worst y-max/p95 ratio for transparency
        worst=""
        for c in mcols:
            yv=col_floats(hdr,rows,c); t=lib.zoom_trim(yv)
            if t["p95"]: worst=f"{c}: max {t['vmax']:.3g} vs p95 {t['p95']:.3g}"
        report.append((pid,"none",f"checked; no distorting outliers ({worst})")); continue

    ycol,yv,trim,_=best
    # other metric col (for scatter x); time col; group col
    othermetric=[c for c in mcols if c!=ycol]
    xtime=first_present(hdr,list(X_TIME))
    idcol=first_present(hdr,["batch","track"])
    gcol=first_present(hdr,GROUP_COLS)
    groups=[row[hdr.index(gcol)] for row in rows] if gcol else None
    batches=[row[hdr.index(idcol)] for row in rows] if idcol else None
    if xtime and idcol:
        family="line"; xv=col_floats(hdr,rows,xtime); xlabel=xtime
    elif othermetric:
        family="scatter"
        # 2026-07-11 (user): keep the zoom's x/y ORIENTATION identical to the parent scatter. By record_plot
        # convention the parent's y-axis is the LAST metric column and x is the other metric. The generic
        # "most-distorted column = y" pick could TRANSPOSE the zoom vs its parent (e.g. G4_fluor_vs_duration_scaled01
        # put duration on Y instead of fluor). Force parent_y on Y (trim it) and parent_x on X. If the parent's y
        # has no distorting outliers (or is a structural 0-1 min-max axis), skip — don't emit a transposed zoom.
        parent_y=mcols[-1]; parent_x=next((c for c in mcols if c!=parent_y),None)
        if parent_x is None:
            report.append((pid,"skip","scatter: single metric column")); continue
        _yv=col_floats(hdr,rows,parent_y); _t=lib.zoom_trim(_yv)
        _struct01=_t["vmax"] is not None and abs(_t["vmax"]-1.0)<1e-6 and abs(_t["vmin"] or 0)<1e-6
        if _struct01 or not _t["distorting"]:
            report.append((pid,"none",f"orientation-preserved: parent y '{parent_y}' has no distorting outliers")); continue
        ycol,yv,trim=parent_y,_yv,_t
        xcol=parent_x; xv=col_floats(hdr,rows,xcol); xlabel=xcol
    else:
        family="strip"; xv=np.arange(len(yv)); xlabel=""
    # USER 2026-08-03: "what is x-min? I know ive asked this about this plot several times which means you need
    # to actually label the axis with x_min with a more descriptive label title". The companion was labelling its
    # axes with the RAW CSV COLUMN NAMES (x_min, fluor_mean_au, ...), which are storage names, not axis titles.
    # A builder can now publish real axis titles in its record_plot metadata and they win here; otherwise fall
    # back to a readable form of the column name rather than the bare identifier.
    _sett=info.get("settings") or {}    # record_plot nests its metadata under "settings" in PLOT_SETTINGS.json
    xlabel=_sett.get("x_label") or AXIS_LABELS.get(xlabel) or _pretty_col(xlabel)
    ylabel=_sett.get("y_label") or AXIS_LABELS.get(ycol)   or _pretty_col(ycol)
    outpng,nout=render_and_log(pid,ycol,yv,xv,xlabel,ylabel,
                               np.array(batches) if batches else None,groups,trim,hdr,rows,family)
    report.append((pid,"zoom",
        f"col='{ycol}' {nout} outlier pts removed; y-max {trim['vmax']:.3g}->{trim['hi']:.3g}"
        f" ({family}) -> {os.path.basename(outpng)}"))
    _REFRESH_PROV.append(pid)

# ---- keep each zoom's recorded provenance in step with its parent (2026-08-04) -------------------
# A _zoom is drawn from its PARENT's data CSV, so its sources are the parent's sources. This script
# regenerates the zoom PNG but never touched the zoom's PLOT_SETTINGS entry, so its `hashes_at_build`
# stayed frozen at whenever that entry was first created. The staleness check then reported a zoom as
# out-of-date even though it had just been rebuilt (found on ablation_count_by_cohort_zoom). Copy the
# parent's source block onto the zoom entry after regenerating it.
if _REFRESH_PROV:
    try:
        _sp = f"{PLOTS}/PLOT_SETTINGS.json"
        _all = json.load(open(_sp))
        _n = 0
        # 2026-08-05: refresh EVERY <pid>_zoom entry whose parent carries provenance, not only the ones
        # regenerated on this run. A zoom that needed no new trim this time still has a stale (or absent)
        # source block, and three placed zooms - G4_velocity_zoom, G4_velocity_vs_distance_zoom,
        # G4_oscillation_chronological_zoom - had NO source block at all for exactly that reason.
        _targets = list(dict.fromkeys(list(_REFRESH_PROV) +
                        [k[:-5] for k in _all if k.endswith("_zoom") and k[:-5] in _all]))
        # also consider parents whose _zoom PNG exists on disk but has NO entry at all - three placed
        # supplemental zooms (G4_velocity_zoom, G4_velocity_vs_distance_zoom,
        # G4_oscillation_chronological_zoom) were on the deck completely unregistered (2026-08-05).
        for _p2 in list(_all):
            if _p2.endswith("_zoom") or (_p2 + "_zoom") in _all: continue
            if os.path.isfile(os.path.join(group_dir(_p2), _p2 + "_zoom.png")): _targets.append(_p2)
        _targets = list(dict.fromkeys(_targets))
        for _pid in _targets:
            _par = _all.get(_pid)
            if not _par or not _par.get("source"): continue
            _zm = _all.get(_pid + "_zoom")
            if _zm is None:                       # create the missing entry from its parent
                _zm = {"caption": (_par.get("caption") or _pid) + " - outlier-trimmed zoom companion",
                       "settings": {"type": "zoom companion", "companion_of": _pid,
                                    "trim": "robust IQR fence via lib.zoom_trim"},
                       "n_rows": _par.get("n_rows"),
                       "data": f"data/{_pid}_zoom.csv" if os.path.isfile(
                                   os.path.join(DATA, _pid + "_zoom.csv")) else _par.get("data"),
                       "code": _par.get("code", "")}
                _all[_pid + "_zoom"] = _zm
            _src = dict(_par["source"])
            _src["derived_from"] = _pid          # say WHY the zoom carries the parent's source hashes
            _zm["source"] = _src
            _n += 1
        json.dump(_all, open(_sp, "w"), indent=1)
        print(f"provenance refreshed on {_n} _zoom entries (copied from their parents)")
    except Exception as _e:
        print(f"provenance refresh FAILED: {type(_e).__name__}: {_e}")

lib.flush_review(REVIEW_OUT)

# ---- accounting report --------------------------------------------------------------------------
zoomed=[r for r in report if r[1]=="zoom"]
none_=[r for r in report if r[1]=="none"]
skip=[r for r in report if r[1]=="skip"]
err=[r for r in report if r[1]=="error"]
print("="*90)
print(f"ZOOM COMPANIONS BUILT: {len(zoomed)}")
for pid,_,d in sorted(zoomed): print(f"  [ZOOM] {pid}: {d}")
print(f"\nCHECKED, NO OUTLIER TRIM NEEDED: {len(none_)}")
for pid,_,d in sorted(none_): print(f"  [none] {pid}: {d}")
print(f"\nSKIPPED (non-continuous / too small): {len(skip)}")
for pid,_,d in sorted(skip): print(f"  [skip] {pid}: {d}")
if err:
    print(f"\nERRORS: {len(err)}")
    for pid,_,d in sorted(err): print(f"  [ERR ] {pid}: {d}")
print("="*90)
print(f"review log -> {REVIEW_OUT}  ({len(lib.REVIEW)} rows)")
print(f"TOTAL PLOTS ACCOUNTED: {len(report)}  (zoom {len(zoomed)} / none {len(none_)} / skip {len(skip)} / err {len(err)})")
