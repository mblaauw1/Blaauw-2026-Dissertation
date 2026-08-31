"""Targeted Kinetochore Localization: KT fate, edge distance, origin-normalized position, chromosome length."""
import sys; sys.path.insert(0,"/Volumes/4 MB/ablation_figures_20260625")
import csv, json, numpy as np, matplotlib.pyplot as plt
from collections import defaultdict
from matplotlib.ticker import FuncFormatter
import lib
lib.apply_style()
OUT="/Volumes/4 MB/ablation_figures_20260625/group3"; import os; os.makedirs(OUT,exist_ok=True); SCRIPT=__file__
data,_=lib.load_master_plots(); mr={r["Batch Name"]:r for r in data}
_dbl=lib.double_chromosome_batches()   # l429: destruction of 2 KTs on one chromosome excluded from ALL plots (globally)
def md(b):
    r=mr.get(b);
    if not r: return None
    d,ok=lib.mitotic_duration_min(r); return d if ok else None
def phase(b):
    p=mr.get(b,{}).get("Phase of Ablations","").strip().lower()
    ph="Prophase" if p.startswith("proph") else "Prometaphase" if p.startswith("promet") else "Metaphase" if p.startswith("metaph") else None
    return "Prometaphase" if (ph=="Prophase" and lib.is_v2_prometaphase(b)) else ph   # USER 2026-07-16: v2 binning
def ps(b):
    try: return float(mr.get(b,{}).get("Pixel Size (um)",""))
    except: return 0.062
PCOL={"Prophase":"#1b7837","Prometaphase":"#2166ac","Metaphase":"#762a83",None:"#999"}
def _pxs_text(records):
    """D9/X2 (2026-07-07): N listed per phase × sisterless (prophase-1sis, prometa-1sis, meta-1sis, ...),
    NOT lumped as separate per-phase and per-sisterless totals. records = rows whose [0]=batch, [3]=phase."""
    from collections import Counter as _Cn
    cnt=_Cn()
    for r in records:
        s=mr.get(r[0],{}).get("# Sisterless KTs","")
        if s in "123": cnt[(r[3],s)]+=1
    lines=["N (phase × sisterless):"]
    for ph in ["Prophase","Prometaphase","Metaphase"]:
        parts=[f"{s}-sis {cnt[(ph,s)]}" for s in "123" if cnt[(ph,s)]]
        if parts: lines.append(f"  {ph}: "+", ".join(parts))
    return "\n".join(lines)

# ---------- 1. KT fate ----------
# S37 feedback: the three fate categories must be DISTINCT. Semantics of chromosome_k_plate_join:
#   "anaphase"      -> the polar (sisterless) KT never joins the plate; stays polar right up to anaphase
#   "0" / "0:00:00" -> the KT was AT the metaphase plate the entire time (joined at t=0 / never went polar)
#   finite non-zero -> the KT started polar then MOVED to the plate at that time
r=list(csv.reader(open("/Volumes/4 MB/annotations/SISTERLESS_PLATE_JOIN_TIMES.csv"))); ix={c:i for i,c in enumerate(r[0])}
fate=defaultdict(lambda: defaultdict(int)); recF=[]
for row in r[1:]:
    if row[ix['exclude_this_data']].strip(): continue
    if lib.is_mad1(row[ix['batch']].strip()) or lib.plot_excluded(row[ix['batch']].strip()) or row[ix['batch']].strip() in _dbl: continue  # l429: double-chromosome excluded globally
    n=row[ix['n_sisterless']].strip()
    if n not in ("1","2","3"): continue
    for k in (1,2,3):
        v=row[ix[f'chromosome_{k}_plate_join']].strip()
        s=row[ix[f'chromosome_{k}_plate_join_s']].strip()
        if not v or v.lower()=="n/a": continue
        if v.lower()=="anaphase": cat="remains at pole (polar to anaphase)"
        elif v in ("0","0:00:00"): cat="at metaphase plate the entire time"
        else: cat="moves to plate"
        fate[n][cat]+=1; recF.append([row[ix['batch']],n,cat,s])
# USER 2026-08-16 (NOTES §1 rule 30): "there are instances of red and green being used together, and this
# cannot be, because many men have red-green colorblindness." This stack paired #b2182b (red) with #5aae61
# (green) — the exact forbidden pair, and the two categories a reader most needs to tell apart. Replaced
# with Okabe-Ito vermillion / blue / reddish-purple, which stay distinct under deuteranopia and protanopia
# and carry NO green at all.
CATS=["remains at pole (polar to anaphase)","moves to plate","at metaphase plate the entire time"]; CC=["#d55e00","#0072b2","#cc79a7"]
fig,a1=plt.subplots(figsize=(6.2,5.0))   # S37: single fate-composition panel; movers time-to-plate plot removed (that data lives on G3_plate_join_timing)
for i,n in enumerate("13"):   # S36: 1 & 3-sisterless only (no 2-sisterless data)
    tot=sum(fate[n].values()) or 1; bottom=0
    for c,col in zip(CATS,CC):
        f=fate[n][c]/tot; a1.bar(i,f,bottom=bottom,color=col,width=.7,label=c if i==0 else None)
        if f>0.03:   # audio s37: label each stacked section with its fraction
            a1.text(i,bottom+f/2,f"{f*100:.0f}%",ha="center",va="center",fontsize=8.5,color="white",fontweight="bold")
        bottom+=f
    a1.text(i,1.02,f"N={sum(fate[n].values())}",ha="center",fontsize=8)
