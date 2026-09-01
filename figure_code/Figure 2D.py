"""Nocodazole & ZM drug-sensitivity violins (Control vs drug vs target-ablated)."""
import sys; sys.path.insert(0,"/Volumes/4 MB/ablation_figures_20260625")
import numpy as np, matplotlib.pyplot as plt, re
from matplotlib.ticker import FuncFormatter
import lib
lib.apply_style()
OUT="/Volumes/4 MB/ablation_figures_20260625/group4"; SCRIPT=__file__
data,_=lib.load_master()
def mdur(r):
    d,ok=lib.mitotic_duration_min(r); return d if ok else None
act=[r for r in data if r.get("Exclude") not in ("Yes","yes") and not lib.is_mad1(r["Batch Name"]) and not lib.excluded(r["Batch Name"])]
def is_noc(b): return bool(re.search(r'low dose noc|nocod',b.lower()))
def is_zm(b): return bool(re.search(r'zm_ablation|zm_',b.lower()))
# cohorts — control + target-ablated come from the CANONICAL lib.assign_cohorts() set so N for the
# unmodified control and the sisterless target groups matches the main / phase-split / exhaustion violins.
_coh=lib.assign_cohorts()
ctrl=[v for _,v in _coh["unModified"]]


# target-ablated comparison = ON-TARGET cells of the requested sisterless count ONLY (NOC->1-sisterless,
# ZM->3-sisterless), drawn from the canonical IQR-screened cohort.
def targ_grp(sis): return [v for _,v in _coh[f"{sis}-Sister"]]
def drug_violin(drugfn,name,fname,tsis,drop_over=None,ontarget_only=False):
    targ=targ_grp(tsis)
    drug=[]
    for r in act:
        if not drugfn(r["Batch Name"]): continue
        if ontarget_only and r.get("On-Target / Off-Target","")!="On-target": continue   # #8: ZM drug group = ON-TARGET only
        d=mdur(r)
        if d is None: continue
        if drop_over is not None and d>drop_over:   # H4: drop >100 min drug outlier(s)
            print(f"{name}: dropping >{drop_over:g}-min outlier {r['Batch Name']!r} dur={d:.1f}")
            lib.log_review(f"{name}_drug_outlier",r["Batch Name"],f"{d:.1f}",f"drug duration >{drop_over:g} min - dropped from {name} plot; review")
            continue
        drug.append(d)
    # order per feedback S51: Control (unmodified), Target-ablated, then the drug
    groups=[("Control (Unmodified)",[x for x in ctrl if x],"#6e6e6e"),
            (f"Target-ablated ({tsis}-sisterless)",[x for x in targ if x],"#1b7837"),
            (f"Low-dose {name}",[x for x in drug if x],"#b35806")]
    fig,ax=plt.subplots(figsize=(7.2,5.2)); rows=[]
    for i,(lab,d,col) in enumerate(groups):
        if not d: continue
        lib.journal_violin(ax,d,i,col,width=.7,alpha=.3)   # scale=width (uniform max half-width), cut=0, N<6 points-only
        ax.scatter(np.full(len(d),i)+(np.random.RandomState(i).rand(len(d))-.5)*.18,d,s=lib.VIOLIN_DOT_S,color=col,alpha=.8,edgecolor="white",lw=.3,zorder=3)
        ax.hlines(np.median(d),i-.3,i+.3,color=col,lw=2.6,zorder=4)            # median bar
        ax.hlines(np.mean(d),i-.24,i+.24,color=col,lw=1.3,ls=(0,(2,1.5)),zorder=4)  # mean (dashed)
        ax.text(i,max(d)+1,f"x̄ {lib.mmss(np.mean(d))}\nmed {lib.mmss(np.median(d))}\nN={len(d)}",ha="center",va="bottom",fontsize=7.5)
        for x in d: rows.append([lab,round(x,3)])
    # stats: pairwise Mann-Whitney as significance BARS (asterisks + p) — drug vs BOTH others + control vs target
    from scipy import stats as _st
    def _stars(p): return "***" if p<.001 else "**" if p<.01 else "*" if p<.05 else "ns"
    _ymax=max((max(d) for _,d,_ in groups if d),default=1); _yr=_ymax*0.07
    # significance bars link the EXACT two violins compared; label states which two groups + p
    _gshort=["Control","Target","Drug"]
    _topbar=_ymax
    for k,(a,b) in enumerate([(0,1),(1,2),(0,2)]):    # control-vs-target, target-vs-drug, control-vs-drug
        da,db=groups[a][1],groups[b][1]
        if len(da)>=2 and len(db)>=2:
            try:
                _u,_p=_st.mannwhitneyu(da,db,alternative="two-sided"); yy=_ymax+_yr*(4.2+k*2.1)  # LZ4: base raised 1.6->4.2 so the first sig bar clears the 3-line per-violin (x̄/med/N) labels
                ax.plot([a,a,b,b],[yy,yy+_yr*.3,yy+_yr*.3,yy],color="#333",lw=1.0,clip_on=False)
                ax.text((a+b)/2,yy+_yr*.34,f"{_gshort[a]} vs {_gshort[b]}: {_stars(_p)} p={_p:.2g}",ha="center",va="bottom",fontsize=6.5,color="#333")
                _topbar=max(_topbar,yy+_yr)
            except Exception: pass
    ax.set_ylim(top=_topbar+_yr*1.5)   # headroom so significance bars + labels never overlap title/each other
    ax.set_xticks(range(3)); ax.set_xticklabels([g[0].replace(" (","\n(") for g in groups],fontsize=8)
    from matplotlib.lines import Line2D as _L2dr
    ax.legend(handles=[_L2dr([0],[0],color="#444",lw=2.6,label="median"),
                       _L2dr([0],[0],color="#444",lw=1.3,ls=(0,(2,1.5)),label="mean")],loc="upper left",fontsize=7.5)
    ax.set_ylabel("Metaphase duration (MM:SS)"); ax.yaxis.set_major_formatter(FuncFormatter(lambda v,_: lib.mmss(v) if v>=0 else ""))
    ax.set_title(f"{name} sensitivity — metaphase duration",loc="left",fontweight="bold",fontsize=11)
    plt.tight_layout(); plt.savefig(f"{OUT}/{fname}",bbox_inches="tight"); plt.close()
    lib.record_plot(fname[:-4],["group","mitotic_duration_min"],rows,
      {"type":"violin","groups":["control","drug","target-ablated"]},SCRIPT,f"{name} drug sensitivity violin")
    print(f"{name}: control {len([x for x in ctrl if x])}, drug {len([x for x in drug if x])}, target {len([x for x in targ if x])}")
