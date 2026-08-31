"""#2 — Violin: 1/2/3-sisterless metaphase duration vs mitotic-EXHAUSTION controls (colcemid, nocodazole),
each its own violin. Exhaustion duration = time in mitosis (NEBD->exit, or from imaging start for cells
already in metaphase) read from the Anaphase field; 'greater than X' = right-censored lower bound.
Color-coded by whether the cell was already IN METAPHASE at the start of imaging
(Meta=0, or anaphase-without-metaphase, or noted)."""
import sys, json, re, numpy as np, matplotlib.pyplot as plt
sys.path.insert(0,"/Volumes/4 MB/ablation_figures_20260625"); import lib
from matplotlib.ticker import FuncFormatter
from matplotlib.lines import Line2D
from scipy import stats
import matplotlib.colors as mcol
lib.apply_style()
OUT="/Volumes/4 MB/ablation_figures_20260625/group4"; SCRIPT=__file__
data,_=lib.load_master_plots(); mr={r["Batch Name"]:r for r in data}
import os as _os   # prefer the 4 MB copy; /tmp is a cleanable fallback only
_EXJ="/Volumes/4 MB/ablation_figures_20260625/_inputs_exhaustion_batches.json"
d=json.load(open(_EXJ if _os.path.isfile(_EXJ) else "/tmp/exhaustion_batches.json"))
def is_col(b): bl=b.lower(); return "colcemid" in bl and "ablation" not in bl
def is_noc(b): bl=b.lower(); return "no_ablations_nocodazole" in bl

def parse_dur(s):
    """minutes, censored? from a time (H:MM:SS / H:MM) or free text ('3hrs','4hrs 30mins')."""
    s=(s or "").strip().lower()
    if not s: return None,False
    cens="greater than" in s or s.startswith(">")
    s=re.sub(r"greater than|>","",s).strip()
    m=re.match(r"^(\d{1,2}):(\d{2})(?::(\d{2}))?$",s)
    if m: return int(m.group(1))*60+int(m.group(2))+int(m.group(3) or 0)/60.0, cens
    h=re.search(r"(\d+)\s*hr",s); mn=re.search(r"(\d+)\s*min",s)
    if h or mn: return (int(h.group(1)) if h else 0)*60+(int(mn.group(1)) if mn else 0), cens
    return None,False

def in_meta_start(r):
    meta=(r.get("Metaphase Start (s)","")or"").strip().lower()
    ana=(r.get("Anaphase Onset (s)","")or"").strip(); notes=(r.get("Notes","")or"").lower()
    return meta in ("0","0:00:00","00:00:00","o") or (bool(ana) and not meta) or "metaphase at start" in notes or "in metaphase" in notes

# ---- collect ----
G={"1-Sisterless":[],"2-Sisterless":[],"3-Sisterless":[],"colcemid":[],"nocodazole":[]}
rec=[]
# sisterless = metaphase->anaphase duration. Use the CANONICAL lib.assign_cohorts() set
# (Exclude/drug/mad1/double-chromosome filtered + IQR-screened) so N for 1/2/3-sisterless is
# IDENTICAL to the main violin (g1_violin2) and the phase-split violin (group2_build).
_coh=lib.assign_cohorts()
for n in ("1","2","3"):
    for b,dd in _coh[f"{n}-Sister"]:
        G[f"{n}-Sisterless"].append((dd,False,False)); rec.append([b,f"{n}-sisterless",round(dd,1),0,0])
for b,grp in [(x,"colcemid") for x in d["colcemid"] if is_col(x)]+[(x,"nocodazole") for x in d["noc"] if is_noc(x)]:
    r=mr.get(b,{}); ana,cens=parse_dur(r.get("Anaphase Onset (s)","")); neb,_=parse_dur(r.get("NEB Time (s)",""))
    if ana is None: continue
    dur=ana-(neb or 0)                      # NEBD->exit, or from imaging start (in-meta cells have no NEB)
    if dur<=0: continue
    ims=in_meta_start(r)
    G[grp].append((dur,ims,cens)); rec.append([b,grp,round(dur,1),int(ims),int(cens)])

