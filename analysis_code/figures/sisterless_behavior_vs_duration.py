"""Sisterless-KT behavior vs metaphase/mitotic duration — MULTIPLE visualizations (USER 2026-07-17).
Cohort: cdc20 on-target, non-drug, non-collagen, non-mad1, 1/2/3-sisterless, non-excluded.
Per sisterless KT behavior = congress-to-plate@time | at-plate-from-start(t=0) | polar-until-anaphase(never joins).
Sources: (1) SISTERLESS_PLATE_JOIN_TIMES.csv structured per-KT (reliable); (2) master Notes prose (approximate,
flagged). Derived per cell: n_polar, n_congress, n_atplate, latest resolution time, metaphase/mitotic duration.
Builds several plots to look for a pattern between behavior and metaphase length."""
import sys; sys.path.insert(0,"/Volumes/4 MB/ablation_figures_20260625")
import csv, re, os, numpy as np, matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import lib
try: lib.apply_style()
except Exception: pass
def tmin(s):
    s=(s or "").strip()
    if not s: return None
    p=s.split(":")
    try: return (int(p[0])*3600+int(p[1])*60+int(float(p[2])))/60.0 if len(p)==3 else int(p[0])+int(p[1])/60.0
    except: return None
data,_=lib.load_master_plots(); mr={r["Batch Name"]:r for r in data}
def ok(r):
    b=r["Batch Name"]
    return (r.get("# Sisterless KTs","") in ("1","2","3") and "on-target" in (r.get("On-Target / Off-Target","").lower())
            and not lib.is_drug(b) and "collagen" not in b.lower() and not lib.is_mad1(b)
            and r.get("Exclude") not in ("Yes","yes") and not lib.excluded(b)
            # 2026-08-03 (item 3, "n should be higher / all cells specified"): this builder never applied the
            # standing rule "metaphase ablations excluded by default; filter from every master-derived set
            # unless asked" (MEMORY feedback_metaphase_ablations_excluded_default) -- lib.assign_cohorts() and
            # the G1 duration violin both apply it, this file did not. That let 11 metaphase-ablation batches
            # sit in this builder's cohort uncounted: 7 were already "fully described" and silently plotted
            # alongside prometaphase cells, and 4 were under-described but invisible to the review list because
            # the review gate only checks membership in the (correctly-filtered) G1 violin batch set (vbatch).
            # Removing them here brings this builder in line with every other master-derived plot.
            and not lib.is_metaphase_ablation(b))
_DBL=lib.double_chromosome_batches()   # both KTs on one chromosome -> no sisterless; never in this analysis
sel=[r for r in data if ok(r) and r["Batch Name"] not in _DBL]
pj={r["batch"].strip():r for r in csv.DictReader(open("/Volumes/4 MB/annotations/SISTERLESS_PLATE_JOIN_TIMES.csv"))
    if (r.get("exclude_this_data") or "").lower()!="yes"}
# batches in the MAIN duration violin — only these need behavior resolved (USER 2026-07-18)
vbatch=set()
try:
    for _r in csv.DictReader(open("/Volumes/4 MB/ablation_plots/data/G1_violin2_sisterless_1234.csv")):
        if lib.is_prophase_ablation(_r.get("batch","")): continue   # prophase excluded (no prophase group)
        _b=(_r.get("batch") or _r.get("Batch Name") or "").strip()
        if _b: vbatch.add(_b)
except Exception: pass

def parse_structured(r):
    beh=[]  # (type, time_min)
    for k in ("chromosome_1_plate_join","chromosome_2_plate_join","chromosome_3_plate_join"):
        v=(r.get(k) or "").strip().lower()
        if not v or v=="n/a": continue
        if v=="anaphase": beh.append(("polar",None))
        elif v=="0" or v=="0:00:00": beh.append(("atplate",0.0))
        elif re.match(r"\d+:\d+",v): beh.append(("congress",tmin(v)))
    return beh
def parse_prose(text,n):
    """Reconstruct each sisterless KT's disposition from the review prose. Logic: count congression events
    (to-plate, with times) + at-plate events ('never seen'/'at plate whole time'); the REMAINDER (of the n
    sisterless KTs) is polar-until-anaphase IF the text mentions polar/pole. Returns list of (type,time)."""
    t=" "+text.lower()+" "
    times=[]
    for m in re.finditer(r'(?:move[sd]?|moving|congress\w*|converg\w*|join\w*|disappear\w*|align\w*|reach\w*)[^.|]{0,45}?plate[^.|]{0,25}?(\d{1,2}:\d{2}(?::\d{2})?)',t): times.append(tmin(m.group(1)))
    for m in re.finditer(r'converg\w*[^.|]{0,15}?(?:at\s*)?(\d{1,2}:\d{2}(?::\d{2})?)',t): times.append(tmin(m.group(1)))
    for m in re.finditer(r'plate[^.|]{0,8}?at\s*(\d{1,2}:\d{2}(?::\d{2})?)',t): times.append(tmin(m.group(1)))
    # continuation times ("then another at TIME", "second/third ... at TIME") within a plate-congression comment
    if re.search(r'plate|congress|converg',t):
        for m in re.finditer(r'(?:another|second|third|next|then|first)[^.|]{0,22}?(?:at\s*)?(\d{1,2}:\d{2}(?::\d{2})?)',t):
            pre=t[max(0,m.start()-22):m.start()].lower()
            if re.search(r'anaphase|metaphase|nebd|stuck|change|onset|congress\w*\s*$',pre): continue  # skip non-congression times
            times.append(tmin(m.group(1)))
    times=sorted(set(round(x,2) for x in times if x is not None))
    no_time=len(re.findall(r'(?:congress\w*\s+to|movement\s+from\s+pole\s+to|move[sd]?\s+(?:in)?to)\s+(?:the\s*)?(?:metaphase\s*)?plate',t))
    n_cong=len(times)+(1 if (no_time>0 and len(times)==0) else 0)
    n_atpl=len(re.findall(r'never seen|at (?:the )?(?:metaphase )?plate (?:the )?whole time|at (?:the )?(?:metaphase )?plate until anaphase|at (?:the )?(?:metaphase )?plate from (?:the )?(?:start|beginning)',t))
    has_polar=bool(re.search(r'polar|at (?:the )?pole',t))
    n_cong=min(n_cong,n); n_atpl=min(n_atpl,n-n_cong)
    n_polar=max(0,n-n_cong-n_atpl) if has_polar else 0
    beh=[("congress",x) for x in times[:n_cong]]+[("congress",None)]*(n_cong-len(times[:n_cong]))
    beh+=[("atplate",0.0)]*n_atpl+[("polar",None)]*n_polar
    return beh
