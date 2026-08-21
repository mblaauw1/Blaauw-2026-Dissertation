"""Refined sister-KT analysis, single vs 3-sisterless, restricted to metaphase->anaphase window.
PAIRED KINETOCHORES ONLY (user 2026-08-10) - polar and lagging are excluded from this whole family.
ONE DATAPOINT PER SISTER PAIR: a cell with two annotated pairs contributes two separate points.
Outputs: per-pair oscillation amplitude (SD of plate-rel position) + mean metaphase k-k, with
Mann-Whitney stats; oscillation traces with per-group mean+/-SD trendline; model waves from
median amplitude+period; anaphase-separation timing as a separate readout.
"""
import sys, csv, re, json, collections; sys.path.insert(0,"/Volumes/4 MB/ablation_figures_20260625")
import numpy as np; from scipy.stats import mannwhitneyu
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
import lib
ANN="/Volumes/4 MB/annotations"; PX=0.062
data,_=lib.load_master(); mrow={r["Batch Name"]:r for r in data}
def tag(n,k): m=re.search(rf"{k}:([^;]*)",n or ""); return m.group(1) if m else ""
def absnum(b): return (mrow.get(b,{}).get("# Sisterless KTs","") or "").strip()
def hms2s(s):
    s=(s or "").strip(); neg=s.startswith("-"); s=s.lstrip("-")
    if not s: return None
    p=[float(x) for x in s.split(":")]; v=p[0]*3600+p[1]*60+p[2] if len(p)==3 else (p[0]*60+p[1] if len(p)==2 else p[0])
    return -v if neg else v
def cen(p): a=np.array(p,float); return np.array([a[:,0].mean(),a[:,1].mean()])

# SISTERS: the ONE authoritative file (basis=manual overrides proximity). GEOMETRY: the tracked
# objects (grp-aware track_id), so pieces of a KT are already combined. `pair:` tags no longer exist.
SIS={}
for r in csv.DictReader(open(f"{ANN}/KT_SISTERS_20260723.csv")):
    if r["sister_pair_id"]: SIS[r["track_id"]]=r["sister_pair_id"]
outs=collections.defaultdict(list)
# USER 2026-08-10: "for this subset of plots, dont include any measurements from polar or lagging
# kinetochores; just paired kinetochores." This REPLACES the earlier ITEM 8 request that added polar
# boxes to the amplitude/period panels — polar is now read nowhere in this file, and `lagging` is
# excluded by the same label gate. The counter below is printed so the exclusion stays visible.
_EXCLUDED=collections.Counter()
for r in csv.DictReader(open(f"{ANN}/KT_OUTLINE_TRACKS_20260723.csv")):
    if r["label"]!="paired":
        _EXCLUDED[r["label"]]+=1; continue        # polar / lagging / plate -> NOT in this family
    if not r["t_sec"] or not r["frame"].isdigit(): continue
    outs[r["batch"]].append(dict(frame=int(r["frame"]),t=float(r["t_sec"]),grp=r["track_id"],
              pair=SIS.get(r["track_id"],""),c=np.array([float(r["cx_px"]),float(r["cy_px"])])))
print("EXCLUDED (paired-only family):", dict(_EXCLUDED))
plates=collections.defaultdict(dict)
for r in csv.DictReader(open(f"{ANN}/meta_plates.csv")):
    if not r["points"] or not r["frame"].isdigit(): continue
    P=np.array(json.loads(r["points"]),float)
    if len(P)<2: continue
    ctr=P.mean(0); _,_,vt=np.linalg.svd(P-ctr); plates[r["batch"]][int(r["frame"])]=(ctr,vt[1])
def plate_at(b,f):
    d=plates.get(b)
    if not d: return None
    if f in d: return d[f]
    nf=min(d,key=lambda x:abs(x-f)); return d[nf] if abs(nf-f)<=6 else None

def _oriented_plates(cell, frames):
    """frame -> (ctr, normal), with the normal's SIGN made continuous across the WHOLE cell so that
    "towards pole A" keeps one sign for every kinetochore in it. Orientation used to be re-seeded inside
    each pair's own loop, so two pairs in one cell could silently end up on opposite conventions."""
    out={}; prev=None
    for f in sorted(frames):
        pl=plate_at(cell,f)
        if pl is None: continue
        ctr,normal=pl
        if prev is not None and np.dot(normal,prev)<0: normal=-normal
        prev=normal; out[f]=(ctr,normal)
    return out