# ---- plot ----
order=["1-Sisterless","2-Sisterless","3-Sisterless","colcemid","nocodazole"]
PAL={"1-Sisterless":lib.PALETTE["1-Sister"],"2-Sisterless":lib.PALETTE["2-Sister"],"3-Sisterless":lib.PALETTE["3-Sister"],
     # nocodazole moved off blue: 2-Sisterless is already blue (#2166ac) on this same axis (user 2026-08-04)
     "colcemid":"#b35806","nocodazole":"#01665e"}
_CENS_BY_GROUP={}   # group -> count of right-censored points, reported under the axis (markers are uniform)
IMS_COLOR="#d62728"   # in-metaphase-at-start (red); not = group color
EXHAUSTION_GROUPS={"colcemid","nocodazole"}   # points homogenized in the journal variant (user 2026-08-03)
# ---- SUBSET COMPANIONS (user request via handoff-8 §7 #3; this figure is NOT windowable) ----------------
# `minutes` here is ONE DURATION PER CELL, not a timepoint, so make_window_companions_20260729.py cannot
# build a time-window companion for it and deliberately skips it. The two variants that ARE meaningful
# filter on the figure's own two quality flags instead:
#   nebd_captured  drop the cells that were already in metaphase when imaging started (the RED points).
#                  Their plotted duration is a LOWER BOUND because mitotic entry was never seen, so the
#                  exhaustion medians are biased DOWN by exactly the cells that arrested longest.
#   measured_exit  drop the right-censored cells (the OPEN TRIANGLES) — those had not exited mitosis when
#                  the movie ended, so their value is a minimum too. What is left is every cell whose exit
#                  was actually observed.
# Both are sensitivity checks on the same claim, and both are strictly SUBSETS — nothing is recomputed.
# Naming: `_win_<name>`. The suffix is not literally a time window, but it is the suffix that the family
# grouping and PLACE_ZOOMS_BESIDE_PARENT_20260729.jsx already know how to strip back to the parent
# (/_win_[a-z_]+$/), so the companion lands beside G4_exhaustion_violin_journal instead of adrift.
SUBSETS={
 "nebd_captured": (lambda val,ims,cens: not ims,
                   "NEBD-CAPTURED CELLS ONLY — cells already in metaphase when imaging began are removed, "
                   "because their duration is only a lower bound"),
 "measured_exit": (lambda val,ims,cens: not cens,
                   "OBSERVED-EXIT CELLS ONLY — right-censored cells (still in mitosis when the movie ended) "
                   "are removed, because their duration is only a lower bound"),
}