# ---- RECOVERY PASS (2026-08-03, item 3) --------------------------------------------------------------
# Per-batch behavior for the 9 cells listed in 4_TABLES_AND_REPORTS/SISTERLESS_BEHAVIOR_NEEDS_REVIEW_20260718.csv is ABSENT from
# every source this builder previously read (master Notes/annotation_notes/Polar Comments prose, and
# SISTERLESS_PLATE_JOIN_TIMES.csv structured rows -- 2 of the 9 have a row there, id 44 and 51, but every
# time/join field on both is blank). It IS recorded, for all 9, in annotations/CHROMO_LENGTH_BEHAVIOR_PAIRING.csv
# (the 8781 pairing-tool output) -- a source this builder never read at all. Recovered BY HAND below, preferring
# each row's chrN_movement column (a later, per-chromosome structured re-annotation pass -- see the
# "[2026-07-22 claude] ... was: ..." edit trail on single_ablation_13's own pairing_notes) over the older
# free-text pairing_notes when both exist. Every entry cites its exact source text so this is auditable/
# correctable rather than inferred, and where _scratch/primary_geometry_chrom.csv already had an independent
# dist-to-plate trajectory for the same kinetochore (computed from kt_points.csv "sisterless" marks, unrelated
# pipeline) it was cross-checked: e.g. triple_ablation_18's three KTs never approach the plate (min dist
# 5.6-9.0 um across the whole tracked window), consistent with "polar until anaphase" x3 below. Times are
# absolute movie-clock minutes:seconds, matching Metaphase Start (s)/Anaphase Onset (s) as tmin() parses them
# elsewhere in this file, and every recovered time below DOES fall inside that batch's [meta,ana] window --
# a sanity check the numbers pass, not a guarantee they are error-free.
RECOVERED_BEHAVIOR = {
    "20250711 double ablation_21": [("atplate",0.0),("polar",None),("polar",None)],
        # pairing_notes: "1 at plate until anaphase onset; 2 and 3 polar until anaphase onset"
    "20250904 triple_ablation_8": [("congress",tmin("16:46")),("congress",tmin("27:06")),("congress",tmin("33:26"))],
        # pairing_notes: "1 moves to metaphase plate at 16:46. 2 moves metaphase plate at 27:06. 3 congresses at 33:26"
    "20260416 single ablation_13": [("atplate",0.0),("congress",tmin("16:24"))],
        # chr1_movement: "at plate from metaphase onset" | chr2_movement: "congresses to plate at 16:24"
        # (this batch's Notes also read "consider excluding" over acquisition health, not over missing behavior
        # -- master Exclude is blank, so the cohort filter above keeps it; her call to drop it stands if she wants)
    "20260420 ptk2 eyfp cdc20 1 ablation_43": [("polar",None)],
        # chr1_movement: "polar until anaphase"
    "20260108 two_sisterless_kinetochores_4": [("atplate",0.0),("atplate",0.0)],
        # chr1_movement / chr2_movement: "at plate from beginning" (both)
        # (annotation_notes flags "uncertain on chromosome lines. change # of chromosomes" -- the pairing file
        # only carries chr1/chr2, matching master "# Sisterless KTs"=2, so used as-is; her call if the count itself is wrong)
    "20251006 triple_ablation_18": [("polar",None),("polar",None),("polar",None)],
        # chr1_movement/chr2_movement/chr3_movement: "polar until anaphase" (all three)
    "20251006 triple_ablation_21": [("congress",tmin("30:28")),("polar",None),("polar",None)],
        # chr1_movement: "congresses at 30:28" | chr2_movement/chr3_movement: "polar until anaphase"
        # CONTRADICTS this same batch's own pairing_notes ("1 congresses...23:57. 2 at 42:28, 3 at 00:43:18",
        # implying all three eventually congress). chrN_movement is preferred as the later per-KT pass (see
        # header note) but the conflict is real and NOT resolved by this script -- flagged in the printed
        # review-of-recoveries list below for her to confirm.
    "20260113 snigle_ablation_visualize chromosome with sisterless kinetochore_14": [("congress",tmin("40:46")),("atplate",0.0)],
        # chr1_movement: "congresses at 40:46" (pairing_notes says 00:42:06 -- chrN_movement preferred, same conflict-preference rule)
        # chr2_movement: "at plate from metaphase onset"
    "20251028 triple_ablation_9": [("congress",tmin("26:25")),("congress",tmin("29:45")),("congress",tmin("31:25"))],
        # chr1_movement/chr2_movement/chr3_movement: "congresses at 26:25" / "29:45" / "31:25"
}
RECOVERED_CONFLICTS = {   # batches above where chrN_movement disagreed with pairing_notes -- surfaced on the figure
    "20251006 triple_ablation_21": "chrN_movement says KT1 congresses/KT2+3 stay polar; pairing_notes implies all 3 congress",
}
rows=[]; review=[]; recovered_used=[]
def _reason(txt):
    tl=txt.lower()
    if not txt.strip(" |"): return "no behavior description in Notes"
    if re.search(r'did not go past anaphase|not continued long enough|not imaged|anaphase unclear|imaging did not|did not go past',tl): return "imaging didn't capture the outcome (anaphase not reached/unclear)"
    if re.search(r'unhealthy|consider exclud|potentially exclud|uncertain|extremely rounded|extremly rounded',tl): return "reviewer flagged unhealthy/uncertain"
    if "samesweep" in tl: return "SAMESWEEP-contaminated batch (behavior not scorable as-is)"
    return "behavior not stated in the comment — please describe"