def kt_series(cell, frs):
    """frs: frame -> grp -> [centroids].  Returns (kk_series, {grp: pos_series}) within the metaphase window.

    USER 2026-08-10: "for amplitude and period, this refers to oscilation back and forth, so you need to
    find this for each kinetochore, not pair of kinetochores."  So the plate-relative position is taken for
    EACH SISTER SEPARATELY -- one oscillation trace per KINETOCHORE, two per pair, four per triple-sisterless
    cell. It used to be taken from the pair MIDPOINT, which cancels exactly the back-and-forth motion the
    amplitude is meant to measure: when sisters breathe apart and together, the midpoint barely moves.
    k-k stays a PAIR quantity -- it is the distance between the two sisters and is undefined for one.
    """
    ms=hms2s(mrow.get(cell,{}).get("Metaphase Start (s)")); ana=hms2s(mrow.get(cell,{}).get("Anaphase Onset (s)"))
    if ms is None or ana is None: return [], {}, ms, ana
    ft={r["frame"]:r["t"] for r in outs[cell]}
    pl=_oriented_plates(cell, frs.keys())
    kk=[]; per=collections.defaultdict(list)
    for f in sorted(frs):
        t=ft.get(f)
        if t is None or not (ms<=t<=ana): continue          # METAPHASE WINDOW
        tm=(t-ms)/60.0
        gd={g:np.mean(v,axis=0) for g,v in frs[f].items()}  # pieces of ONE kinetochore combined
        if f in pl:
            ctr,normal=pl[f]
            for g,c in gd.items():
                per[g].append((tm, float(np.dot(c-ctr,normal))*PX))
        if len(gd)==2:
            c1,c2=list(gd.values())
            kk.append((tm, float(np.hypot(c1[0]-c2[0], c1[1]-c2[1])*PX)))
    return kk, dict(per), ms, ana

def est_period_min(T,POS):
    # zero-crossing based: period ~= 2*span/#crossings of the detrended signal. Robust for short series.
    ts=[(t,p) for t,p in zip(T,POS) if p is not None]
    if len(ts)<5: return None
    ts.sort(); t=np.array([x[0] for x in ts]); y=np.array([x[1] for x in ts])
    y=y-np.mean(y)
    if np.std(y)==0: return None
    s=np.sign(y); s[s==0]=1
    nc=int(np.sum(np.abs(np.diff(s))>0))
    if nc<1: return None
    span=t.max()-t.min()
    return 2.0*span/nc

# build the two UNITS this family measures:
#   pairs -> mean metaphase k-k        (one per sister pair)
#   kts   -> oscillation amp + period  (one per KINETOCHORE, user 2026-08-10)
# COHORT GATE (added 2026-08-10). This file used to select on "# Sisterless KTs" ALONE and never called
# lib.plot_excluded, so it silently kept prophase ablations, drug-treated cells, metaphase ablations,
# 4-sisterless, master Exclude=Yes, Mad1 and double-chromosome cells that every other cohort plot drops.
# The visible symptom: NF7 (G6_sister_oscillation_single_vs_triple) and the kk_osc_amplitude panel measure
# the SAME quantity from the SAME file and disagreed -- n=25/44 p=0.045 vs n=35/53 p=0.117 -- purely
# because NF7 applied this gate and this file did not. USER 2026-08-10 chose the standing rule (exclude).
_DBL = set(lib.double_chromosome_batches())
def _cohort_ok(b): return (not lib.plot_excluded(b)) and (not lib.is_mad1(b)) and b not in _DBL