drug_violin(is_noc,"Nocodazole","G4_nocodazole.png","1")          # NOC vs on-target 1-sisterless
drug_violin(is_zm,"ZM","G4_zm.png","3",drop_over=100,ontarget_only=True)   # #8: ZM group = ON-TARGET only; drop >100min outlier

# ---- ZM split by TARGET GROUP (on-target / off-target / unmodified) — the ZM samples carry all three ----
def zm_by_group():
    from scipy import stats as _st
    from matplotlib.lines import Line2D as _L
    groups=[("ZM on-target","On-target","#1b7837"),("ZM off-target","Off-target","#d6604d"),("ZM unmodified","Unmodified","#6e6e6e")]
    vals={lab:[] for lab,_,_ in groups}; rows=[]
    for r in act:
        if not is_zm(r["Batch Name"]): continue
        d=mdur(r); tt=r.get("On-Target / Off-Target","")
        if d is None: continue
        for lab,key,_ in groups:
            if tt==key: vals[lab].append(d); rows.append([lab,r["Batch Name"],round(d,3)])
    fig,ax=plt.subplots(figsize=(7.6,5.4)); order=[(lab,col) for lab,_,col in groups]
    for i,(lab,col) in enumerate(order):
        d=vals[lab]
        if not d: continue
        lib.journal_violin(ax,d,i,col,width=.7,alpha=.3)   # scale=width (uniform max half-width), cut=0, N<6 points-only
        ax.scatter(np.full(len(d),i)+(np.random.RandomState(i).rand(len(d))-.5)*.18,d,s=lib.VIOLIN_DOT_S,color=col,alpha=.8,edgecolor="white",lw=.3,zorder=3)
        ax.hlines(np.median(d),i-.3,i+.3,color=col,lw=2.6,zorder=4); ax.hlines(np.mean(d),i-.24,i+.24,color=col,lw=1.3,ls=(0,(2,1.5)),zorder=4)
        ax.text(i,max(d)+1,f"x̄ {lib.mmss(np.mean(d))}\nmed {lib.mmss(np.median(d))}\nN={len(d)}",ha="center",va="bottom",fontsize=7.5)
    labs=[lab for lab,_ in order]
    _stars=lambda p:"***" if p<.001 else "**" if p<.01 else "*" if p<.05 else "ns"
    _ymax=max((max(v) for v in vals.values() if v),default=1); _yr=_ymax*0.06; _top=_ymax
    for k,(a,b) in enumerate([(0,1),(1,2),(0,2)]):
        da,db=vals[labs[a]],vals[labs[b]]
        if len(da)>=2 and len(db)>=2:
            _u,_p=_st.mannwhitneyu(da,db,alternative="two-sided"); yy=_ymax+_yr*(1.6+k*2.1)
            ax.plot([a,a,b,b],[yy,yy+_yr*.3,yy+_yr*.3,yy],color="#333",lw=1.0,clip_on=False)
            ax.text((a+b)/2,yy+_yr*.34,f"{labs[a].split()[-1]} vs {labs[b].split()[-1]}: {_stars(_p)} p={_p:.2g}",ha="center",va="bottom",fontsize=6.3); _top=max(_top,yy+_yr)
    ax.set_ylim(top=_top+_yr*1.5); ax.set_xticks(range(3)); ax.set_xticklabels(labs,fontsize=9)
    ax.legend(handles=[_L([0],[0],color="#444",lw=2.6,label="median"),_L([0],[0],color="#444",lw=1.3,ls=(0,(2,1.5)),label="mean")],loc="upper right",fontsize=7.5)
    ax.set_ylabel("Metaphase duration (MM:SS)"); ax.yaxis.set_major_formatter(FuncFormatter(lambda v,_: lib.mmss(v) if v>=0 else ""))
    ax.set_title("ZM (2µM) — metaphase duration by target group\n(includes the 103-min off-target sample — real, per dish/pos table)",loc="left",fontweight="bold",fontsize=10)
    plt.tight_layout(); plt.savefig(f"{OUT}/G4_zm_by_target.png",bbox_inches="tight"); plt.close()
    lib.record_plot("G4_zm_by_target",["group","batch","metaphase_duration_min"],rows,
      {"type":"violin 3-group","groups":["ZM on-target","ZM off-target","ZM unmodified"],"note":"103min off-target sample included"},SCRIPT,"ZM metaphase duration by target group")
    print("ZM by target group N:",{lab:len(vals[lab]) for lab,_ in order})