for r in sel:
    b=r["Batch Name"]; n=int(r["# Sisterless KTs"])
    txt=(r.get("Notes","")+" || "+r.get("annotation_notes","")+" || "+r.get("Polar Comments",""))
    if "both kinetochores on one chromosome" in txt.lower() or "[plate-join n/a" in txt.lower(): continue  # no sisterless — user: doesn't matter
    meta=tmin(r.get("Metaphase Start (s)","")); ana=tmin(r.get("Anaphase Onset (s)",""))
    mdur,ok2=lib.mitotic_duration_min(r); mdur=mdur if ok2 else None
    metadur=(ana-meta) if (meta is not None and ana is not None) else None
    if b in pj: beh=parse_structured(pj[b]); src="structured"
    else: beh=[]; src=None
    if len(beh)!=n and b in RECOVERED_BEHAVIOR and len(RECOVERED_BEHAVIOR[b])==n:
        beh=RECOVERED_BEHAVIOR[b]; src="pairing_recovered"; recovered_used.append(b)
    elif src is None:
        beh=parse_prose(txt,n); src="prose"
    beh=beh[:n]; full=(len(beh)==n)
    if not full and b in vbatch: review.append((b,n,len(beh),_reason(txt),txt.strip(" |")[:150]))
    n_polar=sum(1 for x in beh if x[0]=="polar"); n_cong=sum(1 for x in beh if x[0]=="congress"); n_atpl=sum(1 for x in beh if x[0]=="atplate")
    ctimes=[x[1] for x in beh if x[0]=="congress" and x[1] is not None]
    latest=max(ctimes) if ctimes else None
    all_resolved=(n_polar==0 and full)
    rows.append(dict(batch=b,group=n,src=src,n_polar=n_polar,n_cong=n_cong,n_atpl=n_atpl,
                     latest=latest,all_resolved=all_resolved,meta=meta,ana=ana,mdur=mdur,metadur=metadur,beh=beh,n_desc=len(beh),full=full))
nfull=sum(1 for x in rows if x['full'])
print(f"cohort {len(rows)} | structured {sum(1 for x in rows if x['src']=='structured')} | prose {sum(1 for x in rows if x['src']=='prose')} | pairing_recovered {sum(1 for x in rows if x['src']=='pairing_recovered')}")
print(f"FULLY described (all sisterless KTs): {nfull} | under-described (review): {len(review)}")
print(f"2026-08-03 recovery: {len(recovered_used)}/{len(RECOVERED_BEHAVIOR)} of the 9 previously-missing batches recovered from CHROMO_LENGTH_BEHAVIOR_PAIRING.csv: {sorted(recovered_used)}")
if RECOVERED_CONFLICTS: print(f"UNRESOLVED CONFLICTS in recovered behavior (her call): {RECOVERED_CONFLICTS}")
import csv as _csv
# NOTE (2026-08-03): this file is REGENERATED each run -- it is the live "still needs her input" list, not a
# permanent record. If it is empty, every cohort member (after the metaphase-ablation exclusion fix above) has
# a resolvable behavior; that is the expected/target state, not a bug.
with open("/Volumes/4 MB/4_TABLES_AND_REPORTS/SISTERLESS_BEHAVIOR_NEEDS_REVIEW_20260718.csv","w",newline="") as f:
    w=_csv.writer(f); w.writerow(["batch","n_sisterless","n_KTs_parsed","reason","comment_excerpt"])
    for x in review: w.writerow(x)
print(f"review list ({len(review)} rows) -> 4_TABLES_AND_REPORTS/SISTERLESS_BEHAVIOR_NEEDS_REVIEW_20260718.csv")

OUT="/Volumes/4 MB/ablation_figures_20260625/custom_collagen_vs_triple"; os.makedirs(os.path.join(OUT,"illustrator"),exist_ok=True)
GC={1:"#2e9e3f",2:"#d68f00",3:"#8e44ad"}
MSRC={"structured":dict(marker="o"),"prose":dict(marker="^"),"pairing_recovered":dict(marker="D"),
      # set by the prose->PREABL replacement below; structured per-chromosome data, so it marks as structured
      "preabl_structured":dict(marker="o")}
def yval(r): return r["metadur"] if r["metadur"] is not None else r["mdur"]
YL="Metaphase duration (min)"
def save(fig,nm,caption,cols,prov):
    fig.savefig(os.path.join(OUT,nm+".png"),dpi=150); fig.savefig(os.path.join(OUT,"illustrator",nm+".svg")); plt.close(fig)
    lib.record_plot(nm,cols,prov,{"cohort":"cdc20 on-target non-drug non-collagen 1/2/3-sisterless",
        "behavior_source":"SISTERLESS_PLATE_JOIN_TIMES.csv (structured, o) + master Notes prose (approx, ^)"},
        __file__,caption,source=["/Volumes/4 MB/ABLATION_MASTER.csv","/Volumes/4 MB/annotations/SISTERLESS_PLATE_JOIN_TIMES.csv"])
    print("wrote",nm)

# V1: # polar (never-joined) sisterless KTs vs metaphase duration (strip, by group)
fig,ax=plt.subplots(figsize=(7.6,5.4))
for r in rows:
    y=yval(r)
    if y is None or not r["full"]: continue
    x=r["n_polar"]+ (np.random.default_rng(abs(hash(r["batch"]))%2**32).uniform(-0.16,0.16))
    ax.scatter(x,y,color=GC[r["group"]],alpha=.8,s=42,edgecolor="w",lw=.5,**MSRC[r["src"]],zorder=3)
for g in (1,2,3): ax.scatter([],[],color=GC[g],label=f"{g}-sisterless")
ax.scatter([],[],color="gray",marker="o",label="structured data"); ax.scatter([],[],color="gray",marker="^",label="prose (approx)")
ax.scatter([],[],color="gray",marker="D",label="recovered from pairing tool (2026-08-03)")
ax.set_xlabel("# sisterless KTs that stayed polar (never joined plate)"); ax.set_ylabel(YL)
ax.set_title("Metaphase duration vs number of never-joining (polar) sisterless KTs"); ax.set_xticks([0,1,2,3]); ax.legend(fontsize=8)
save(fig,"G4_sisbehav_npolar_vs_duration","Metaphase duration vs # polar (never-joined) sisterless KTs",
     ["batch","group","n_polar","metaphase_duration_min","source"],
     [[r["batch"],r["group"],r["n_polar"],round(yval(r),2) if yval(r) else "",r["src"]] for r in rows if yval(r) and r["full"]])

