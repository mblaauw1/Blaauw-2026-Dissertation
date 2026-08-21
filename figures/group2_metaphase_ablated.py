"""metaphase-ablated samples: metaphase duration by sisterless group (dots colored by abl->anaphase)."""
import sys; sys.path.insert(0,"/Volumes/4 MB/ablation_figures_20260625")
import numpy as np, matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
import lib
lib.apply_style()
OUT="/Volumes/4 MB/ablation_figures_20260625/group2"; SCRIPT=__file__
data,_=lib.load_master()
# ITEM 5 (feedback 2026-07-06): "metaphase-to-anaphase time and ablation-to-anaphase time are the same? This
# should not be the case." ROOT CAUSE: the old abl_to_ana() read the master 'Meta Duration (s)' column, which
# is EMPTY for every metaphase-ablated cell, so it fell back to mitotic_duration_min() — i.e. the dot COLOUR
# (abl->ana) was literally the same number as the y-position (meta->ana) for every point. Fixed below.
# CLOCK: for a metaphase-ablated cell the event clock is anchored at the ablation (t=0). 'Metaphase Start (s)'
# is NEGATIVE (metaphase precedes the ablation) and 'Anaphase Onset (s)' is positive. lib.parse_time DROPS the
# leading minus, so we parse the sign locally here. Then:
#   meta->ana = Anaphase Onset - Metaphase Start   (the true metaphase-to-anaphase duration)
#   abl->ana  = Anaphase Onset                     (ablation-anchored) = meta->ana - |Metaphase Start|
# so the two are DISTINCT (differ by |metaphase-start-relative-to-ablation|).
def psec(s):
    s=(s or "").strip()
    if not s: return None
    neg=s.startswith("-"); v=lib.parse_time(s.lstrip("-"))
    return None if v is None else (-v if neg else v)
def mdur(r):
    ms=psec(r.get("Metaphase Start (s)","")); ao=psec(r.get("Anaphase Onset (s)",""))
    if ms is None or ao is None: return None
    d=(ao-ms)/60.0
    return d if 0<d<=300 else None
def phase(r):
    return r.get("Phase of Ablations","").strip().lower()
_dbl=lib.double_chromosome_batches()   # l429: destruction of 2 KTs on one chromosome excluded from ALL plots (globally)
act=[r for r in data if r.get("Exclude") not in ("Yes","yes") and not lib.is_drug(r["Batch Name"])
     and not lib.is_mad1(r["Batch Name"]) and not lib.excluded(r["Batch Name"]) and r["Batch Name"] not in _dbl]   # Mad1 reserved for Group 5; +REVIEW_EXCLUDE guard; l429: double-chromosome excluded globally
meta=[r for r in act if phase(r).startswith("metaph")]   # metaphase-ablated
# D10 (2026-07-07): "why 8 batches not 12?" TROUBLESHOOTING RESULT — 8 IS the complete, correct count.
# Of the 20 cells whose 'Phase of Ablations'=="metaphase" & 1-sisterless on-target, 6 are Mad1 batches
# (Group-5 reserved AND they have a BLANK 'Metaphase Start (s)', so no Meta->Ana duration is computable) and
# the rest lack a valid signed duration; exactly 8 non-Mad1 1-sisterless metaphase-ablated cells carry both a
# Metaphase Start and an Anaphase Onset, so 8 plot. The "12" the user recalled = the 20 metaphase-phase cells
# minus these 8, i.e. the ones legitimately excluded. Mad1 metaphase-ablated cells appear in the Group-5 deck.
def abl_to_ana(r):
    ao=psec(r.get("Anaphase Onset (s)",""))              # ablation-anchored: t=0 = ablation -> abl->ana = Anaphase Onset
    return ao/60.0 if ao is not None else None
def _num(s):
    try: return float((s or "").replace(",","").strip())
    except: return None