a1.set_xticks([0,1]); a1.set_xticklabels(["1-Sisterless","3-Sisterless"]); a1.set_ylabel("fraction of kinetochores"); a1.set_ylim(0,1.18); a1.set_xlim(-0.6,1.6)
a1.legend(fontsize=7.5,loc="upper center",ncol=1,bbox_to_anchor=(.5,-.10)); a1.set_title("Fate composition",fontsize=10)   # legend below, off the bars
fig.suptitle("Targeted-kinetochore fate by sisterless group",x=.01,ha="left",fontweight="bold")
plt.tight_layout(); plt.savefig(f"{OUT}/G3_kt_fate.png",bbox_inches="tight"); plt.close()
lib.record_plot("G3_kt_fate",["batch","n_sisterless","fate","time_s"],recF,{"type":"stacked bar","source":"SISTERLESS_PLATE_JOIN_TIMES","note":"3 distinct fates; time-to-plate movers panel removed per S37"},SCRIPT,"KT fate categorization")

# ---------- outlines (abl phase) + pre_abl positions ----------
co=list(csv.reader(open("/Volumes/4 MB/annotations/cell_outlines.csv"))); ox={c:i for i,c in enumerate(co[0])}
ablout={}
for x in co[1:]:
    if x[ox['phase']]=='abl':
        try: ablout[x[ox['batch']].strip()]=np.array(json.loads(x[ox['points']]),float)
        except: pass
kt=list(csv.reader(open("/Volumes/4 MB/annotations/kt_points.csv"))); kx={c:i for i,c in enumerate(kt[0])}
preabl=defaultdict(list)
for x in kt[1:]:
    if x[kx['label']].strip()=='pre_abl':
        if lib.is_mad1(x[kx['batch']].strip()) or lib.plot_excluded(x[kx['batch']].strip()) or x[kx['batch']].strip() in _dbl: continue  # l429: double-chromosome excluded globally
        try: preabl[x[kx['batch']].strip()].append((float(x[kx['x']]),float(x[kx['y']])))
        except: pass
def pt_poly(p,poly):
    p=np.array(p,float); d=1e18
    for i in range(len(poly)-1):
        a,b=poly[i],poly[i+1]; ab=b-a; L=np.dot(ab,ab); t=0 if L<1e-9 else np.clip(np.dot(p-a,ab)/L,0,1)
        d=min(d,np.hypot(*(a+t*ab-p)))
    return d

# ---------- 2. Edge distance vs duration (by sister group, colored by phase) ----------
fig,axes=plt.subplots(1,3,figsize=(13,4.6),sharey=True); recE=[]
for ax,s in zip(axes,"123"):
    PX=[];PY=[]; pph=defaultdict(lambda:([],[])); cellE={}   # per-phase (x,y); cellE[batch]=[edges,duration]
    for b,pos in preabl.items():
        if b not in ablout or mr.get(b,{}).get("# Sisterless KTs")!=s: continue
        d=md(b);
        if d is None: continue
        for (x,y) in pos:
            ed=pt_poly((x,y),ablout[b])*ps(b)
            if ed>40:   # slide-38: the >40µm 1-sisterless point — review-list, don't plot
                lib.log_review("edge_distance_outlier",b,f"{ed:.1f}µm",">40µm ablation-to-edge EXCLUDED; review"); continue
            ax.scatter(ed,d,s=28,color=PCOL[phase(b)],alpha=.8,edgecolor="white",lw=.3); recE.append([b,s,round(ed,3),round(d,3),phase(b)]); PX.append(ed);PY.append(d)
            pph[phase(b)][0].append(ed); pph[phase(b)][1].append(d); cellE.setdefault(b,[[],d])[0].append(ed)
    for _ph in ["Prophase","Prometaphase","Metaphase"]:   # per-phase trend line (color = phase)
        xx,yy=pph.get(_ph,([],[]))
        if len(xx)>=3:
            m,b0=np.polyfit(xx,yy,1); xr=np.linspace(min(xx),max(xx),20); ax.plot(xr,m*xr+b0,"--",color=PCOL[_ph],lw=1.5)
    if len(PX)>=3:   # overall trend line (all phases pooled)
        m,b0=np.polyfit(PX,PY,1); xr=np.linspace(min(PX),max(PX),20); ax.plot(xr,m*xr+b0,"-",color="#222",lw=1.8)
    # --- pseudoreplication-aware stats: does ablation toward the edge -> longer metaphase delay? ---
    # 1-sisterless: each cell has ONE ablation location -> points are independent -> Spearman directly (PRIMARY).
    # 2/3-sisterless: 2-3 locations share ONE duration -> NOT independent -> average distance per cell (one pt/cell).
    from scipy.stats import spearmanr as _spr
    if s=="1":
        if len(PX)>=4:
            _r,_p=_spr(PX,PY); ax.text(.04,.97,f"Spearman ρ={_r:.2f}, p={_p:.2g}\n(1 ablation/cell — independent; N={len(PX)})",
                transform=ax.transAxes,va="top",fontsize=6.8,color="#111",bbox=dict(fc="white",ec="#bbb",alpha=.85))
    else:
        cm=[(np.mean(v[0]),v[1]) for v in cellE.values() if v[0]]
        if len(cm)>=4:
            _r,_p=_spr([c[0] for c in cm],[c[1] for c in cm]); ax.text(.04,.97,f"per-cell mean dist: ρ={_r:.2f}, p={_p:.2g}\n(avoids pseudoreplication; N={len(cm)} cells)",
                transform=ax.transAxes,va="top",fontsize=6.8,color="#111",bbox=dict(fc="white",ec="#bbb",alpha=.85))
    ax.set_title(f"{s}-Sisterless",fontsize=10); ax.set_xlabel("ablation-to-cell-edge distance (µm)")