# V2: latest congression time vs metaphase duration (cells where all KTs resolved); polar cells shown separately
fig,ax=plt.subplots(figsize=(7.8,5.4))
resolved=[r for r in rows if r["all_resolved"] and r["latest"] is not None and yval(r) is not None]
for r in resolved:
    ax.scatter(r["latest"],yval(r),color=GC[r["group"]],alpha=.85,s=46,edgecolor="w",lw=.5,**MSRC[r["src"]],zorder=3)
if len(resolved)>=3:
    xs=np.array([r["latest"] for r in resolved]); ys=np.array([yval(r) for r in resolved])
    m,b=np.polyfit(xs,ys,1); xr=np.array([xs.min(),xs.max()]); ax.plot(xr,m*xr+b,"k--",lw=1.4,alpha=.7)
    from scipy import stats; rho,p=stats.spearmanr(xs,ys)
    ax.text(.03,.97,f"all-resolved cells: N={len(resolved)}\nSpearman rho={rho:.2f}, p={p:.2g}",transform=ax.transAxes,va="top",fontsize=9,bbox=dict(boxstyle="round",fc="white",ec=".6"))
for g in (1,2,3): ax.scatter([],[],color=GC[g],label=f"{g}-sisterless")
ax.set_xlabel("Time of LAST sisterless-KT congression to plate (min)"); ax.set_ylabel(YL)
ax.set_title("Does the last sisterless KT to congress set metaphase length?\n(cells where all sisterless KTs eventually joined the plate)"); ax.legend(fontsize=8)
save(fig,"G4_sisbehav_lastcongress_vs_duration","Last sisterless-KT congression time vs metaphase duration",
     ["batch","group","latest_congress_min","metaphase_duration_min","source"],
     [[r["batch"],r["group"],round(r["latest"],2),round(yval(r),2),r["src"]] for r in resolved])

# ── POLAR KINETOCHORES PRESENT AT ANAPHASE ONSET, measured from her outlines ──────────────────────
# USER 2026-08-10: "we did some calculation looking at how many polar kinetochores a cell typically goes
# into anaphase with, and for both triple and single sisterless groups, it was close, like between .5-.7 ...
# Recalculate this ... and then I want to figure out some way to visualize this on the per-cell sisterless-kt
# resolution timeline (sorted by metaphase duration)."
#
# 🔴 THE OUTLINE-DERIVED NUMBERS BELOW ARE NOT THE ANSWER — see the correction at the anaphase circles
# further down (2026-08-10). This block reads KT_OUTLINE_TRACKS (a distinct polar track carrying an outline
# in the window), which covers only 36 of the 66 cohort cells and can never report more than one polar KT
# per cell. It gives single 0.65 / triple 0.45, and it was on that basis that I told her the distribution is
# strictly {0,1} and no cell enters anaphase with more than one polar kinetochore. That was an artifact of
# outline coverage, not biology. HER behaviour determinations cover all 66 cells and DO record 2 and 3 polar
# KTs; the authoritative per-cell count is `n_pol`, drawn from r["beh"], not from _POLAR_AT_ANA.
# _POLAR_AT_ANA is kept only as an INDEPENDENT CROSS-CHECK of the subset it covers.
#
# Authoritative (behaviour-derived, capped at each cell's # Sisterless KTs, 2026-08-14 re-derivation):
#   1-sisterless 0.67 (n=36, {0:12, 1:24})   2-sisterless 1.00 (n=8)   3-sisterless 0.82 (n=22, {0:11,1:6,2:3,3:2})
#   single vs triple Mann-Whitney p=0.92 -- indistinguishable, so the "single and triple are close" reading
#   survives the source correction even though the ceiling of 1 KT/cell did not: triples DO enter anaphase
#   with 2 or 3 polar KTs (5 of 22 cells), singles never with more than 1.
#   Adding the 4 collagen triples (a substrate, not a drug) moves triple to 1.00 (n=26); p=0.40, same reading.
_POLAR_AT_ANA = {}
try:
    import csv as _c3, collections as _cc3
    _pt = _cc3.defaultdict(lambda: _cc3.defaultdict(list))
    for _r in _c3.DictReader(open("/Volumes/4 MB/annotations/KT_OUTLINE_TRACKS_20260723.csv")):
        if _r.get("label") != "polar": continue
        try: _pt[(_r.get("batch") or "").strip()][_r["track_id"]].append(float(_r["t_sec"]))
        except Exception: pass
    _W = 120.0     # 2 min before anaphase; the count is flat at 0.5-0.7 for 1-3 min so the choice is not load-bearing
    for _b, _tr in _pt.items():
        _an = lib.parse_time((mr.get(_b, {}) or {}).get("Anaphase Onset (s)", ""))
        if _an is None: continue
        _POLAR_AT_ANA[_b] = sum(1 for _t, _ts in _tr.items() if any(_an - _W <= _x <= _an for _x in _ts))
except Exception as _e:
    print(f"  (polar-at-anaphase not measured: {_e})")
print(f"  polar-at-anaphase measured for {len(_POLAR_AT_ANA)} cells")

# V3: swimmer/raster — cells sorted by metaphase duration; per-KT congression dots + polar bars to anaphase
# ── CONGRESSION TIMES from CHROMOSOME_MASTER.csv (added 2026-08-10) ───────────────────────────────
# USER 2026-08-10: "look through not just the master csv but also all of the master annotation csvs and any
# other csvs containing data or comments". Doing that turned up `annotations/CHROMOSOME_MASTER.csv`, which
# this builder never read: it carries a per-chromosome `behavior` (congressed / noncongression / at_plate)
# AND `congression_time_s` for 57 cohort cells / 66 timed congressions. It adds no new CELLS, but it does
# supply times this builder lacked -- a congression with no time draws NOTHING, so those KTs were silently
# invisible even though their behaviour was recorded. `20260420 ptk2 eyfp cdc20 1 ablation_30` is exactly
# that case: congressed at 577 s here, blank in the sources this builder was using.
_CM_TIMES = {}
try:
    import csv as _c5
    for _r in _c5.DictReader(open("/Volumes/4 MB/annotations/CHROMOSOME_MASTER.csv",
                                  newline="", encoding="utf-8", errors="replace")):
        _b = (_r.get("batch") or "").strip()
        if (_r.get("behavior") or "").strip() != "congressed": continue
        try: _t = float((_r.get("congression_time_s") or "").strip()) / 60.0   # the column is SECONDS;
        except Exception: continue                                              # this builder works in MINUTES
        _CM_TIMES.setdefault(_b, []).append(_t)
    for _r2 in rows:
        _b = _r2["batch"]
        _avail = sorted(_CM_TIMES.get(_b, []))
        if not _avail: continue
        _used = {tm for t, tm in _r2["beh"] if t == "congress" and tm is not None}
        _spare = [t for t in _avail if t not in _used]
        _new = []
        for _t, _tm in _r2["beh"]:
            if _t == "congress" and _tm is None and _spare:
                _new.append((_t, _spare.pop(0)))
            else:
                _new.append((_t, _tm))
        _r2["beh"] = _new
    _filled = sum(1 for _r2 in rows for t, tm in _r2["beh"] if t == "congress" and tm is not None)
    print(f"  CHROMOSOME_MASTER: {len(_CM_TIMES)} cells with timed congressions; "
          f"congression events now carrying a time: {_filled}")