pairs=[]; kts=[]; _odd=[]; _gated=collections.Counter()
for b,rs in outs.items():
    a=absnum(b); cohort="3" if a=="3" else ("single" if a=="1" else None)   # USER 2026-08-05: 3 only, never 2
    if cohort is None: continue
    if not _cohort_ok(b):
        _gated["prophase" if lib.is_prophase_ablation(b) else
               "metaphase" if lib.is_metaphase_ablation(b) else
               "drug" if lib.is_drug(b) else
               "Mad1" if lib.is_mad1(b) else
               "double-chromosome" if b in _DBL else "other (Exclude/4-sis/review)"] += 1
        continue
    byp=collections.defaultdict(lambda: collections.defaultdict(lambda: collections.defaultdict(list)))
    for r in rs:
        if r["pair"]: byp[r["pair"]][r["frame"]][r["grp"]].append(r["c"])
    for pid,frs in byp.items():
        kk, per, ms, ana = kt_series(b, frs)
        sp=str(pid).split("|")[-1]
        ntr=len({g for gd in frs.values() for g in gd})
        if ntr!=2: _odd.append((b,sp,ntr))   # a sister pair is 2 tracks; anything else is worth seeing
        if kk: pairs.append(dict(cohort=cohort,cell=b,pair=sp,kk=kk,n_kk=len(kk)))
        for g,ser in per.items():
            kts.append(dict(cohort=cohort,cell=b,pair=sp,kt=str(g).split("|")[-1],
                            id=f"{b}|{sp}|{g}",ser=ser,n_pos=len(ser)))
if _odd:
    print(f"NOTE: {len(_odd)} sister pair(s) not made of exactly 2 tracks: {_odd[:6]}")
if _gated:
    print(f"COHORT-GATED cells (standing rule, same test NF7 uses): {dict(_gated)}")

MIN_USABLE=4
# USER 2026-08-10: "some of the N's are lower than they should be." Every metric used to be gated on the
# INTERSECTION -- frames having both sisters AND a metaphase plate -- so a pair with plenty of k-k
# measurements was dropped from the k-k panel entirely just because that cell had no meta_plate annotation.
# Mean k-k does not involve the plate at all, so it is gated on k-k frames alone; only the plate-relative
# metrics need a plate. Each metric is now gated on exactly the frames IT uses, at its own unit.
for p in pairs:
    p["meankk"]=float(np.mean([v for _,v in p["kk"]])) if len(p["kk"])>=MIN_USABLE else None
for k in kts:
    if len(k["ser"])>=MIN_USABLE:
        T=[t for t,_ in k["ser"]]; POS=[v for _,v in k["ser"]]
        k["amp"]=float(np.std(POS)); k["period"]=est_period_min(T,POS)
    else:
        k["amp"]=k["period"]=None

# ITEM 8 (polar KT oscillation) REMOVED 2026-08-10 per user: this family is PAIRED KINETOCHORES
# ONLY. The polar analysis itself is not wrong and still lives in the polar/lagging figures --
# it is simply not part of these six plots.

def vals(co,key):
    """k-k is measured per PAIR; amplitude and period per KINETOCHORE. Each panel therefore counts its own
    unit, and the n= on each axis is the number of things actually measured."""
    src = pairs if key=="meankk" else kts
    return [x[key] for x in src if x["cohort"]==co and x.get(key) is not None]
print("=== metaphase-window metrics ===")
_ppc=collections.Counter(p["cell"] for p in pairs)
_kpc=collections.Counter(k["cell"] for k in kts)
print(f"  k-k          UNIT = sister PAIR      : {len(pairs)} pairs from {len(_ppc)} cells")
print(f"  amp / period UNIT = KINETOCHORE      : {len(kts)} kinetochores from {len(_kpc)} cells")
for co in ["single","3"]:
    npair=sum(1 for p in pairs if p["cohort"]==co); nkt=sum(1 for k in kts if k["cohort"]==co)
    print(f"    {co:6s}: {npair} pairs / {nkt} kinetochores | "
          f"meankk n={len(vals(co,'meankk'))} med={np.median(vals(co,'meankk')):.2f}um | "
          f"amp n={len(vals(co,'amp'))} med={np.median(vals(co,'amp')):.2f}um | "
          f"period n={len(vals(co,'period'))} med={np.median(vals(co,'period')) if vals(co,'period') else float('nan'):.1f}min")
_tri={c for c,_ in _kpc.items()}
print(f"  triple cells contributing 4 kinetochores: "
      f"{sum(1 for c,v in _kpc.items() if v==4 and absnum(c)=='3')} of {sum(1 for c in _kpc if absnum(c)=='3')}")