axes[0].set_ylabel("Metaphase duration (MM:SS)"); axes[0].yaxis.set_major_formatter(FuncFormatter(lambda v,_: lib.mmss(v) if v>=0 else ""))
from matplotlib.lines import Line2D
axes[2].legend(handles=[Line2D([0],[0],marker='o',color='w',markerfacecolor=PCOL[p],label=p) for p in ["Prophase","Prometaphase","Metaphase"]]+
   [Line2D([0],[0],color="#222",ls="-",lw=1.8,label="overall trend"),Line2D([0],[0],color="#888",ls="--",lw=1.5,label="per-phase trend")],fontsize=8)
fig.suptitle("Ablation edge-distance vs metaphase duration (color = ablation phase)",x=.01,ha="left",fontweight="bold")
plt.tight_layout(); plt.savefig(f"{OUT}/G3_edge_distance.png",bbox_inches="tight"); plt.close()
lib.record_plot("G3_edge_distance",["batch","n_sisterless","edge_um","duration_min","phase"],recE,{"type":"scatter 3-panel","color":"phase"},SCRIPT,"Ablation edge distance vs duration")

# ---------- 3. Origin-normalized ablation position (dot size = duration) ----------
fig,axes=plt.subplots(1,3,figsize=(13,4.6),sharex=True,sharey=True); recO=[]
from scipy.stats import spearmanr as _sprO
_allR=[]; _allD=[]   # (distance-from-origin, metaphase duration) pooled — does ablation POSITION affect mitotic time?
for ax,s in zip(axes,"123"):
    _pr=[]; _pd=[]
    for b,pos in preabl.items():
        if b not in ablout or mr.get(b,{}).get("# Sisterless KTs")!=s: continue
        d=md(b);
        if d is None: continue
        cx,cy=ablout[b].mean(0)
        for (x,y) in pos:
            dx=(x-cx)*ps(b); dy=(y-cy)*ps(b)
            ax.scatter(dx,dy,s=8+d*4,color=PCOL[phase(b)],alpha=.6,edgecolor="white",lw=.3); recO.append([b,s,round(dx,2),round(dy,2),round(d,2),phase(b)])
            _pr.append(float(np.hypot(dx,dy))); _pd.append(d)
    _allR+=_pr; _allD+=_pd
    if len(_pr)>=5:   # S38: does |distance from cell center (0,0)| correlate with metaphase duration? label goes BELOW the panel (off the points)
        _rho,_p=_sprO(_pr,_pd)
        ax.text(.5,-0.30,f"|distance from center (0,0)| vs metaphase duration\nSpearman ρ={_rho:.2f}, p={_p:.2g}  (N={len(_pr)})",
            transform=ax.transAxes,va="top",ha="center",fontsize=6.6,color="#111",bbox=dict(fc="white",ec="#bbb",alpha=.9))
    ax.axhline(0,color="#ccc",lw=.6); ax.axvline(0,color="#ccc",lw=.6); ax.set_title(f"{s}-Sisterless",fontsize=10); ax.set_xlabel("x from cell origin (µm)"); ax.set_aspect('equal')
if len(_allR)>=5:
    _rhoA,_pA=_sprO(_allR,_allD); _oa=f" — |position| vs duration overall: Spearman ρ={_rhoA:.2f}, p={_pA:.2g} (N={len(_allR)})"
    print(f"G3 origin-position: distance-from-origin vs metaphase duration Spearman rho={_rhoA:.3f} p={_pA:.3g} (N={len(_allR)})")
else: _oa=""
axes[0].set_ylabel("y from cell origin (µm)")
# legend: phase colors + dot-size = duration (per S38, in the legend not just the title)
axes[2].legend(handles=[Line2D([0],[0],marker='o',color='w',markerfacecolor=PCOL[p],label=p) for p in ["Prophase","Prometaphase","Metaphase"]]+
   [Line2D([0],[0],marker='o',color='w',markerfacecolor='#bbb',markersize=ms,label=lab) for ms,lab in [(4,"short duration"),(9,"long duration")]],
   fontsize=7,loc="upper right",title="color=phase · size=metaphase duration",title_fontsize=7)
fig.suptitle("Ablation position relative to cell origin (dot size = metaphase duration; color = phase)"+_oa,x=.01,ha="left",fontweight="bold")
plt.tight_layout(); plt.subplots_adjust(bottom=0.26)   # room for the correlation labels placed below each panel
plt.savefig(f"{OUT}/G3_origin_position.png",bbox_inches="tight"); plt.close()
lib.record_plot("G3_origin_position",["batch","n_sisterless","dx_um","dy_um","duration_min","phase"],recO,{"type":"scatter 3-panel","dot_size":"duration"},SCRIPT,"Origin-normalized ablation position")