except Exception as _e:
    print(f"  CHROMOSOME_MASTER times not merged: {_e}")

# ── PREABL_CHROMOSOME_ASSIGNMENT + NOTABLE_BATCHES cross-check (added 2026-08-10) ──────────────────
# Continuing the sweep she asked for. Of the four unread sources found:
#   PREABL_CHROMOSOME_ASSIGNMENT.csv  per-chromosome `behavior` -> MERGED here as fates
#   4_TABLES_AND_REPORTS/NOTABLE_BATCHES_20260623.csv      prose observations -> used only as a CROSS-CHECK, never as data,
#                                     because "polar cdc20 signal" is an observation, not a per-KT fate
#   batch_meta.csv                    processing comments ("slide", "change anaphase time") -> not behaviour
import collections as _coll
_MAP = {"noncongression": "polar", "congressed": "congress", "at_plate": "atplate"}
_pre = {}
try:
    import csv as _c6
    # ONE FATE PER CHROMOSOME, not per PREABL row. PREABL_CHROMOSOME_ASSIGNMENT carries one row per
    # ABLATION ATTEMPT, so a chromosome hit twice (two ablation_frame values, same chr_num) appears twice --
    # `20251029 single_ablation_13` has ids 168 and 169, both chr_num 1, both `noncongression`. Counting rows
    # gave that 1-sisterless cell TWO polar kinetochores, which is impossible, and it was the single value
    # above 1 in the whole 1-sisterless group. Key on (batch, chr_num) so a re-ablated chromosome counts once.
    _seen6 = set()
    for _r in _c6.DictReader(open("/Volumes/4 MB/annotations/PREABL_CHROMOSOME_ASSIGNMENT.csv",
                                  newline="", encoding="utf-8", errors="replace")):
        _b = (_r.get("batch") or "").strip()
        _v = _MAP.get((_r.get("behavior") or "").strip().lower())
        _k6 = (_b, (_r.get("chr_num") or "").strip())
        if not (_b and _v) or _k6 in _seen6: continue
        _seen6.add(_k6)
        _pre.setdefault(_b, []).append(_v)
    _added = 0; _capped = []; _replaced = []
    for _r2 in rows:
        _want_l = _pre.get(_r2["batch"], [])
        _have = _coll.Counter(t for t, _ in _r2["beh"])
        _want = _coll.Counter(_want_l)
        # PROSE LOSES TO PREABL. The regex prose parser is my inference over her free text; PREABL is her
        # structured per-chromosome behaviour. Where a PROSE-sourced cell is already at its cap and PREABL
        # disagrees, REPLACE rather than append -- appending was producing impossible >n fate lists, and
        # refusing outright keeps a known-bad parse. `20260420 ...ablation_22` is exactly this: her note
        # reads "sisterless kt ... polar until anaphase", but the sentence about the junk shape ("never seen
        # with kinetochores and never aligns to metaphase plate") tripped the `never seen` at-plate pattern,
        # so the parser stored at-plate for a cell PREABL and master `Polar Chromosomes`=Yes both call polar.
        if (_r2["src"] == "prose" and _want_l and len(_want_l) == _r2["group"]
                and _have != _want and len(_r2["beh"]) >= _r2["group"]):
            _replaced.append((_r2["batch"], sorted(_have.elements()), sorted(_want.elements())))
            _r2["beh"] = [(_t, None) for _t in _want_l]; _r2["src"] = "preabl_structured"
            continue
        for _t, _n in _want.items():
            _gap = _n - _have.get(_t, 0)
            for _ in range(max(0, _gap)):
                # HARD CONSTRAINT: a cell cannot have more sisterless-KT fates than it has sisterless KTs
                # (`# Sisterless KTs` == r["group"], the column the whole cohort is binned on).
                if len(_r2["beh"]) >= _r2["group"]:
                    _capped.append((_r2["batch"], _t)); break
                _r2["beh"].append((_t, None)); _added += 1
    print(f"  PREABL_CHROMOSOME_ASSIGNMENT: {len(_pre)} cells; fates added where missing: {_added}"
          + (f"; {len(_capped)} refused (would exceed # Sisterless KTs): "
             + ", ".join(f'{b[:34]}:{t}' for b, t in _capped[:6]) if _capped else ""))
    for _b, _old, _new in _replaced:
        print(f"    prose->PREABL replace: {_b[:44]:44s} {_old} -> {_new}")
except Exception as _e:
    print(f"  PREABL not merged: {_e}")

# cross-check the polar count against her prose evidence, and SAY when they disagree rather than silently
# trusting either one
try:
    import csv as _c7, re as _re7
    _eviD = {}
    for _r in _c7.DictReader(open("/Volumes/4 MB/4_TABLES_AND_REPORTS/NOTABLE_BATCHES_20260623.csv",
                                  newline="", encoding="utf-8", errors="replace")):
        _b = (_r.get("batch") or "").strip()
        _e = ((_r.get("polar_evidence") or "") + " " + (_r.get("lagging_evidence") or "")).strip()
        if _b and _e: _eviD[_b] = _e
    _dis = []
    for _r2 in rows:
        _b = _r2["batch"]
        if _b not in _eviD: continue
        _npol = sum(1 for t, _ in _r2["beh"] if t == "polar")
        _says_polar = bool(_re7.search(r"polar", _eviD[_b], _re7.I))
        if _says_polar and _npol == 0: _dis.append((_b, _npol, _eviD[_b][:60]))
    if _dis:
        print(f"  NOTABLE_BATCHES mentions polar but this builder has 0 polar KTs for {len(_dis)} cell(s):")
        for _b, _n, _e in _dis[:8]: print(f"     {_b[:44]:44s} {_e}")