def build_exhaustion(journal=False,subset=None):
  # journal=True -> the "_journal" variant (scale='width', width=0.8, cut=0, points-only N<6) alongside original.
  # subset -> a key of SUBSETS; builds "<name>_win_<subset>" from the SAME data with those points removed.
  keep,subset_note=SUBSETS[subset] if subset else ((lambda *a: True),None)
  Gs={g:[v for v in G[g] if keep(*v)] for g in order} if subset else G
  n_removed=sum(len(G[g])-len(Gs[g]) for g in order)
  fig,ax=plt.subplots(figsize=(10,7.4))
  for i,g in enumerate(order):
    vals=[v[0] for v in Gs[g]]
    if journal:
        lib.journal_violin(ax,vals,i,PAL[g],alpha=.25)      # scale=width, width=0.8, cut=0, points-only N<6
    elif len(vals)>=2:
        for bd in ax.violinplot([vals],positions=[i],widths=.8,showextrema=False)['bodies']:
            bd.set_facecolor(PAL[g]); bd.set_alpha(.25); bd.set_edgecolor(PAL[g])
    # USER 2026-08-03 (journal variant): "homogenize points on colcemid and nocodazole plots". The
    # in-metaphase-at-start red/grey split carries no information in the exhaustion controls - those cells are
    # arrested by a spindle poison, not scored on when imaging caught them - so both control groups draw in one
    # uniform colour. The right-censored TRIANGLE is kept: it marks a ">" duration and is a property of the
    # datum, not styling; flattening it would silently redraw censored cells as completed ones.
    # USER 2026-08-04: every point on every group is now the same solid circle in that group's violin
    # colour - the marker style used on the other violins. That drops the red/grey in-metaphase-at-start
    # split on 1/2/3-sisterless and the censored triangle on the exhaustion controls. Right-censoring is
    # real information, so the counts are printed under the axis instead of being encoded in the marker.
    _ncens=0
    for (val,ims,cens) in Gs[g]:
        if cens: _ncens+=1
        ax.scatter(i+(np.random.RandomState(int(val*7)%99).rand()-.5)*.28,val,s=30,
                   facecolor=PAL[g],edgecolor="white",lw=.5,alpha=.85,zorder=3,marker="o")
    _CENS_BY_GROUP[g]=_ncens
    if vals:
        ax.hlines(np.median(vals),i-.32,i+.32,color=PAL[g],lw=2.6,zorder=4)                    # median (solid)
        ax.hlines(np.mean(vals),i-.28,i+.28,color=PAL[g],lw=1.4,ls=(0,(2,1.5)),zorder=4)        # mean (dashed)
        ax.text(i,max(vals)+3,f"x̄ {lib.mmss(np.mean(vals))}\nmed {lib.mmss(np.median(vals))}\nN={len(vals)}",ha="center",va="bottom",fontsize=7.5)
  ax.set_xticks(range(len(order))); ax.set_xticklabels(["1-Sisterless","2-Sisterless","3-Sisterless","colcemid\n(exhaustion)","nocodazole\n(exhaustion)"])
  ax.set_ylabel("Time in mitosis (MM:SS)"); ax.yaxis.set_major_formatter(FuncFormatter(lambda v,_: lib.mmss(v) if v>=0 else ""))
  ax.set_title("Metaphase duration (sisterless) vs\nmitotic-exhaustion controls (colcemid, nocodazole)",loc="left",fontweight="bold",fontsize=10)
  # legend reduced to the summary lines: every point is now one circle in its group's colour, so the
  # old red/grey and triangle keys describe nothing on the figure (user 2026-08-04).
  ax.legend(handles=[Line2D([0],[0],color='#555',lw=2.6,label='median'),
                     Line2D([0],[0],color='#555',lw=1.4,ls=(0,(2,1.5)),label='mean')],
            fontsize=7.5,loc="upper left")
  # 2026-08-05 (user): the right-censored count line under the axis is REMOVED - she does not want it.
  # ---------- pairwise significance (Mann-Whitney U, adjacent pairs) ----------
  # USER 2026-08-03: "remove stats markings; I'll do this manually" -> the journal variant draws no brackets
  # and no stars. The non-journal variant keeps them.
  def _stars(p): return "***" if p<.001 else "**" if p<.01 else "*" if p<.05 else "ns"
  _gv={g:[v[0] for v in Gs[g]] for g in order}
  def _mwu(gi,gj):
    a,b=_gv[order[gi]],_gv[order[gj]]
    return stats.mannwhitneyu(a,b,alternative="two-sided").pvalue if (len(a)>=3 and len(b)>=3) else None
  if not journal:
    _ymaxall=max((max(v) for v in _gv.values() if v),default=1); _dh=_ymaxall*0.045
    _pairs=[(0,1),(1,2),(2,3),(3,4)]   # 1v2, 2v3-Sis, 3-Sis vs colcemid (the key sisterless-vs-exhaustion), colcemid vs noc
    _ytops=[]
    for k,(gi,gj) in enumerate(_pairs):
      p=_mwu(gi,gj)
      if p is None: continue
      base=max(max(_gv[order[gi]]),max(_gv[order[gj]]))
      y=base+_dh*2+k*_dh*1.5
      ax.plot([gi,gi,gj,gj],[y,y+_dh*.35,y+_dh*.35,y],color="#333",lw=1.0,clip_on=False)
      ax.text((gi+gj)/2,y+_dh*.42,f"{_stars(p)} p={p:.2g}",ha="center",va="bottom",fontsize=7.2)
      _ytops.append(y+_dh)
    if _ytops: ax.set_ylim(top=max(_ytops)+_dh*2)
  # ---------- ITEM 4b: on-figure explanatory paragraph ----------
  _para=("How to read this plot:  Each point is one cell's time in mitosis.  The sisterless groups (1/2/3-Sisterless) "
         "are metaphase-to-anaphase durations after laser-ablating that many kinetochores' sister KTs.  The two "
         "EXHAUSTION CONTROLS are cells arrested by spindle poisons — colcemid (microtubule depolymerizer) and "
         "nocodazole — which hold an unsatisfiable spindle-assembly checkpoint until the arrest 'exhausts' (slippage); "
         "they set the ceiling for how long these cells can stay in mitosis.\n"
         # 2026-08-04/05: every point is now one solid circle in its group's colour, so the caption must not
         # describe a red/grey code or triangles that are no longer drawn, nor the censored-count line (removed
         # at her request 2026-08-05). The lower-bound caveat stays as plain caption text.
         "Every point is drawn as a filled circle in its group's colour.  Solid bar = median, dashed bar = mean.  "
         "Some cells had not exited mitosis by the end of the movie, so those durations are lower bounds.  "
         + ("No significance markings are drawn on this figure; the full "
            "5×5 Mann–Whitney pairwise grid is in G4_exhaustion_statgrid."
            if journal else
            "Brackets = Mann–Whitney U (ns / * <.05 / ** <.01 / *** <.001); the full 5×5 "
            "pairwise grid is in G4_exhaustion_statgrid."))
  if subset_note:
      # say on the figure WHICH cells were removed and how many — a subset that does not announce itself
      # reads as a different measurement rather than the same one with points taken out
      _emptied=[g for g in order if G[g] and not Gs[g]]
      _para=(f"SUBSET COMPANION of G4_exhaustion_violin_journal — {subset_note}. "
             f"{n_removed} of {sum(len(G[g]) for g in order)} cells removed; nothing is recomputed. "
             f"The parent figure shows every cell."
             + (f"  A GROUP DISAPPEARS HERE, and that is the result, not a gap: "
                f"{', '.join(_emptied)} has NO cell that survives this filter "
                f"(all {', '.join(str(len(G[g])) for g in _emptied)} of them are excluded), so its whole "
                f"arrest duration rests on lower-bound cells." if _emptied else "")
             + "\n\n") + _para
  # USER 2026-08-11: "theres a bunch of text on the mitotic slippage plot, get it off". The on-figure
  # paragraph is dropped. It was legible at the old 7.4pt, but once the figure text was scaled 2.2x it
  # ran across the x-axis, the tick labels and itself. The wording is NOT lost — it is still recorded as
  # the figure caption via lib.record_plot below, which is where the deck legend reads it from.
  _CAPTION_TEXT = _para          # kept for record_plot; no longer drawn on the figure
  _fn=("G4_exhaustion_violin_journal" if journal else "G4_exhaustion_violin")+(f"_win_{subset}" if subset else "")+".png"
  plt.tight_layout(); plt.savefig(f"{OUT}/{_fn}",bbox_inches="tight"); plt.close()   # no reserved footnote band
  _srec=[r for r in rec if not subset or keep(r[2],bool(r[3]),bool(r[4]))]
  lib.record_plot(_fn[:-4],["batch","group","minutes","in_metaphase_at_start","censored"],_srec,
    {"type":"violin, 5 groups","sisterless":"meta->ana metaphase duration","drug":"time in mitosis (NEBD->exit or from start); 'greater than X' censored",
     "color":"red = in metaphase at start of imaging; open triangle = right-censored",
     **({"subset":subset_note,"removed":n_removed,"parent":"G4_exhaustion_violin_journal"} if subset else {})},
    SCRIPT,("Sisterless metaphase duration vs colcemid/nocodazole exhaustion — "+subset_note.split(" — ")[0]) if subset
           else "Sisterless metaphase duration vs colcemid/nocodazole exhaustion, colored by in-metaphase-at-start")
  print(f"  {_fn[:-4]}: N per group " + ", ".join(f"{g}={len(Gs[g])}" for g in order))