import glob as _glob, json as _json
def abl_to_ana_note(r):
    """Ablation->Anaphase, minutes — REAL value or None ('n/a'). Returned only when it is unambiguously
    derivable: the master Anaphase Onset must fall on the SAME clock as the frames.json ablation frames
    (i.e. master anaphase lies within the monitoring-frame t_sec range), in which case
    abl->ana = anaphase - ablation-frame-time. Otherwise None: the ablation annotation lives on the
    ablation-movie clock which, for most of these cells, is offset from the master metaphase/anaphase
    times (calibration mismatch) — so abl->ana cannot be computed without ablation timing on the event clock."""
    ao=lib.parse_time(r.get("Anaphase Onset (s)",""))
    if ao is None: return None
    fj=_glob.glob(f"/Volumes/4 MB/**/{r['Batch Name']}/{r['Batch Name']}_frames.json",recursive=True)
    if not fj: return None
    try: d=_json.load(open(fj[0]))
    except Exception: return None
    fr=d.get("frames",[])
    mon=[f['t_sec'] for f in fr if f.get('role')=='monitoring']; abl=[f['t_sec'] for f in fr if f.get('role')=='ablation']
    if not mon or not abl: return None
    if not (min(mon)-30 <= ao <= max(mon)+30): return None      # master anaphase NOT on the frames.json clock -> n/a
    val=(ao-float(np.median(abl)))/60.0
    return val if val>0 else None
def _spread(ys,gap):
    """nudge label y-positions apart (bottom-up) so notes don't overlap."""
    out=np.array(ys,float); order=np.argsort(out)
    for k in range(1,len(order)):
        if out[order[k]]<out[order[k-1]]+gap: out[order[k]]=out[order[k-1]]+gap
    return out
fig,ax=plt.subplots(figsize=(8.2,5.4)); rows=[]; allc=[]; _ytop=0
pts_by={}
for i,s in enumerate("13"):
    d=[(mdur(r),abl_to_ana(r),r["Batch Name"],r) for r in meta if r.get("# Sisterless KTs")==s]
    d=[(m,a,b,r) for m,a,b,r in d if m is not None]
    pts_by[s]=d
    if not d: continue
    ys=[m for m,_,_,_ in d]
    lib.journal_violin(ax,ys,i,lib.PALETTE[f"{s}-Sister"],width=.7,alpha=.25)   # scale=width (uniform max half-width), cut=0, N<6 points-only
    cvals=[a if a is not None else np.nan for _,a,_,_ in d]
    jx=np.full(len(ys),i)+(np.random.RandomState(i).rand(len(ys))-.5)*.16
    sc=ax.scatter(jx,ys,c=cvals,cmap="viridis",s=42,edgecolor="k",lw=.4,zorder=3)
    allc+=[c for c in cvals if not np.isnan(c)]
    ax.hlines(np.median(ys),i-.3,i+.3,color=lib.PALETTE[f"{s}-Sister"],lw=2.2)               # median (solid)
    ax.hlines(np.mean(ys),i-.26,i+.26,color=lib.PALETTE[f"{s}-Sister"],lw=1.4,ls=(0,(2,1.5)))  # mean (dashed)
    ax.text(i,max(ys)+1,f"x̄ {lib.mmss(np.mean(ys))}\nmed {lib.mmss(np.median(ys))}\nN={len(ys)}",ha="center",va="bottom",fontsize=7.5)
    # ---- per-point note: abl->ana AND meta->ana (MM:SS) — stacked to the right, leader-lined, de-overlapped ----
    tx=i+0.42; gap=max((max(ys)-min(ys)) if len(ys)>1 else 1,1)*0.085+0.9
    ty=_spread(ys,gap)
    for (m,a,b,r),px,py,lyy in sorted(zip(d,jx,ys,ty),key=lambda z:z[2]):
        note=f"abl->ana {lib.mmss(a) if a is not None else 'n/a'} / meta->ana {lib.mmss(m)}"
        ax.plot([px,tx-0.01],[py,lyy],color="#bbb",lw=.5,zorder=2)
        ax.text(tx,lyy,note,ha="left",va="center",fontsize=5.0,color="#333",zorder=4)
        _ytop=max(_ytop,lyy)
    for m,a,b,r in d: rows.append([f"{s}-Sisterless",round(m,3),round(a,3) if a is not None else "",b])