except Exception as _e:
    print(f"  NOTABLE cross-check skipped: {_e}")

plot_rows=[r for r in rows if yval(r) is not None and r["full"] and r["ana"] is not None and r["meta"] is not None]
plot_rows.sort(key=lambda r:yval(r))
fig,ax=plt.subplots(figsize=(8.6,max(5,len(plot_rows)*0.14)))
# ── ITEM 15 (user 2026-08-04): "there are some groups that are grey, which I take to mean theyre not in
# a 1,2,or 3 group. Resolve this and fix it on the plot."
# The grey is NOT an unassigned group — every plotted cell is 1/2/3-sisterless (the recorded CSV holds only
# those three). Grey is the metaphase TIMELINE drawn for every row at color="0.85". A row therefore reads as
# grey when it received NO coloured mark: its per-KT behaviour list produced neither a congression dot, an
# at-plate square, nor a polar bar. Those rows are counted and reported here rather than silently reading as
# a fourth group, and each is drawn with an explicit hollow marker + note so it cannot be misread again.
_unmarked=[]; _ANA_COUNTS=[]
# x-step between stacked at-plate squares: small enough not to read as a congression time, big enough to
# separate 1 from 2 from 3 kinetochores at this figure width
_maxdur=max((r["ana"]-r["meta"]) for r in plot_rows) if plot_rows else 1.0
_DX=max(_maxdur*0.013,0.35)
for i,r in enumerate(plot_rows):
    dur=r["ana"]-r["meta"]
    # ITEM 15: the base timeline was neutral grey, and the GROUP colour only ever appeared via a
    # congression dot or a polar bar. A cell whose sisterless KTs all congressed therefore rendered as a
    # plain grey line — which reads as a fourth, unassigned group. It is not: every plotted cell is
    # 1/2/3-sisterless. Tint the timeline with the cell's own group colour (light) so group membership is
    # readable on EVERY row regardless of outcome.
    # USER 2026-08-17: "for that sideways bar plot, you use differet transparencies for the lines, but dont
    # do this." (Restated 2026-08-19 as item 18, "not updated based on previous feedback".) There were TWO
    # line opacities on this figure -- .30 for the metaphase timeline and .60 for the polar bars -- so a row
    # read as darker or lighter for a reason that carried no meaning. Both are now fully opaque and the two
    # line KINDS are told apart by WIDTH alone, which also survives greyscale (NOTES rule 30's second channel).
    ax.plot([0,dur],[i,i],color=GC[r["group"]],lw=1.1,alpha=1.0,zorder=1)  # metaphase timeline, group-tinted
    _marked=False
    for typ,tm in r["beh"]:
        if typ in ("congress","atplate","polar"): _marked=True
    if not _marked:
        _unmarked.append(r)
        ax.scatter(dur/2.0,i,facecolors="none",edgecolors="#b30000",s=30,lw=1.0,marker="x",zorder=4)
    # USER 2026-08-04: "how is it annotated differently if multiple kinetochores start out at plate?
    # Right now no matter what it seems like there is just a square." It was one square because EVERY
    # at-plate KT was drawn at exactly (0, i) — two or three of them landed on top of each other and were
    # indistinguishable from one. Draw one square PER at-plate kinetochore, stepped along x so the count is
    # readable. The polar bars had the identical defect (n identical bars over the same span), so the bar
    # thickens with the number of polar KTs.
    n_atpl=sum(1 for typ,_ in r["beh"] if typ=="atplate")
    n_pol =sum(1 for typ,_ in r["beh"] if typ=="polar")
    for k in range(n_atpl):
        ax.scatter(k*_DX,i,facecolors="none",edgecolors=GC[r["group"]],s=22,zorder=3,marker="s")
    # ONE BAR PER POLAR KINETOCHORE, not one bar made thicker.
    # USER 2026-08-10: "many of the bars still don't have sufficient kt behavior marks". This is the cause
    # I missed: a cell with two or three KTs that never congress drew a SINGLE bar with lw scaled by the
    # count, so a triple carrying two polar KTs was visually indistinguishable from one carrying one -- the
    # marks were there in the data but not on the page. Each polar KT now gets its own bar, offset within
    # the row, matching how the at-plate squares and the anaphase circles are one-per-KT.
    if n_pol:
        _off = 0.30 / max(1, n_pol)          # spread inside the row without colliding with neighbours
        for _k in range(n_pol):
            _y = i + (_k - (n_pol - 1) / 2.0) * _off
            ax.plot([0, dur], [_y, _y], color=GC[r["group"]], lw=2.8, alpha=1.0, zorder=2)
    for typ,tm in r["beh"]:
        if typ=="congress" and tm is not None:
            x=max(0,tm-r["meta"]); ax.scatter(x,i,color=GC[r["group"]],s=22,zorder=3,marker="o")
    ax.scatter(dur,i,color="k",marker="|",s=40,zorder=4)  # anaphase
    # POLAR KTs THE CELL ENTERED ANAPHASE WITH — one filled circle per KT, none when zero.
    # USER 2026-08-10: "I don't like the open circles. Take those off ... lack of a circle the viewer can
    # assume means no polar at anaphase. If multiple polar at anaphase, put multiple circles (like the
    # squares at the beginning)."
    #
    # SOURCE CORRECTED at the same time. This used to read an OUTLINE-derived count, which covered only 36
    # of the 66 cells and reported a maximum of one polar KT per cell -- so I told her no cell enters
    # anaphase with more than one, which was an artifact of outline coverage, not biology. HER behaviour
    # determinations cover all 66 cells and record 2 or 3 polar KTs in several: 3-sisterless {0:11, 1:6,
    # 2:3, 3:2}, 2-sisterless {0:4, 2:4}. The two disagree on 11 of the 36 cells both describe, and hers
    # is the authority, so the circles are drawn from `n_pol` — the same field the polar BAR is drawn from.
    if n_pol:
        for _k in range(n_pol):
            ax.scatter(dur + _DX * (0.9 + _k * 0.9), i, color=GC[r["group"]], s=26, zorder=5,
                       marker="o", edgecolor="k", lw=.4)
    _ANA_COUNTS.append((r["group"], n_pol))