build_exhaustion(False); build_exhaustion(True)   # original + journal-standard (scale='width', width=0.8, cut=0, points-only N<6)
for _sub in SUBSETS: build_exhaustion(True,_sub)  # the two meaningful companions (handoff-8 §7 #3)
# ---------- Statistical grid (Mann-Whitney U pairwise) — S19 statgrid style ----------
GLAB={"1-Sisterless":"1-Sisterless","2-Sisterless":"2-Sisterless","3-Sisterless":"3-Sisterless",
      "colcemid":"colcemid\n(exhaustion)","nocodazole":"nocodazole\n(exhaustion)"}
gvals={g:[v[0] for v in G[g]] for g in order}
n=len(order); P=np.full((n,n),np.nan)
for i in range(n):
    for j in range(n):
        if i==j: continue
        a,b=gvals[order[i]],gvals[order[j]]
        if len(a)>=3 and len(b)>=3:
            P[i,j]=stats.mannwhitneyu(a,b,alternative="two-sided").pvalue
figS,axS=plt.subplots(figsize=(6.6,5.8))
cmap=mcol.ListedColormap(["#08519c","#3182bd","#9ecae1","#deebf7","#f7f7f7"])
bounds=[0,0.001,0.01,0.05,0.1,1]; norm=mcol.BoundaryNorm(bounds,cmap.N)
im=axS.imshow(P,cmap=cmap,norm=norm)
for i in range(n):
    for j in range(n):
        if np.isnan(P[i,j]): continue
        p=P[i,j]
        axS.text(j,i,lib.sig_cell(p),ha="center",va="center",fontsize=7,linespacing=1.25,
                 color="#111" if p>.05 else "white")