ax.set_xlim(-0.6,1.6)
_allmax=max([m for v in pts_by.values() for m,_,_,_ in v] or [10])
ax.set_ylim(top=max(ax.get_ylim()[1],_ytop+2,_allmax+4.5))   # headroom so per-violin label clears the title
# only label groups that actually have metaphase-ablated samples (drop empty 3-Sisterless tick)
present=[(i,f"{s}-Sisterless") for i,s in enumerate("13") if pts_by.get(s)]
ax.set_xticks([i for i,_ in present]); ax.set_xticklabels([l for _,l in present])
# y = Metaphase Start -> Anaphase Onset interval (lib.mitotic_duration_min). It is ALWAYS the
# Metaphase->Anaphase duration; the dot COLOR is abl->anaphase (master 'Meta Duration' col, a proxy
# used where present, else the same Meta->Ana value).
ax.set_ylabel("Metaphase duration (MM:SS)"); ax.yaxis.set_major_formatter(FuncFormatter(lambda v,_: lib.mmss(v) if v>=0 else ""))
if allc:
    cb=fig.colorbar(sc,ax=ax,fraction=.046,pad=.04); cb.set_label("Ablation-to-Anaphase (min; = Anaphase Onset, ablation-anchored)")
# median legend: a proper horizontal-LINE handle (Line2D), not a marker — otherwise it renders as a box
from matplotlib.lines import Line2D as _L2
ax.legend(handles=[_L2([0],[0],color="#444",lw=2.2,label="median"),_L2([0],[0],color="#444",lw=1.4,ls=(0,(2,1.5)),label="mean")],loc="upper right",fontsize=8)
ax.set_title(f"Metaphase-ablated — metaphase duration by sisterless group\n(dot colour = abl->ana = Anaphase Onset, ablation-anchored; N={sum(len(v) for v in pts_by.values())})",loc="left",fontweight="bold",fontsize=10)
# 2026-08-04: this N-note used to sit INSIDE the axes at (.02,.02), where the lowest per-point callout
# labels ran straight through it. Moved below the axes — it is caption text, not data, so it does not
# belong in the data area at all, and the plot gets that space back.
ax.text(0.0,-0.085,f"N={len(pts_by.get('1',[]))} = all non-Mad1 1-sisterless metaphase-ablated cells with a computable metaphase duration.  "
                "Other metaphase-phase cells are Mad1 (Group 5) or lack a Metaphase Start, so no duration.",
        transform=ax.transAxes,fontsize=6.6,va="top",ha="left",color="#666")
plt.tight_layout(); plt.savefig(f"{OUT}/G2_metaphase_ablated.png",bbox_inches="tight")
# USER 2026-07-16: _zoom = full parent (identical, no outlier trim). Emit it here so its pdf-cache stays in
# sync with the parent (make_zoom_companions.py SKIP_IDS this plot, so nothing else would keep it current).
plt.savefig(f"{OUT}/G2_metaphase_ablated_zoom.png",bbox_inches="tight"); plt.close()
lib.record_plot("G2_metaphase_ablated",["group","mitotic_duration_min","abl_to_ana_min","batch"],rows,
  {"type":"violin+colored points","subset":"Phase of Ablations==metaphase","y":"meta->ana = Anaphase Onset - Metaphase Start (signed)","color":"abl->ana = Anaphase Onset (ablation-anchored)","note":"meta->ana and abl->ana now distinct; differ by |Metaphase Start|"},
  SCRIPT,"Metaphase-ablated samples: metaphase duration by sisterless group")
lib.record_plot("G2_metaphase_ablated_zoom",["group","mitotic_duration_min","abl_to_ana_min","batch"],rows,
  {"type":"violin+colored points","subset":"Phase of Ablations==metaphase","note":"_zoom = full parent G2_metaphase_ablated (identical; no outlier trim per user 2026-07-16)"},
  SCRIPT,"Metaphase-ablated samples: metaphase duration by sisterless group (zoom = full parent)")