# 2026-08-04: spelling the whole key out on one line made this label wider than the axes and it was clipped
# at both ends. Axis label stays short; the key wraps onto its own line underneath.
# ── USER 2026-08-17, the second half of the same message ─────────────────────────────────────────────
# "and again i want wsomething on that plot to show the idea of that triple cells congress chromosomes until
#  on average they ente[r anaphase]"
# i.e. the figure should SAY where each group's congression typically finishes, not leave it to be read off
# a cloud of dots. Per group: the MEDIAN congression time over every timed congression event in that group,
# drawn as a vertical line in the group's own colour. It is a median over EVENTS within a group, which is
# what "on average they congress until" means here -- a per-cell aggregate would hide cells with two or
# three sisterless KTs congressing at different times, and those are the whole point of the 3-sis group.
_CONG = {}
for _r in plot_rows:
    for _typ, _tm in _r["beh"]:
        if _typ == "congress" and _tm is not None and _r.get("meta") is not None:
            _CONG.setdefault(_r["group"], []).append(max(0.0, _tm - _r["meta"]))
for _g in sorted(_CONG):
    _v = sorted(_CONG[_g])
    if len(_v) < 3: continue
    _med = float(np.median(_v))
    ax.axvline(_med, color=GC[_g], ls=(0, (4, 2)), lw=1.8, zorder=6)
    ax.plot([], [], color=GC[_g], ls=(0, (4, 2)), lw=1.8,
            label=f"{_g}-sis median congression {_med:.1f} min (n={len(_v)} KTs)")
ax.set_yticks([]); ax.set_xlabel("Time from metaphase start (min)")
ax.text(0.0, -0.085,
        "dot = congression   ·   square = at plate from metaphase onset (one per KT)   ·   "
        "bar = polar until anaphase (thicker = more polar KTs)   ·   | = anaphase",
        transform=ax.transAxes, ha="left", va="top", fontsize=7, color="#444")
_am = {}
for _g in (1, 2, 3):
    _v = [n for g_, n in _ANA_COUNTS if g_ == _g]
    if _v: _am[_g] = (len(_v), float(np.mean(_v)))
if _am:
    _txt = "   ·   ".join(f"{g}-sis {m:.2f} (n={n})" for g, (n, m) in sorted(_am.items()))
    ax.text(0.0, -0.113,
            "circles past the anaphase tick = how many polar KTs the cell ENTERED ANAPHASE with, one circle\n"
            "each, from her behaviour determinations (no circle = none).   mean per cell:  " + _txt,
            transform=ax.transAxes, ha="left", va="top", fontsize=7, color="#444", linespacing=1.5)
ax.set_ylabel(f"cells sorted by metaphase duration (N={len(plot_rows)})")
for g in (1,2,3): ax.plot([],[],color=GC[g],lw=3,label=f"{g}-sisterless")
ax.scatter([],[],facecolors="none",edgecolors="#555",marker="s",s=22,label="at plate from metaphase onset (1 square per KT)")
ax.scatter([],[],color="#555",marker="o",s=26,edgecolor="k",lw=.4,
           label="polar KT at anaphase (one circle per KT; none = zero)")
if _unmarked:
    ax.scatter([],[],facecolors="none",edgecolors="#b30000",marker="x",s=30,
               label=f"no per-KT event recorded (n={len(_unmarked)})")
# ── USER (repeated, most recently 2026-08-20 board 5 item 1): "i want something ON that plot to show the
# idea of that triple cells congress chromosomes until on average they enter anaphase with less than 1
# polar, similar to single sisterless."
# The numbers were already computed, but they sat in 7 pt grey text UNDER the axes -- which is not "on the
# plot", and is why she has had to ask more than once. They are now an inset: three bars of mean polar KTs
# per cell at anaphase against a reference line at 1.0, so the point ("all below 1, and the triple bar is
# no taller than the single bar") is readable at a glance without doing arithmetic on a caption.
if _am:
    # upper-right: the legend owns the lower-right corner and the long bars own the upper-LEFT, so this
    # band is the only region of the axes with nothing in it (checked against the render, not assumed).
    _ins = ax.inset_axes([0.665, 0.615, 0.245, 0.175])
    _gs = sorted(_am)
    _ins.bar(range(len(_gs)), [_am[g][1] for g in _gs],
             color=[GC[g] for g in _gs], width=0.68, zorder=2)
    _ins.axhline(1.0, ls=(0, (3, 2)), lw=1.4, color="#333", zorder=3)
    _ins.text(len(_gs) - 0.42, 1.0, " 1 polar KT", va="center", ha="left", fontsize=6.5, color="#333")
    for _i, _g in enumerate(_gs):
        _ins.text(_i, _am[_g][1] + 0.045, f"{_am[_g][1]:.2f}", ha="center", va="bottom", fontsize=6.5)
    _ins.set_xticks(range(len(_gs))); _ins.set_xticklabels([f"{g}-sis" for g in _gs], fontsize=6.5)
    _ins.set_ylim(0, max(1.25, max(_am[g][1] for g in _gs) * 1.35))
    _ins.set_yticks([0, 1]); _ins.tick_params(labelsize=6.5, length=2)
    _ins.set_title("polar KTs per cell\nAT ANAPHASE", fontsize=7, pad=2)
    for _sp in ("top", "right"): _ins.spines[_sp].set_visible(False)
    _ins.patch.set_alpha(0.92)

ax.set_title("Per-cell sisterless-KT resolution timeline (sorted by metaphase duration)"); ax.legend(fontsize=8,loc="lower right")
print(f"ITEM 15: {len(_unmarked)} of {len(plot_rows)} rows had no coloured mark (grey-looking): "
      + ", ".join(r["batch"][:40] for r in _unmarked[:6]))