def mw(key):
    a,b=vals("single",key),vals("3",key)
    if len(a)>=3 and len(b)>=3:
        u,pv=mannwhitneyu(a,b,alternative="two-sided"); return pv
    return None
p_amp=mw("amp"); p_kk=mw("meankk")
print(f"\nMann-Whitney: amplitude p={p_amp}, mean k-k p={p_kk}")

# ---- FIGURE ----
# USER 2026-08-05: "break it apart into 6 separate figures instead of how it is right now as one figure
# holding 6". Each panel now gets its own figure; the shim below means none of the plotting body had to
# change (it still addresses axs[0,0] .. axs[1,2]), which keeps this edit from disturbing the analysis.
_PANELS = {}
_PANEL_NAME = {(0,0): "kk_osc_meankk", (0,1): "kk_osc_amplitude", (0,2): "kk_osc_period",
               (1,0): "kk_osc_about_plate", (1,1): "kk_osc_model", (1,2): "kk_osc_metaphase_duration"}
class _AxGrid:
    def __getitem__(self, k):
        if k not in _PANELS: _PANELS[k] = plt.subplots(figsize=(7.6, 5.6))
        return _PANELS[k][1]
axs = _AxGrid(); COL={"single":"#2a7fff","3":"#ff5a3c"}
def boxstrip(ax,key,title,ylab,pv):
    for i,co in enumerate(["single","3"]):
        v=vals(co,key); x=np.random.default_rng(i).normal(i,0.06,len(v))
        ax.scatter(x,v,c=COL[co],s=45,alpha=.75,edgecolor="k",lw=.4,zorder=3)
        if v: ax.boxplot(v,positions=[i],widths=.5,showfliers=False)
    ax.set_xticks([0,1]); ax.set_xticklabels([f"single\n(n={len(vals('single',key))})",f"3-sisterless\n(n={len(vals('3',key))})"])
    ax.set_ylabel(ylab); ax.set_title(title+(f"   MW p={pv:.3g}" if pv else "")); ax.grid(alpha=.3,axis="y")
boxstrip(axs[0,0],"meankk","Mean metaphase k-k (per sister pair)","k-k distance (um)",p_kk)
boxstrip(axs[0,1],"amp","Oscillation amplitude, per kinetochore (SD of plate-rel pos)","amplitude (um)",p_amp)
# period box
axp=axs[0,2]
for i,co in enumerate(["single","3"]):
    v=vals(co,"period"); x=np.random.default_rng(i+5).normal(i,0.06,len(v))
    axp.scatter(x,v,c=COL[co],s=45,alpha=.75,edgecolor="k",lw=.4,zorder=3)
    if v: axp.boxplot(v,positions=[i],widths=.5,showfliers=False)