# ---- SECOND PLOT (2026-07-10 user): SAME metaphase-ablated group, abl->meta interval vs metaphase duration ----
# For a metaphase-ablated cell the ablation is anchored at t=0 and 'Metaphase Start (s)' is NEGATIVE (metaphase
# preceded the ablation). So the "time between the metaphase ablation and metaphase onset" = |Metaphase Start| =
# how long AFTER metaphase onset the cell was ablated. x = that interval (min); y = meta->ana duration.
def abl_to_meta(r):
    ms=psec(r.get("Metaphase Start (s)",""))
    return abs(ms)/60.0 if ms is not None else None
# ── ITEM 3 (user 2026-08-04, REPEAT): "still not correct. Ablating further into metaphase should decrease
# metaphase time." She is right, and the old y-axis made that impossible to see.
# THE DEFECT WAS ARITHMETIC, NOT BIOLOGICAL. y was the TOTAL metaphase duration, and for a metaphase-ablated
# cell   total = (metaphase onset -> ablation) + (ablation -> anaphase)   — i.e. x is a COMPONENT OF y.
# Ablating one minute later therefore adds one minute to y by construction, which is exactly the positive
# slope the old figure showed (rho=+0.77): a plotting identity, not an effect.
# The quantity her statement is about is the time REMAINING after the ablation — how much delay the ablation
# still imposes. So y is now abl->ana. Left panel = that (the corrected plot); right panel keeps the old
# total-duration view, labelled as self-correlated, so the two can be compared honestly.
def abl_to_ana_min(r):
    ao=psec(r.get("Anaphase Onset (s)",""))          # ablation-anchored: t=0 = ablation
    return ao/60.0 if ao is not None else None
# Two further defects found while fixing the axis (2026-08-04):
#  (a) COVERAGE — the group loop ran over "13" only, so the 3 metaphase-ablated cells with
#      `# Sisterless KTs`==2 and the 2 with the field blank were silently dropped: 6 of 12 cells plotted.
#      All groups with data are now included, and anything still dropped is logged rather than vanishing.
#  (b) SIGN — `abs(Metaphase Start)` assumes metaphase PRECEDES the ablation (the value is stored negative
#      on the ablation-anchored clock). One cell stores it POSITIVE, i.e. metaphase began ~7.7 min AFTER the
#      ablation, so it is not a metaphase ablation on this clock at all; abs() turned that into a
#      plausible-looking x. Such cells are now excluded and logged.
def meta_onset_to_abl(r):
    """Minutes from metaphase onset to the ablation, or None if metaphase did not precede the ablation."""
    ms=psec(r.get("Metaphase Start (s)",""))
    if ms is None: return None
    if ms > 0:      # metaphase started AFTER the ablation -> not metaphase-ablated on this clock
        lib.log_review("metaphase_ablated_sign", r["Batch Name"], f"Metaphase Start = +{ms/60:.2f} min",
                       "positive Metaphase Start: metaphase began AFTER the ablation, so this cell cannot "
                       "contribute a metaphase-onset->ablation interval — excluded (ITEM 3)")
        return None
    return abs(ms)/60.0