# 2026-08-03 (item 3, "n should be higher / all cells should have behavior specified"): state the accounting
# ON THE FIGURE so N is never silently short. Eligible cohort = 1/2/3-sisterless, on-target, cdc20 (non-mad1),
# non-drug, non-collagen, non-excluded, non-metaphase-ablation (see ok() above). Of that cohort, every cell
# with a resolvable behavior for ALL its sisterless KTs is plotted here; the rest (if any) lack a timestamp
# or a still-unresolved behavior and are listed by name/reason in 4_TABLES_AND_REPORTS/SISTERLESS_BEHAVIOR_NEEDS_REVIEW_20260718.csv.
_n_elig=len(rows); _n_full=nfull; _n_notime=sum(1 for r in rows if r["full"] and yval(r) is not None and (r["ana"] is None or r["meta"] is None))
_n_nodur=sum(1 for r in rows if r["full"] and yval(r) is None)
_acct=f"N={len(plot_rows)} of {_n_elig} eligible cohort cells shown  |  {_n_full}/{_n_elig} have every sisterless KT's behavior specified"
if review: _acct+=f"  |  {len(review)} still unresolved (see 4_TABLES_AND_REPORTS/SISTERLESS_BEHAVIOR_NEEDS_REVIEW_20260718.csv): {', '.join(x[0] for x in review)}"
else: _acct+="  |  0 unresolved — every eligible cell's behavior is specified"
if _n_notime or _n_nodur: _acct+=f"  |  {_n_notime+_n_nodur} fully-described but missing a metaphase/anaphase timestamp, not placeable on this timeline"
if recovered_used: _acct+=f"  |  {len(recovered_used)} of these recovered 2026-08-03 from CHROMO_LENGTH_BEHAVIOR_PAIRING.csv (the pairing tool), a source this builder did not previously read"
ax.text(0.01,1.045,_acct,transform=ax.transAxes,ha="left",va="bottom",fontsize=6.6,color="0.25",wrap=True)
save(fig,"G4_sisbehav_swimmer","Per-cell sisterless-KT resolution timeline sorted by metaphase duration",
     ["batch","group","metaphase_duration_min","source"],[[r["batch"],r["group"],round(yval(r),2),r["src"]] for r in plot_rows])

# V4: fraction of sisterless KTs that congressed/joined vs duration
fig,ax=plt.subplots(figsize=(7.4,5.4))
for r in rows:
    y=yval(r)
    if y is None or not r["full"]: continue
    frac=(r["n_cong"]+r["n_atpl"])/r["group"]
    jit=np.random.default_rng(abs(hash(r["batch"]+"f"))%2**32).uniform(-0.03,0.03)
    ax.scatter(frac+jit,y,color=GC[r["group"]],alpha=.8,s=42,edgecolor="w",lw=.5,**MSRC[r["src"]],zorder=3)
for g in (1,2,3): ax.scatter([],[],color=GC[g],label=f"{g}-sisterless")
ax.set_xlabel("Fraction of sisterless KTs that joined the plate (congressed or at-plate)"); ax.set_ylabel(YL)
ax.set_title("Metaphase duration vs fraction of sisterless KTs that joined the plate"); ax.legend(fontsize=8)
save(fig,"G4_sisbehav_fracjoined_vs_duration","Metaphase duration vs fraction of sisterless KTs that joined the plate",
     ["batch","group","frac_joined","metaphase_duration_min","source"],
     [[r["batch"],r["group"],round((r["n_cong"]+r["n_atpl"])/r["group"],2),round(yval(r),2) if yval(r) else "",r["src"]] for r in rows if yval(r) and r["full"]])
print("DONE")


# ── ITEM 15 (part 2, user 2026-08-04): "are there any significant relationships in this plot regarding
# chromosome behaviour and metaphase duration?" Tested explicitly rather than left to the eye.
def _item15_stats():
    from scipy import stats as _st
    import numpy as _np
    rows_ = [r for r in plot_rows if yval(r) is not None]
    def dur(r): return r["ana"] - r["meta"]
    cat = {}
    for r in rows_:
        types = {t for t, _ in r["beh"]}
        if "polar" in types:      k = "any KT stayed polar"
        elif "congress" in types: k = "all congressed (none polar)"
        else:                     k = "all at plate throughout"
        cat.setdefault(k, []).append(dur(r))
    out = []
    ks = [k for k in cat if len(cat[k]) >= 3]
    if len(ks) >= 2:
        try:
            H, p = _st.kruskal(*[cat[k] for k in ks])
            out.append(f"Kruskal across {len(ks)} behaviour classes: H={H:.2f}, p={p:.3g}")
        except Exception: pass
        for i in range(len(ks)):
            for j in range(i + 1, len(ks)):
                u, p = _st.mannwhitneyu(cat[ks[i]], cat[ks[j]], alternative="two-sided")
                out.append(f"{ks[i]} (n={len(cat[ks[i]])}, med {_np.median(cat[ks[i]]):.1f}) vs "
                           f"{ks[j]} (n={len(cat[ks[j]])}, med {_np.median(cat[ks[j]]):.1f}): MW p={p:.3g}")
    # does the NUMBER of polar KTs scale with duration?
    npol = [(sum(1 for t, _ in r["beh"] if t == "polar"), dur(r)) for r in rows_]
    if len(npol) >= 6:
        rho, p = _st.spearmanr([x for x, _ in npol], [y for _, y in npol])
        out.append(f"# KTs staying polar vs metaphase duration: Spearman rho={rho:+.2f}, p={p:.3g}, N={len(npol)}")
    # and the LATEST congression time?
    lat = [(max((tm - r["meta"] for t, tm in r["beh"] if t == "congress" and tm is not None), default=None), dur(r))
           for r in rows_]
    lat = [(x, y) for x, y in lat if x is not None]
    if len(lat) >= 6:
        rho, p = _st.spearmanr([x for x, _ in lat], [y for _, y in lat])
        out.append(f"latest congression time vs metaphase duration: Spearman rho={rho:+.2f}, p={p:.3g}, N={len(lat)}")
    print("ITEM 15 STATS:")
    for line in out: print("   " + line)
    with open("/Volumes/4 MB/ablation_plots/ITEM15_swimmer_stats_20260804.txt", "w") as f:
        f.write("G4_sisbehav_swimmer — behaviour vs metaphase duration (ITEM 15, 2026-08-04)\n\n"
                + "\n".join(out) + "\n")
_item15_stats()