axp.set_xticks([0,1]); axp.set_xticklabels([f"single\n(n={len(vals('single','period'))})",f"3-sisterless\n(n={len(vals('3','period'))})"])
axp.set_ylabel("period (min)"); axp.set_title("Oscillation period, per kinetochore  ·  paired KTs only"); axp.grid(alpha=.3,axis="y")
# oscillation traces + trendline (mean +/- SD envelope over time)
axt=axs[1,0]
_lab=[]
for co in ["single","3"]:
    allpts=[]
    for p in kts:                      # per-KINETOCHORE oscillation traces (user 2026-08-10)
        if p["cohort"]!=co: continue
        tr=list(p["ser"])
        if len(tr)>=4:
            tr.sort(); x,y=zip(*tr); axt.plot(x,y,c=COL[co],alpha=.25,lw=1); allpts+=tr
    if allpts:
        x=np.array([a[0] for a in allpts]); y=np.array([a[1] for a in allpts])
        bins=np.arange(0,np.ceil(x.max())+2,2); idx=np.digitize(x,bins); mx=[];md=[];sd=[]
        for bi in range(1,len(bins)):
            yy=y[idx==bi]
            if len(yy)>=3: mx.append(bins[bi-1]+1); md.append(yy.mean()); sd.append(yy.std())
        if mx:
            mx,md,sd=map(np.array,(mx,md,sd))
            # USER 2026-08-10: the TREND (this mean +/- SD envelope) stops at THIS cohort's median metaphase
            # duration. Past it most of the cohort has entered anaphase, so the envelope would be describing
            # only the longest-metaphase cells while looking like the cohort. Traces themselves still show.
            _cells={k["cell"] for k in kts if k["cohort"]==co}
            _cap=lib.trend_cap(_cells)
            if _cap is not None:
                _m=mx<=_cap; mx,md,sd=mx[_m],md[_m],sd[_m]
                lib.annotate_trend_cap(axt,_cap,color=COL[co],label=f"median metaphase ({co})")
            if len(mx):
                # 🔴 HER 2026-08-20, board-8 item 1: *"the trendlines show basically an average of all of all
                # the movement, not of the oscillations themselves, so the trendlines hover around 0 without
                # oscillatory pattern ... but I still want this plot to use the x-axis of time from metaphase
                # and y-axis of kinetochore position relative to plate."*
                #
                # THE FLAT LINE IS NOT A BUG, IT IS ARITHMETIC: kinetochores oscillate with independent
                # PHASE, so the mean of their positions cancels to ~0 no matter how many you add. No amount
                # of binning recovers the oscillation from a plain average. Keeping her axes, what those axes
                # CAN carry is:
                #   * the ENVELOPE -- the typical excursion either side of the plate at each time, drawn
                #     symmetrically (+/- RMS) so it reads as oscillation extent rather than as a mean; and
                #   * a MODEL WAVE at the group's median amplitude and period, which is the "typical
                #     oscillation" she is after, on the same axes.
                # The old mean is kept as a thin dotted line, labelled, so it is clear WHY it sits at zero
                # instead of looking like a result.
                _rms = np.array([np.sqrt(np.mean(y[idx == bi] ** 2))
                                 for bi in range(1, len(bins))
                                 if len(y[idx == bi]) >= 3])[:len(mx)]
                axt.plot(mx, _rms, c=COL[co], lw=2.6, zorder=6)
                axt.plot(mx, -_rms, c=COL[co], lw=2.6, zorder=6)
                axt.fill_between(mx, -_rms, _rms, color=COL[co], alpha=.12, zorder=1)
                axt.plot(mx, md, c=COL[co], lw=1.0, ls=":", alpha=.9, zorder=5)
                # model wave: median amplitude (an SD, so peak = A*sqrt(2)) and median period for this group
                _A = float(np.median(vals(co, "amp"))) if vals(co, "amp") else None
                _P = float(np.median(vals(co, "period"))) if vals(co, "period") else None
                if _A and _P and _P > 0:
                    _tw = np.linspace(0, mx.max(), 400)
                    axt.plot(_tw, _A*np.sqrt(2)*np.sin(2*np.pi*_tw/_P), c=COL[co], lw=1.4,
                             ls=(0, (5, 2)), alpha=.85, zorder=7)
                    _lab.append(f"{co}: envelope \u00b1RMS, model wave A={_A:.2f} \u00b5m, P={_P:.1f} min")
axt.axhline(0,ls="--",c="k",alpha=.5); axt.set_xlabel("time from metaphase (min)")
axt.set_ylabel("kinetochore pos rel. to plate (um)")
from matplotlib.lines import Line2D as _L
# ONE legend: the two cohorts AND what each line style means. Two legend() calls on the same axes silently
# replace one another -- the style key was being drawn and then thrown away.
_h=[_L([],[],c=COL['single'],lw=3),_L([],[],c=COL['3'],lw=3)]
_t=[f"single (n={len(vals('single','amp'))})",f"3-sisterless (n={len(vals('3','amp'))})"]
if _lab:
    _h += [_L([],[],c="#444",lw=2.6),
           _L([],[],c="#444",lw=1.4,ls=(0,(5,2))),
           _L([],[],c="#444",lw=1.0,ls=":")]
    _t += ["envelope: \u00b1RMS position (typical excursion)",
           "model wave (median amplitude & period)",
           "mean position \u2248 0 \u2014 phases cancel, not a result"]