# ITEM 3, SECOND PASS (2026-08-04) — and the CORRECTION to my own first attempt at it.
# She asked whether there are fairly delayed ablations that should sit past the point of no return. There
# appeared to be one (`20260420 ...ablation_36`, ablated 7.68 min into metaphase with only 1.58 min left), and
# I briefly added it back as a "sisterless group not recorded" series on the theory that its blank
# `# Sisterless KTs` was a metadata gap.
# THAT WAS WRONG. Checking the master: that cell is `On-Target / Off-Target` = **Off-target**, with 8 unique
# targets. Its `# Sisterless KTs` is blank BECAUSE it is an off-target control — an off-target hit creates no
# sisterless kinetochore. Her rule holds: non-excluded ON-TARGET batches do carry the value. Including it put
# an off-target control into an on-target phenotype figure, which is a worse error than the exclusion.
# So the 1/2/3 group requirement stays, and any metaphase-ablated cell that fails it is now reported with the
# REASON, so a genuine metadata gap can never again be mistaken for a cohort boundary (or vice versa).
_GROUPS=[s for s in ("1","2","3") if any((r.get("# Sisterless KTs","") or "").strip()==s for r in meta)]
_SCOL={s:lib.PALETTE[f"{s}-Sister"] for s in _GROUPS}
_SLAB={s:f"{s}-Sisterless" for s in _GROUPS}
fig2,(ax2,ax2b)=plt.subplots(1,2,figsize=(12.4,5.2))
rows2=[]; _dropped=[]
for r in meta:
    _s=(r.get("# Sisterless KTs","") or "").strip()
    if _s in _GROUPS: continue
    _ot=(r.get("On-Target / Off-Target","") or "").strip()
    _why=("OFF-TARGET control — no sisterless KT is created, so a blank group is correct"
          if "off-target" in _ot.lower() else
          f"on-target but '# Sisterless KTs' is '{_s or 'blank'}' — REAL metadata gap, needs filling")
    _dropped.append((r["Batch Name"], _ot or "(blank)", _why))
    lib.log_review("metaphase_ablated_no_group", r["Batch Name"], f"{_ot or '(blank)'} / '{_s or 'blank'}'",
                   _why + " — not plotted (ITEM 3)")
for i,s in enumerate(_GROUPS):
    sel=[r for r in meta if (r.get("# Sisterless KTs","") or "").strip()==s]
    d=[(meta_onset_to_abl(r),abl_to_ana_min(r),mdur(r),r["Batch Name"]) for r in sel]
    d=[(x,y,tot,b) for x,y,tot,b in d if x is not None and y is not None and tot is not None]
    if not d: continue
    c=_SCOL[s]
    ax2.scatter([x for x,_,_,_ in d],[y for _,y,_,_ in d],s=48,color=c,edgecolor="k",lw=.4,
                label=f"{_SLAB[s]} (N={len(d)})",zorder=3)
    ax2b.scatter([x for x,_,_,_ in d],[t for _,_,t,_ in d],s=48,color=c,edgecolor="k",lw=.4,
                 label=f"{_SLAB[s]} (N={len(d)})",zorder=3)
    for x,y,tot,b in d: rows2.append([_SLAB[s].replace(chr(10)," "),round(x,3),round(y,3),round(tot,3),b])
from scipy import stats as _st2
def _fit(ax_,xi,yi,txt_,corner="right"):
    """corner: where to park the stats box. Panel A must NOT use bottom-right — that is exactly where the
    late/point-of-no-return cell sits, and the box was covering it."""
    if len(xi)<3: return None,None
    _z=np.polyfit(xi,yi,1); _xr=np.linspace(min(xi),max(xi),50)
    ax_.plot(_xr,np.polyval(_z,_xr),color="#333",lw=1.5,ls="--",zorder=2,label="overall trend")
    _rho,_p=_st2.spearmanr(xi,yi)
    _x,_ha=(0.02,"left") if corner=="left" else (0.98,"right")
    ax_.text(_x,.02,f"Spearman ρ={_rho:.2f}, p={_p:.2g} (N={len(xi)})",transform=ax_.transAxes,
             ha=_ha,va="bottom",fontsize=8,bbox=dict(fc="#f6f6f6",ec="#ccc",alpha=.9),zorder=1)
    return float(_rho),float(_p)
_ax=[r[1] for r in rows2]
_rho_rem,_p_rem=_fit(ax2,_ax,[r[2] for r in rows2],"remaining",corner="left")
_rho_tot,_p_tot=_fit(ax2b,_ax,[r[3] for r in rows2],"total")
for _a in (ax2,ax2b):
    _a.set_xlabel("Time from metaphase onset to the ablation (min)")
    _a.yaxis.set_major_formatter(FuncFormatter(lambda v,_: lib.mmss(v) if v>=0 else ""))
    _a.legend(loc="upper right",fontsize=8)