# ---------- 4. Chromosome length vs duration (by phase) ----------
# de-duped length traces: chromo_measure_lines.csv (slide tool) SUPERSEDES chromo_lines.csv per batch so the
# new measurements are used and nothing is double-counted (user 2026-07-20).
_meas={}
_mp="/Volumes/4 MB/annotations/chromo_measure_lines.csv"
if os.path.isfile(_mp):
    for _r in csv.DictReader(open(_mp)):
        if lib.is_prophase_ablation(_r.get("batch","")): continue   # prophase excluded (no prophase group)
        _b=(_r.get('batch','') or '').strip()
        if _b and (_r.get('points','') or '').strip(): _meas.setdefault(_b,[]).append(_r.get('points',''))
_traces=[]   # (batch, points_json), de-duped
for _r in csv.DictReader(open("/Volumes/4 MB/annotations/chromo_lines.csv")):
    if lib.is_prophase_ablation(_r.get("batch","")): continue   # prophase excluded (no prophase group)
    _b=(_r.get('batch','') or '').strip()
    if _b and _b not in _meas: _traces.append((_b,_r.get('points','')))    # keep chromo_lines only where NOT superseded
for _b,_pl in _meas.items():
    for _p in _pl: _traces.append((_b,_p))

# ── ITEM 25 (user 2026-08-04): "there seems to be too many points on this plot — many at exactly the same
# metaphase duration but different chromosome lengths?" She is right, and the cause is the UNIT OF
# OBSERVATION. `chromo_lines` / `chromo_measure_lines` hold EVERY chromosome traced in a cell — one cell
# contributed 131 traces — and each trace was plotted against that cell's single metaphase duration, which
# is exactly the vertical stack of points she saw. 704 points came from only 85 cells.
# The unit this plot is actually about is the SISTERLESS (ablated) chromosome, which is what
# CHROMOSOME_MASTER records: one row per sisterless chromosome, 1 or 3 per cell.
# Restrict to those; the all-traces version remains available as G3_chromo_length_alltraces.
_SIS = {}
for _r in csv.DictReader(open("/Volumes/4 MB/annotations/CHROMOSOME_MASTER.csv")):
    if lib.is_prophase_ablation(_r.get("batch","")): continue   # prophase excluded (no prophase group)
    _b = (_r.get("batch", "") or "").strip()
    try: _L = float(_r.get("length_um") or "")
    except Exception: continue
    if _b: _SIS.setdefault(_b, []).append(_L)
_traces_all = list(_traces)
_traces = [(_b, None) for _b in _SIS for _ in _SIS[_b]]   # placeholder; lengths taken from _SIS below
_sis_iter = {b: iter(v) for b, v in _SIS.items()}
print(f"ITEM 25: chromosome-length plot restricted to SISTERLESS chromosomes — "
      f"{sum(len(v) for v in _SIS.values())} chromosomes across {len(_SIS)} cells "
      f"(was {len(_traces_all)} traces across {len({b for b,_ in _traces_all})} cells)")

fig,ax=plt.subplots(figsize=(7.4,5.2)); recC=[]; CX=[];CY=[]
SISMARK={"1":"o","2":"s","3":"^"}   # marker shape by sisterless count
for b,_pjson in _traces:
    if lib.is_mad1(b) or lib.plot_excluded(b) or b in _dbl: continue  # +drug/Exclude/REVIEW_EXCLUDE; double-chromosome excluded
    if _pjson is None:                      # ITEM 25: length comes straight from CHROMOSOME_MASTER
        try: L=next(_sis_iter[b])
        except StopIteration: continue
    else:
        try: P=np.array(json.loads(_pjson),float)
        except: continue
        if len(P)<2: continue
        L=np.sum(np.hypot(np.diff(P[:,0]),np.diff(P[:,1])))*ps(b)
    d=md(b)
    if d is None or L>30: continue
    mk=SISMARK.get(mr.get(b,{}).get("# Sisterless KTs",""),"o")
    ax.scatter(L,d,s=30,color=PCOL[phase(b)],alpha=.8,edgecolor="white",lw=.3,marker=mk); recC.append([b,round(L,3),round(d,3),phase(b)]); CX.append(L);CY.append(d)
# per-phase trend lines (slide 40 request); the pooled 'overall' line was removed 2026-08-05
for _ph in ["Prophase","Prometaphase","Metaphase"]:
    _xx=[r[1] for r in recC if r[3]==_ph]; _yy=[r[2] for r in recC if r[3]==_ph]
    if len(_xx)>=3:
        _m,_b=np.polyfit(_xx,_yy,1); _xr=np.linspace(min(_xx),max(_xx),20); ax.plot(_xr,_m*_xr+_b,"--",color=PCOL[_ph],lw=1.8)
# USER 2026-08-05: "remove the thick black line for an 'overall' trend line". It also had nothing to
# report: pooled Spearman rho=+0.034, p=0.684 (n=148 chromosomes), and per cell rho=+0.012, p=0.915
# (n=76 cells) — a line through no relationship. The whole `if len(CX)>=3:` block went with it.
ax.set_xlabel("chromosome length (µm)"); ax.set_ylabel("Metaphase duration (MM:SS)"); ax.yaxis.set_major_formatter(FuncFormatter(lambda v,_: lib.mmss(v) if v>=0 else ""))
# audio s40: N per group in the legend (per phase AND per sisterless group)
# D9 (2026-07-07): N is now listed per phase × sisterless in a dedicated box (see _pxs_text); the legend
# encodes color/marker meaning only (no lumped per-phase-only / per-sisterless-only counts).
ax.legend(handles=[Line2D([0],[0],marker='o',color='w',markerfacecolor=PCOL[p],label=p) for p in ["Prophase","Prometaphase","Metaphase"]]+
          [Line2D([0],[0],color="#888",ls="--",lw=1.8,label="per-phase trend")]+
          [Line2D([0],[0],marker=SISMARK[s],color='w',markerfacecolor='#888',markeredgecolor='#888',label=lib.lbl(f'{s}-Sister')) for s in "123"],fontsize=7,ncol=2)