# ITEM 11: G4_zm_by_target REMOVED from the deck (the three-ZM-groups-only plot doesn't contribute
# without the non-ZM comparison groups; the 103-min off-target sample is meaningless in isolation).
# The full comparison lives in G4_zm_full. Generation disabled; orchestrator drops G4_zm_by_target from the manifest.
# 2026-08-03 (re-enabled, GENERATION ONLY): ITEM 11 removed this figure from the DECK, and disabling
# generation followed from that. But the 2026-08-03 review session PLACED G4_zm_by_target on META board
# M2 as part of the ZM set, so the deck now shows a figure whose data stopped being regenerated -- it was
# still carrying pre-is_mad1()-fix cohorts. Re-enabling the call keeps the placed figure's data honest.
# It does NOT re-place anything and does NOT reverse ITEM 11's editorial judgement.
# ⚠ FOR MADELINE: ITEM 11 (remove from deck) and today's placement contradict each other. Say which wins.
zm_by_group()

# ---- #8: FULL ZM comparison — Control, 3-sisterless target-ablated, ZM on-target, ZM off-target, ZM unmodified ----
def zm_full():
    from scipy import stats as _st
    from matplotlib.lines import Line2D as _L
    zmg={"On-target":[],"Off-target":[],"Unmodified":[]}
    for r in act:
        if not is_zm(r["Batch Name"]): continue
        d=mdur(r); tt=r.get("On-Target / Off-Target","")
        if d is None or d>100: continue                      # same >100-min outlier drop as G4_zm
        if tt in zmg: zmg[tt].append(d)
    groups=[("Control\n(Unmodified)",[x for x in ctrl if x],"#6e6e6e"),
            ("Target-ablated\n(3-sisterless)",[x for x in targ_grp('3') if x],"#1b7837"),
            ("ZM\non-target",zmg["On-target"],"#1b5e20"),
            ("ZM\noff-target",zmg["Off-target"],"#d6604d"),
            ("ZM\nunmodified",zmg["Unmodified"],"#b35806")]
    # LZ5: violin on top, pairwise-stats GRID below (no on-plot significance marks)
    fig,(ax,axT)=plt.subplots(2,1,figsize=(10,8.4),gridspec_kw={"height_ratios":[3,1.5]}); rows=[]
    for i,(lab,d,col) in enumerate(groups):
        if not d: continue
        lib.journal_violin(ax,d,i,col,width=.7,alpha=.3)   # scale=width (uniform max half-width), cut=0, N<6 points-only
        ax.scatter(np.full(len(d),i)+(np.random.RandomState(i).rand(len(d))-.5)*.18,d,s=lib.VIOLIN_DOT_S,color=col,alpha=.8,edgecolor="white",lw=.3,zorder=3)
        ax.hlines(np.median(d),i-.3,i+.3,color=col,lw=2.6,zorder=4); ax.hlines(np.mean(d),i-.24,i+.24,color=col,lw=1.3,ls=(0,(2,1.5)),zorder=4)
        ax.text(i,max(d)+1,f"x̄ {lib.mmss(np.mean(d))}\nmed {lib.mmss(np.median(d))}\nN={len(d)}",ha="center",va="bottom",fontsize=7)
        for x in d: rows.append([lab.replace(chr(10)," "),round(x,3)])
    _stars=lambda p:"***" if p<.001 else "**" if p<.01 else "*" if p<.05 else "ns"
    _ymax=max((max(d) for _,d,_ in groups if d),default=1)
    ax.set_ylim(top=_ymax*1.22)   # headroom for the 3-line per-violin labels only (no bars now)
    ax.set_xticks(range(len(groups))); ax.set_xticklabels([g[0] for g in groups],fontsize=8)
    # ---- LZ5: pairwise Mann-Whitney (two-sided) across ALL group pairs, rendered as a stats grid ----
    _gshort=["Control","Target(3-sis)","ZM on-tgt","ZM off-tgt","ZM unmod"]
    _ng=len(groups); _pmat=[["" for _ in range(_ng)] for _ in range(_ng)]; _grid_rows=[]
    for a in range(_ng):
        for b in range(_ng):
            if a==b: _pmat[a][b]="—"; continue
            _da,_db=groups[a][1],groups[b][1]
            if len(_da)>=2 and len(_db)>=2:
                try:
                    _u,_p=_st.mannwhitneyu(_da,_db,alternative="two-sided")
                    _pmat[a][b]=f"{_p:.2g} {_stars(_p)}"
                    if a<b: _grid_rows.append([_gshort[a],_gshort[b],round(float(_p),5),_stars(_p)])
                except Exception: _pmat[a][b]="n/a"
            else: _pmat[a][b]="n/a"
    axT.axis("off")
    _tbl=axT.table(cellText=_pmat,rowLabels=_gshort,colLabels=_gshort,loc="center",cellLoc="center")
    _tbl.auto_set_font_size(False); _tbl.set_fontsize(7.5); _tbl.scale(1,1.5)
    axT.set_title("Pairwise metaphase-duration comparison — Mann–Whitney U (two-sided): p-value + significance",fontsize=9,loc="left")
    ax.legend(handles=[_L([0],[0],color="#444",lw=2.6,label="median"),_L([0],[0],color="#444",lw=1.3,ls=(0,(2,1.5)),label="mean")],loc="upper right",fontsize=7.5)
    ax.set_ylabel("Metaphase duration (MM:SS)"); ax.yaxis.set_major_formatter(FuncFormatter(lambda v,_: lib.mmss(v) if v>=0 else ""))
    ax.set_title("ZM sensitivity — full comparison (Control, 3-sisterless target-ablated, ZM on/off-target, ZM unmodified)",loc="left",fontweight="bold",fontsize=9.5)
    plt.tight_layout(); plt.savefig(f"{OUT}/G4_zm_full.png",bbox_inches="tight"); plt.close()
    lib.record_plot("G4_zm_full",["group","metaphase_duration_min"],rows,
      {"type":"violin 5-group + pairwise stats grid","groups":["Control","Target-ablated 3-sis","ZM on-target","ZM off-target","ZM unmodified"],
       "stats":"pairwise Mann-Whitney U (two-sided), shown as a grid (LZ5) instead of on-plot marks","pairwise_grid":_grid_rows},SCRIPT,"ZM full comparison (5 groups)")
    print("ZM full N:",{g[0].replace(chr(10),' '):len(g[1]) for g in groups})
zm_full()
lib.flush_review("/Volumes/4 MB/ablation_figures_20260625/_review/outlier_review.csv")