axS.set_xticks(range(n)); axS.set_yticks(range(n))
axS.set_xticklabels([GLAB[g].replace(chr(10),"/") for g in order],rotation=40,ha="right",fontsize=8)
axS.set_yticklabels([GLAB[g].replace(chr(10),"/") for g in order],fontsize=8)
axS.set_title("Statistical grid — Mann–Whitney U (time in mitosis)",loc="left",fontweight="bold",fontsize=10.5)
cb=figS.colorbar(im,ax=axS,fraction=0.046,pad=0.04,ticks=[0.0005,0.005,0.03,0.075,0.5])
cb.ax.set_yticklabels(["<.001","<.01","<.05","<.1","ns"]); cb.set_label("p-value")
plt.tight_layout(); plt.savefig(f"{OUT}/G4_exhaustion_statgrid.png",bbox_inches="tight"); plt.close()
_rg=[[order[i],order[j],("" if np.isnan(P[i,j]) else round(float(P[i,j]),6))] for i in range(n) for j in range(n) if i!=j]
lib.record_plot("G4_exhaustion_statgrid",["group_a","group_b","p_value"],_rg,
  {"type":"significance matrix","test":"Mann-Whitney U two-sided","metric":"time in mitosis (sisterless duration vs drug exhaustion)"},SCRIPT,
  "Pairwise Mann-Whitney U across the 5 exhaustion-violin groups")
print("exhaustion violin:",{g:len(G[g]) for g in order})
print("exhaustion statgrid: 5x5 Mann-Whitney saved -> G4_exhaustion_statgrid.png")