axt.legend(_h,_t,fontsize=6.6,loc="upper right")
axt.set_title(f"Kinetochore oscillation about the plate (metaphase)   amplitude MW p={p_amp:.3g}"); axt.grid(alpha=.3)
# model waves (typical amplitude & period per group)
axm=axs[1,1]
tt=np.linspace(0,10,500)
for co in ["single","3"]:
    A=np.median(vals(co,"amp")) if vals(co,"amp") else np.nan
    Tp=np.median(vals(co,"period")) if vals(co,"period") else np.nan
    if np.isfinite(A) and np.isfinite(Tp):
        axm.plot(tt,A*np.sin(2*np.pi*tt/Tp),c=COL[co],lw=2.5,label=f"{co}: A={A:.2f}um, T={Tp:.1f}min")
axm.axhline(0,ls="--",c="k",alpha=.5); axm.set_xlabel("time (min)"); axm.set_ylabel("model pos (um)")
axm.set_title("Model oscillation (median amplitude & period; phase arbitrary)"); axm.legend(); axm.grid(alpha=.3)
# anaphase-separation timing (separate readout): metaphase duration = ana-ms per cohort
axa=axs[1,2]
durs={"single":[],"3":[]}
for b in outs:
    # BUG (fixed 2026-08-10): this panel alone binned 2-sisterless cells into the "3" group, while every
    # other panel excludes 2 entirely ("USER 2026-08-05: 3 only, never 2"). The duration panel was therefore
    # drawn from a different cohort than the five panels beside it.
    a=absnum(b); co="3" if a=="3" else ("single" if a=="1" else None)
    if co is None: continue
    ms=hms2s(mrow.get(b,{}).get("Metaphase Start (s)")); ana=hms2s(mrow.get(b,{}).get("Anaphase Onset (s)"))
    if ms is not None and ana is not None and any(p["cell"]==b for p in pairs): durs[co].append((ana-ms)/60.0)
for i,co in enumerate(["single","3"]):
    v=durs[co]; x=np.random.default_rng(i+9).normal(i,0.06,len(v))
    axa.scatter(x,v,c=COL[co],s=45,alpha=.75,edgecolor="k",lw=.4,zorder=3)
    if v: axa.boxplot(v,positions=[i],widths=.5,showfliers=False)
axa.set_xticks([0,1]); axa.set_xticklabels([f"single\n(n={len(durs['single'])})",f"3-sisterless\n(n={len(durs['3'])})"])
axa.set_ylabel("metaphase->anaphase (min)"); axa.set_title("Metaphase duration (anaphase timing readout)"); axa.grid(alpha=.3,axis="y")
# Register the plotted data (2026-07-29). These two overflow-board figures had NO recorded data CSV,
# so the deck's significance scan and family grouping had nothing to read and the overflow board
# carried 0 yellow highlights and 0 family blocks. record_plot also archives the generating code.
try:
    # TWO UNITS, never mixed in one row: k-k belongs to a sister PAIR, oscillation to a KINETOCHORE.
    # Keeping them as separate labelled rows means each panel's n is countable straight from this file
    # and nothing gets double-counted by summing a column.
    _hdr=["unit","cell","pair","kinetochore","cohort","meankk_um","amp_um","period_min","n_frames"]
    _rows =[["pair", p_["cell"], p_["pair"], "", p_["cohort"],
             (round(p_["meankk"],4) if p_.get("meankk") is not None else ""), "", "", p_.get("n_kk","")]
            for p_ in pairs]
    _rows+=[["kinetochore", k_["cell"], k_["pair"], k_["kt"], k_["cohort"], "",
             (round(k_["amp"],4)    if k_.get("amp")    is not None else ""),
             (round(k_["period"],3) if k_.get("period") is not None else ""), k_.get("n_pos","")]
            for k_ in kts]
    lib.record_plot("kk_osc_refined", _hdr, _rows,
                    {"type":"sister k-k oscillation, single vs 3-sisterless",
                     "window":"metaphase","amp_test":"Mann-Whitney on amplitude",
                     "kt_types":"PAIRED ONLY (polar and lagging excluded, user 2026-08-10)",
                     "unit":"rows are labelled pair (k-k) or kinetochore (amplitude/period); never per cell"},
                    __file__,
                    "Sister-KT oscillation amplitude and period about the metaphase plate, single vs "
                    "3-sisterless. PAIRED kinetochores only - no polar, no lagging. Oscillation amplitude and period "
                    "are measured PER KINETOCHORE (a triple-sisterless cell contributes four); mean k-k is "
                    "per sister pair (two per such cell). Pairs from "
                    "KT_SISTERS (manual where available), geometry from KT_OUTLINE_TRACKS - her MANUAL outlines.",
                    source=["/Volumes/4 MB/annotations/KT_SISTERS_20260723.csv",
                            "/Volumes/4 MB/annotations/KT_OUTLINE_TRACKS_20260723.csv"],
                    key_column="cell")