ax.text(.99,.02,_pxs_text(recC),transform=ax.transAxes,ha="right",va="bottom",fontsize=6.4,color="#333",bbox=dict(fc="#f8f8f8",ec="#ccc",lw=.6,alpha=.92))
ax.set_title(f"SISTERLESS chromosome length vs metaphase duration (color = phase)  ·  "
             f"{len(recC)} chromosomes from {len({r[0] for r in recC})} cells",
             loc="left",fontweight="bold",fontsize=10)
ax.text(0.0,-0.155,
        "ITEM 25: one point per SISTERLESS (ablated) chromosome, from CHROMOSOME_MASTER. The previous version "
        "plotted every traced chromosome in the cell (one cell contributed 131),\nso each cell produced a tall "
        "vertical stack of points sharing its single metaphase duration.",
        transform=ax.transAxes,fontsize=6.8,color="#555",va="top",linespacing=1.5)
plt.tight_layout(); plt.savefig(f"{OUT}/G3_chromo_length.png",bbox_inches="tight"); plt.close()
lib.record_plot("G3_chromo_length",["batch","length_um","duration_min","phase"],recC,
  {"type":"scatter","color":"phase","unit":"one point per SISTERLESS chromosome (CHROMOSOME_MASTER)",
   "item25":"was one point per traced chromosome in the cell, which stacked points vertically at each cell's duration",
   "x_label":"Sisterless chromosome length (um)","y_label":"Metaphase duration (min)"},
  SCRIPT,"Sisterless chromosome length vs metaphase duration")

# ---- ITEM-1 companion: SAME points (color=phase), but trend lines per SISTERLESS group (1/2/3) instead of per phase ----
SISPAL={"1":lib.PALETTE["1-Sister"],"2":lib.PALETTE["2-Sister"],"3":lib.PALETTE["3-Sister"]}
figB,axB=plt.subplots(figsize=(7.4,5.2))
for r in recC:   # points identical to G3_chromo_length: color = phase, marker = sisterless group
    mk=SISMARK.get(mr.get(r[0],{}).get("# Sisterless KTs",""),"o")
    axB.scatter(r[1],r[2],s=30,color=PCOL[r[3]],alpha=.8,edgecolor="white",lw=.3,marker=mk)
for s in "123":   # trend line per sisterless group
    _xx=[r[1] for r in recC if mr.get(r[0],{}).get("# Sisterless KTs","")==s]
    _yy=[r[2] for r in recC if mr.get(r[0],{}).get("# Sisterless KTs","")==s]
    if len(_xx)>=3:
        _m,_b=np.polyfit(_xx,_yy,1); _xr=np.linspace(min(_xx),max(_xx),20); axB.plot(_xr,_m*_xr+_b,"-",color=SISPAL[s],lw=2.0)
if len(CX)>=3:
    _m,_b=np.polyfit(CX,CY,1); _xr=np.linspace(min(CX),max(CX),20); axB.plot(_xr,_m*_xr+_b,"--",color="#222",lw=1.6)
axB.set_xlabel("chromosome length (µm)"); axB.set_ylabel("Metaphase duration (MM:SS)"); axB.yaxis.set_major_formatter(FuncFormatter(lambda v,_: lib.mmss(v) if v>=0 else ""))
_nsisB={s:sum(1 for r in recC if mr.get(r[0],{}).get("# Sisterless KTs","")==s) for s in "123"}
axB.legend(handles=[Line2D([0],[0],marker='o',color='w',markerfacecolor=PCOL[p],label=p) for p in ["Prophase","Prometaphase","Metaphase"]]+
          [Line2D([0],[0],marker=SISMARK[s],color=SISPAL[s],markerfacecolor='#fff',markeredgecolor=SISPAL[s],lw=2.0,label=f"{lib.lbl(f'{s}-Sister')} trend (n={_nsisB[s]})") for s in "123"]+
          [Line2D([0],[0],color="#222",ls="--",lw=1.6,label="overall trend")],fontsize=7,ncol=2)
axB.text(.99,.02,_pxs_text(recC),transform=axB.transAxes,ha="right",va="bottom",fontsize=6.4,color="#333",bbox=dict(fc="#f8f8f8",ec="#ccc",lw=.6,alpha=.92))
axB.set_title("Chromosome length vs metaphase duration (color = phase; trend = sisterless group)",loc="left",fontweight="bold",fontsize=9.5)
plt.tight_layout(); plt.savefig(f"{OUT}/G3_chromo_length_bysister.png",bbox_inches="tight"); plt.close()
lib.record_plot("G3_chromo_length_bysister",["batch","length_um","duration_min","phase"],recC,{"type":"scatter","color":"phase","trend":"per-sisterless-group"},SCRIPT,"Chromosome length vs duration, trend per sisterless group")