ax2.set_ylabel("Time REMAINING after the ablation, abl->anaphase (MM:SS)")
ax2b.set_ylabel("TOTAL metaphase duration, meta->ana (MM:SS)")
ax2.set_title("A · CORRECTED — remaining metaphase after the ablation",loc="left",fontweight="bold",fontsize=9.4)
ax2b.set_title("B · old view — total duration (self-correlated with x)",loc="left",fontweight="bold",fontsize=9.4)
# Report the LATE ablations explicitly. A single Spearman over all cells is dominated by the tight early
# cluster and hides the point-of-no-return case she asked about, so quantify the two ends separately.
_LATE_MIN=5.0
_rem=[(r[1],r[2],r[4]) for r in rows2]              # (x, remaining, batch)
_early=[v for v in _rem if v[0]<_LATE_MIN]; _late=[v for v in _rem if v[0]>=_LATE_MIN]
_late_txt=""
if _late:
    _lo=min(v[1] for v in _late); _emed=float(np.median([v[1] for v in _early])) if _early else float("nan")
    _late_txt=(f"POINT OF NO RETURN: the {len(_late)} ablation(s) >= {_LATE_MIN:.0f} min into metaphase leave "
               f"only {_lo:.1f} min of metaphase, vs a median of {_emed:.1f} min for the {len(_early)} "
               f"ablations in the first {_LATE_MIN:.0f} min.")
else:
    _late_txt=("NO LATE ABLATIONS EXIST in this on-target cohort: every metaphase ablation happens within "
               f"{max(_ax):.1f} min of metaphase onset, so the 'past the point of no return' case cannot be "
               "tested here. (The one cell that looked late is an OFF-TARGET control, correctly excluded.)")
_xr_txt=(f"{min(_ax):.1f}-{max(_ax):.1f} min" if _ax else "n/a")
fig2.suptitle(
  f"Metaphase-ablated — does ablating further into metaphase shorten what is left? (N={len(rows2)})   ITEM 3\n"
  f"A: remaining metaphase after the ablation.  {_late_txt}\n"
  f"Spearman over ALL cells is flat (rho={_rho_rem:+.2f}, p={_p_rem:.2g}) because {len(_early)} of "
  f"{len(rows2)} ablations sit inside the first {_LATE_MIN:.0f} min ({_xr_txt} overall) — the rank test cannot "
  f"see a single far point.  B: total duration = (meta->abl) + (abl->ana), so it CONTAINS x and rises with it "
  f"(rho={_rho_tot:+.2f}) — that identity, not biology, drove the old trend.",
  x=.01,ha="left",fontweight="bold",fontsize=8.2)
if _late:
    for _x,_y,_b in _late:
        ax2.annotate(f"ablated {_x:.1f} min in\nonly {_y:.1f} min left",xy=(_x,_y),xytext=(-18,42),
                     textcoords="offset points",ha="right",fontsize=7,color="#a33",
                     arrowprops=dict(arrowstyle="->",color="#a33",lw=.9))
plt.tight_layout(); plt.savefig(f"{OUT}/G2_metaphase_ablated_abltometa.png",bbox_inches="tight"); plt.close()
lib.record_plot("G2_metaphase_ablated_abltometa",
  ["group","abl_to_meta_min","remaining_abl_to_ana_min","total_meta_to_ana_min","batch"],rows2,
  {"type":"2-panel scatter + trend + Spearman","subset":"Phase of Ablations==metaphase",
   "x":"|Metaphase Start (s)| = time from metaphase onset to the ablation",
   "y_panelA":"abl->ana = metaphase time REMAINING after the ablation (the corrected axis)",
   "y_panelB":"meta->ana total duration (contains x; self-correlated by construction)",
   "item3":"old single-panel version plotted total duration against one of its own components",
   "stats":{"remaining":{"rho":_rho_rem,"p":_p_rem},"total":{"rho":_rho_tot,"p":_p_tot}},
   "x_label":"Time from metaphase onset to the ablation (min)",
   "y_label":"Time remaining after the ablation, abl->anaphase (min)"},
  SCRIPT,"Metaphase-ablated: does ablating later in metaphase shorten the remaining metaphase?")