except Exception as _e:
    print("record_plot(kk_osc_refined) skipped: %s" % _e)
_PANEL_CAPTION = {
    "kk_osc_amplitude": "Oscillation amplitude per kinetochore about the metaphase plate, single vs 3-sisterless (paired kinetochores only).",
    "kk_osc_period": "Oscillation period per kinetochore, single vs 3-sisterless (paired kinetochores only).",
    "kk_osc_meankk": "Mean metaphase k-k distance per sister pair, single vs 3-sisterless.",
    "kk_osc_about_plate": "Kinetochore position about the metaphase plate over time, per group.",
    "kk_osc_model": "Model waves built from each group's median oscillation amplitude and period.",
    "kk_osc_metaphase_duration": "Metaphase duration of the cells contributing to the oscillation analysis.",
}
import os as _os
_RELINK="/Volumes/4 MB/ablation_figures_20260625/_ai_relink/pdf"; _os.makedirs(_RELINK,exist_ok=True)
_OUTDIR="/Volumes/4 MB/ablation_figures_20260625/group6_tracks"; _os.makedirs(_OUTDIR,exist_ok=True)
# USER 2026-08-20 (artboard 8, item 8): "the y-axis scales on these two plots (copied below) should be the
# same so when theyre placed right next to eachother the information is easily understandable."
# `kk_osc_about_plate` (the measured traces) and `kk_osc_model` (the model waves built from those traces'
# median amplitude and period) sit side by side on artboard 8 and plot the SAME quantity -- kinetochore
# position about the plate, in um. Different autoscaled ranges made the model waves look larger or smaller
# than the data they summarise. One shared symmetric range fixes the comparison; it is taken as the union of
# what the two panels actually need, so nothing is clipped.
_PAIR = [(1, 0), (1, 1)]
_lims = [_PANELS[k][1].get_ylim() for k in _PAIR if k in _PANELS]
if len(_lims) == 2:
    _m = max(max(abs(a), abs(b)) for a, b in _lims)
    for k in _PAIR:
        _PANELS[k][1].set_ylim(-_m, _m)
    print(f"about_plate / model share y = +/-{_m:.2f} um (was "
          + " and ".join(f"[{a:.2f},{b:.2f}]" for a, b in _lims) + ")")

for _k,(_f,_a) in sorted(_PANELS.items()):
    _nm=_PANEL_NAME.get(_k, f"kk_osc_panel_{_k[0]}{_k[1]}")
    _f.tight_layout()
    _f.savefig(_os.path.join(_OUTDIR,_nm+".png"), dpi=150, bbox_inches="tight")
    _f.savefig(_os.path.join(_RELINK,_nm+".pdf"), bbox_inches="tight")
    plt.close(_f)
    # 2026-08-18: these six panels were PLACED on the decks but never registered, so they had no
    # provenance and the legend builder had nothing to say about them. They are views of the parent's
    # dataset, so they register as PANELS rather than writing a second copy of the data.
    try:
        lib.register_panel(_nm, "kk_osc_refined",
                           caption=_PANEL_CAPTION.get(_nm, "Panel of the sister-KT oscillation analysis "
                                                           "(paired kinetochores only, metaphase window)."),
                           settings={"panel_metric": _nm.replace("kk_osc_", "")}, script=__file__)
    except Exception as _e2:
        print(f"register_panel({_nm}) skipped: {_e2}")
    print(f"wrote {_nm}.png (+ deck-linked PDF)")
print(f"{len(_PANELS)} separate figures written to {_OUTDIR}")