# ---- per-batch AVERAGED chromosome length version (slide 40 request) ----
from collections import defaultdict as _dd3
_bl=_dd3(list); _bmeta={}
for b,L,d,ph in recC: _bl[b].append(L); _bmeta[b]=(d,ph)
figA,axA=plt.subplots(figsize=(8,5.4)); recCA=[]; AX=[];AY=[]
for b,Ls in _bl.items():
    d,ph=_bmeta[b]; La=float(np.mean(Ls))
    mk=SISMARK.get(mr.get(b,{}).get("# Sisterless KTs",""),"o")
    axA.scatter(La,d,s=34,color=PCOL[ph],alpha=.85,edgecolor="white",lw=.3,marker=mk); recCA.append([b,round(La,3),round(d,3),ph,len(Ls)]); AX.append(La);AY.append(d)
for _ph in ["Prophase","Prometaphase","Metaphase"]:
    _xx=[r[1] for r in recCA if r[3]==_ph]; _yy=[r[2] for r in recCA if r[3]==_ph]
    if len(_xx)>=3:
        _m,_b=np.polyfit(_xx,_yy,1); _xr=np.linspace(min(_xx),max(_xx),20); axA.plot(_xr,_m*_xr+_b,"--",color=PCOL[_ph],lw=1.8)
if len(AX)>=3:
    _m,_b=np.polyfit(AX,AY,1); _xr=np.linspace(min(AX),max(AX),20); axA.plot(_xr,_m*_xr+_b,"-",color="#222",lw=1.8)
axA.set_xlabel("mean chromosome length per cell (µm)"); axA.set_ylabel("Metaphase duration (MM:SS)"); axA.yaxis.set_major_formatter(FuncFormatter(lambda v,_: lib.mmss(v) if v>=0 else ""))
# audio s40: N per group in the legend (per-cell version -> N = number of CELLS per group)
_nphA={p:sum(1 for r in recCA if r[3]==p) for p in ["Prophase","Prometaphase","Metaphase"]}
_nsisA={s:sum(1 for r in recCA if mr.get(r[0],{}).get("# Sisterless KTs","")==s) for s in "123"}
axA.legend(handles=[Line2D([0],[0],marker='o',color='w',markerfacecolor=PCOL[p],label=p) for p in ["Prophase","Prometaphase","Metaphase"]]+
          [Line2D([0],[0],color="#888",ls="--",lw=1.8,label="per-phase trend")]+
          [Line2D([0],[0],marker=SISMARK[s],color='w',markerfacecolor='#888',markeredgecolor='#888',label=lib.lbl(f'{s}-Sister')) for s in "123"],fontsize=7,ncol=2)
axA.text(.99,.02,_pxs_text(recCA),transform=axA.transAxes,ha="right",va="bottom",fontsize=6.4,color="#333",bbox=dict(fc="#f8f8f8",ec="#ccc",lw=.6,alpha=.92))
axA.set_title("Chromosome length (per-cell average) vs metaphase duration",loc="left",fontweight="bold",fontsize=11)
plt.tight_layout(); plt.savefig(f"{OUT}/G3_chromo_length_percell.png",bbox_inches="tight"); plt.close()
lib.record_plot("G3_chromo_length_percell",["batch","mean_length_um","duration_min","phase","n_chromosomes"],recCA,{"type":"scatter per-cell-avg","color":"phase"},SCRIPT,"Per-cell mean chromosome length vs duration")

# ---- ITEM-1 companion (per-cell avg): SAME points (color=phase), trend lines per SISTERLESS group instead of per phase ----
figBA,axBA=plt.subplots(figsize=(8,5.4))
for r in recCA:   # points identical to G3_chromo_length_percell
    mk=SISMARK.get(mr.get(r[0],{}).get("# Sisterless KTs",""),"o")
    axBA.scatter(r[1],r[2],s=34,color=PCOL[r[3]],alpha=.85,edgecolor="white",lw=.3,marker=mk)
for s in "123":
    _xx=[r[1] for r in recCA if mr.get(r[0],{}).get("# Sisterless KTs","")==s]
    _yy=[r[2] for r in recCA if mr.get(r[0],{}).get("# Sisterless KTs","")==s]
    if len(_xx)>=3:
        _m,_b=np.polyfit(_xx,_yy,1); _xr=np.linspace(min(_xx),max(_xx),20); axBA.plot(_xr,_m*_xr+_b,"-",color=SISPAL[s],lw=2.0)
if len(AX)>=3:
    _m,_b=np.polyfit(AX,AY,1); _xr=np.linspace(min(AX),max(AX),20); axBA.plot(_xr,_m*_xr+_b,"--",color="#222",lw=1.6)
axBA.set_xlabel("mean chromosome length per cell (µm)"); axBA.set_ylabel("Metaphase duration (MM:SS)"); axBA.yaxis.set_major_formatter(FuncFormatter(lambda v,_: lib.mmss(v) if v>=0 else ""))
_nsisBA={s:sum(1 for r in recCA if mr.get(r[0],{}).get("# Sisterless KTs","")==s) for s in "123"}
axBA.legend(handles=[Line2D([0],[0],marker='o',color='w',markerfacecolor=PCOL[p],label=p) for p in ["Prophase","Prometaphase","Metaphase"]]+
          [Line2D([0],[0],marker=SISMARK[s],color=SISPAL[s],markerfacecolor='#fff',markeredgecolor=SISPAL[s],lw=2.0,label=f"{lib.lbl(f'{s}-Sister')} trend (n={_nsisBA[s]})") for s in "123"]+
          [Line2D([0],[0],color="#222",ls="--",lw=1.6,label="overall trend")],fontsize=7,ncol=2)