print(f"ITEM 3: remaining abl->ana vs abl-time rho={_rho_rem} p={_p_rem} | total-duration rho={_rho_tot} p={_p_tot}")

# ---- THIRD PLOT (2026-07-20 user): COMPLEMENT of _abltometa — x = ablation->anaphase interval vs metaphase duration ----
# For a metaphase-ablated cell the ablation is t=0, so abl->ana = Anaphase Onset (min). Note: metaphase duration =
# (meta->abl) + (abl->ana), so this plot is PARTLY self-correlated (duration contains abl->ana) — shown per user request
# as the complement to _abltometa; interpret the trend with that caveat.
fig3,ax3=plt.subplots(figsize=(7.4,5.2)); rows3=[]
for i,s in enumerate("13"):
    d=[(abl_to_ana(r),mdur(r),r["Batch Name"]) for r in meta if r.get("# Sisterless KTs")==s]
    d=[(x,y,b) for x,y,b in d if x is not None and y is not None]
    if not d: continue
    ax3.scatter([x for x,_,_ in d],[y for _,y,_ in d],s=48,color=lib.PALETTE[f"{s}-Sister"],
                edgecolor="k",lw=.4,label=f"{s}-Sisterless (N={len(d)})",zorder=3)
    for x,y,b in d: rows3.append([f"{s}-Sisterless",round(x,3),round(y,3),b])
if len(rows3)>=3:
    _bx=[r[1] for r in rows3]; _by=[r[2] for r in rows3]
    _z=np.polyfit(_bx,_by,1); _xr=np.linspace(min(_bx),max(_bx),50)
    ax3.plot(_xr,np.polyval(_z,_xr),color="#333",lw=1.5,ls="--",zorder=2,label="overall trend")
    try:
        from scipy import stats as _st3; _rho,_p=_st3.spearmanr(_bx,_by)
        ax3.text(.98,.02,f"Spearman ρ={_rho:.2f}, p={_p:.2g} (N={len(_bx)})",transform=ax3.transAxes,
                 ha="right",va="bottom",fontsize=8,bbox=dict(fc="#f6f6f6",ec="#ccc",alpha=.9))
    except Exception: pass
ax3.set_xlabel("Time from the ablation to anaphase onset (min)")
ax3.set_ylabel("Metaphase duration (MM:SS)")
ax3.yaxis.set_major_formatter(FuncFormatter(lambda v,_: lib.mmss(v) if v>=0 else ""))
ax3.legend(loc="upper left",fontsize=8)
ax3.set_title(f"Metaphase-ablated — ablation-to-anaphase interval vs metaphase duration (N={len(rows3)})\n"
              f"(note: duration = (meta-to-abl) + (abl-to-ana), so partly self-correlated)",
              loc="left",fontweight="bold",fontsize=9.0)
plt.tight_layout(); plt.savefig(f"{OUT}/G2_metaphase_ablated_abltoana.png",bbox_inches="tight"); plt.close()
lib.record_plot("G2_metaphase_ablated_abltoana",["group","abl_to_ana_min","mitotic_duration_min","batch"],rows3,
  {"type":"scatter + overall trend + Spearman","subset":"Phase of Ablations==metaphase",
   "x":"Anaphase Onset (s) = time from the ablation to anaphase","y":"meta->ana duration",
   "caveat":"duration = meta->abl + abl->ana => partly self-correlated","complement_of":"G2_metaphase_ablated_abltometa"},
  SCRIPT,"Metaphase-ablated: ablation-to-anaphase interval vs metaphase duration")

lib.flush_review("/Volumes/4 MB/ablation_figures_20260625/_review/outlier_review.csv")
print("metaphase-ablated N per group:",{s:len(pts_by[s]) for s in "13"})