axBA.text(.99,.02,_pxs_text(recCA),transform=axBA.transAxes,ha="right",va="bottom",fontsize=6.4,color="#333",bbox=dict(fc="#f8f8f8",ec="#ccc",lw=.6,alpha=.92))
axBA.set_title("Chromosome length (per-cell average) vs metaphase duration (color = phase; trend = sisterless group)",loc="left",fontweight="bold",fontsize=9.5)
plt.tight_layout(); plt.savefig(f"{OUT}/G3_chromo_length_percell_bysister.png",bbox_inches="tight"); plt.close()
lib.record_plot("G3_chromo_length_percell_bysister",["batch","mean_length_um","duration_min","phase","n_chromosomes"],recCA,{"type":"scatter per-cell-avg","color":"phase","trend":"per-sisterless-group"},SCRIPT,"Per-cell mean chromosome length vs duration, trend per sisterless group")

# ---- D12 (2026-07-07): 1-SISTERLESS-ONLY versions of the two per-cell-average plots (per-phase trend AND
#      per-sisterless trend). Same points/axes/format, just restricted to the 1-sisterless-KT group. ----
_recCA1=[r for r in recCA if mr.get(r[0],{}).get("# Sisterless KTs","")=="1"]
# (i) per-PHASE trend, 1-sisterless only
fig1,ax1=plt.subplots(figsize=(8,5.4))
for r in _recCA1: ax1.scatter(r[1],r[2],s=34,color=PCOL[r[3]],alpha=.85,edgecolor="white",lw=.3,marker="o")
for _ph in ["Prophase","Prometaphase","Metaphase"]:
    _xx=[r[1] for r in _recCA1 if r[3]==_ph]; _yy=[r[2] for r in _recCA1 if r[3]==_ph]
    if len(_xx)>=3:
        _m,_b=np.polyfit(_xx,_yy,1); _xr=np.linspace(min(_xx),max(_xx),20); ax1.plot(_xr,_m*_xr+_b,"--",color=PCOL[_ph],lw=1.8)
_X1=[r[1] for r in _recCA1]; _Y1=[r[2] for r in _recCA1]
if len(_X1)>=3:
    _m,_b=np.polyfit(_X1,_Y1,1); _xr=np.linspace(min(_X1),max(_X1),20); ax1.plot(_xr,_m*_xr+_b,"-",color="#222",lw=1.8)
ax1.set_xlabel("mean chromosome length per cell (µm)"); ax1.set_ylabel("Metaphase duration (MM:SS)"); ax1.yaxis.set_major_formatter(FuncFormatter(lambda v,_: lib.mmss(v) if v>=0 else ""))
_np1={p:sum(1 for r in _recCA1 if r[3]==p) for p in ["Prophase","Prometaphase","Metaphase"]}
ax1.legend(handles=[Line2D([0],[0],marker='o',color='w',markerfacecolor=PCOL[p],label=f"{p} (n={_np1[p]})") for p in ["Prophase","Prometaphase","Metaphase"]]+
          [Line2D([0],[0],color="#222",ls="-",lw=1.8,label="overall trend"),Line2D([0],[0],color="#888",ls="--",lw=1.8,label="per-phase trend")],fontsize=7)
ax1.set_title("Chromosome length (per-cell average) vs metaphase duration — 1-sisterless only (per-phase trend)",loc="left",fontweight="bold",fontsize=9)
plt.tight_layout(); plt.savefig(f"{OUT}/G3_chromo_length_percell_1sis.png",bbox_inches="tight"); plt.close()
lib.record_plot("G3_chromo_length_percell_1sis",["batch","mean_length_um","duration_min","phase","n_chromosomes"],_recCA1,{"type":"scatter per-cell-avg","subset":"1-sisterless only","color":"phase","trend":"per-phase"},SCRIPT,"Per-cell mean chromosome length vs duration — 1-sisterless only, per-phase trend")
# (ii) per-SISTERLESS trend, 1-sisterless only (single group -> one trend line)
fig2,ax2=plt.subplots(figsize=(8,5.4))
for r in _recCA1: ax2.scatter(r[1],r[2],s=34,color=PCOL[r[3]],alpha=.85,edgecolor="white",lw=.3,marker="o")
if len(_X1)>=3:
    _m,_b=np.polyfit(_X1,_Y1,1); _xr=np.linspace(min(_X1),max(_X1),20); ax2.plot(_xr,_m*_xr+_b,"-",color=SISPAL["1"],lw=2.2)
ax2.set_xlabel("mean chromosome length per cell (µm)"); ax2.set_ylabel("Metaphase duration (MM:SS)"); ax2.yaxis.set_major_formatter(FuncFormatter(lambda v,_: lib.mmss(v) if v>=0 else ""))
ax2.legend(handles=[Line2D([0],[0],marker='o',color='w',markerfacecolor=PCOL[p],label=p) for p in ["Prophase","Prometaphase","Metaphase"]]+
          [Line2D([0],[0],color=SISPAL["1"],lw=2.2,label=f"1-sisterless trend (n={len(_recCA1)})")],fontsize=7)
ax2.set_title("Chromosome length (per-cell average) vs metaphase duration — 1-sisterless only (sisterless-group trend)",loc="left",fontweight="bold",fontsize=9)
plt.tight_layout(); plt.savefig(f"{OUT}/G3_chromo_length_percell_bysister_1sis.png",bbox_inches="tight"); plt.close()
lib.record_plot("G3_chromo_length_percell_bysister_1sis",["batch","mean_length_um","duration_min","phase","n_chromosomes"],_recCA1,{"type":"scatter per-cell-avg","subset":"1-sisterless only","color":"phase","trend":"sisterless-group (1-sis)"},SCRIPT,"Per-cell mean chromosome length vs duration — 1-sisterless only, sisterless-group trend")

# ---- PER-CELL congression complexity (slide 41 request): 3-sisterless cells have 3 KTs that congress to
#      different degrees; show the FRACTION of each cell's sisterless KTs that reached the plate, by group ----
rs=list(csv.reader(open("/Volumes/4 MB/annotations/SISTERLESS_PLATE_JOIN_TIMES.csv"))); jx={c:i for i,c in enumerate(rs[0])}
fig,ax=plt.subplots(figsize=(7,5)); recJ=[]; PALn={"1":lib.PALETTE["1-Sister"],"2":lib.PALETTE["2-Sister"],"3":lib.PALETTE["3-Sister"]}
percent_by_n=defaultdict(list)
for row in rs[1:]:
    if row[jx["exclude_this_data"]].strip() or lib.is_mad1(row[jx["batch"]].strip()) or lib.plot_excluded(row[jx["batch"]].strip()) or row[jx['batch']].strip() in _dbl: continue  # l429: double-chromosome excluded globally
    n=row[jx['n_sisterless']].strip()
    if n not in ("1","2","3"): continue
    nk=int(n); reached=0; seen=0
    for k in range(1,nk+1):
        v=row[jx[f'chromosome_{k}_plate_join']].strip()
        if not v or v.lower()=="n/a": continue
        seen+=1
        if v.lower()!="anaphase" and v not in ("0","0:00:00"): reached+=1   # reached the plate (not stuck polar / not lost to anaphase)
    if seen==0: continue
    frac=reached/seen; percent_by_n[n].append(frac); recJ.append([row[jx['batch']],n,seen,reached,round(frac,3)])
# D15 (2026-07-07): the fraction is DISCRETE (0, 1/3, 1/2, 2/3, 1) so the prior VIOLIN was misleading (implies
# a continuous density). Graceful non-violin form (prior feedback, line 480): a per-level DOT PLOT — at each
# achievable level, points fan horizontally so overlap = count — with NO violin. Fan width is NORMALIZED to a
# fixed half-width (0.26) regardless of count, so a group's dots can never spill into the neighbouring group's
# column (fixes the 1-sis/3-sis overlap). Faint guide lines mark the achievable levels.
present=[n for n in "123" if percent_by_n.get(n)]
xt=[]; xl=[]
_HALF=0.26   # max horizontal half-width of any group's dot fan (< 0.5 gap -> never overlaps neighbour)
for _lev in (0,1/3,1/2,2/3,1): ax.axhline(_lev,color="#eee",lw=.8,zorder=0)
from collections import Counter as _Ct
for i,n in enumerate(present):
    d=np.array(percent_by_n[n],float)
    xt.append(i); xl.append(f"{n}-Sisterless")
    cnt=_Ct(np.round(d,3))
    for yv,c in cnt.items():
        offs=np.zeros(1) if c==1 else (np.arange(c)-(c-1)/2)/((c-1)/2)*_HALF   # normalized fan, |offset|<=_HALF
        ax.scatter(i+offs,np.full(c,yv),s=34,color=PALn[n],alpha=.9,edgecolor="white",lw=.5,zorder=3)
    ax.hlines(np.mean(d),i-.30,i+.30,color=PALn[n],lw=2.6,zorder=4); ax.text(i,1.07,f"x̄ {np.mean(d):.2f}\nN={len(d)}",ha="center",va="bottom",fontsize=8)
ax.set_xticks(xt); ax.set_xticklabels(xl); ax.set_xlim(-0.6,len(present)-0.4)
ax.set_yticks([0,1/3,1/2,2/3,1]); ax.set_yticklabels(["0","1/3","1/2","2/3","1"])   # the achievable discrete levels
ax.set_ylabel("fraction of the cell's sisterless KTs that reached the plate"); ax.set_ylim(-0.08,1.22)
ax.set_title("Per-cell congression — fraction of sisterless KTs reaching the plate\n(captures the 1- vs 3-variable complexity per cell)",loc="left",fontweight="bold",fontsize=9.5)
plt.tight_layout(); plt.savefig(f"{OUT}/G3_congression_fraction.png",bbox_inches="tight"); plt.close()
lib.record_plot("G3_congression_fraction",["batch","n_sisterless","n_seen","n_reached_plate","fraction"],recJ,
  {"type":"per-cell fraction-congressed by group","note":"3-sis cells show intermediate fractions (3 independent KTs)"},SCRIPT,"Per-cell fraction of sisterless KTs reaching the plate")
lib.flush_review("/Volumes/4 MB/ablation_figures_20260625/_review/outlier_review.csv")
print(f"fate {sum(sum(fate[n].values()) for n in fate)} KTs, edge {len(recE)}, origin {len(recO)}, chromo {len(recC)}")
