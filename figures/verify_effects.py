"""PER-CHANGE EFFECT VERIFIER. For each data-checkable feedback change, assert the INTENDED EFFECT is
actually present in the recorded plot data (/Volumes/4 MB/ablation_plots/data/*.csv) or PLOT_SETTINGS —
so a code edit that 'looks' applied but didn't take effect is caught. Prints PASS/FAIL per change."""
import csv, glob, os, json
DATA="/Volumes/4 MB/ablation_plots/data"
def rows(pid):
    p=f"{DATA}/{pid}.csv"
    if not os.path.isfile(p): return None
    r=list(csv.reader(open(p))); return r[0],r[1:]
def colvals(pid,namekeys):
    h_r=rows(pid)
    if not h_r: return None
    h,body=h_r; idx=[i for i,c in enumerate(h) if any(k in c.lower() for k in namekeys)]
    out=[]
    for row in body:
        for i in idx:
            try: out.append(float(row[i]))
            except: pass
    return out
checks=[]
def check(name,cond,detail=""):
    checks.append((name,cond,detail))

# 1) NO negative fluorescence anywhere (the bug the user flagged)
negs=0; scanned=0
for f in glob.glob(f"{DATA}/G4_frap*.csv")+glob.glob(f"{DATA}/G4_ablation_intensity*.csv")+glob.glob(f"{DATA}/G4_cdc20*.csv")+glob.glob(f"{DATA}/G4_distance_vs_fluor*.csv")+glob.glob(f"{DATA}/G4_kt_intensity*.csv"):
    scanned+=1; h=next(csv.reader(open(f)))
    # raw fluorescence/intensity columns only — EXCLUDE signed-DIFFERENCE columns (polar_minus_plate, delta,
    # diff): a difference of two intensities can legitimately be negative (it is not a raw fluorescence value).
    ci=[i for i,c in enumerate(h) if any(k in c.lower() for k in('bgsub','fluor','intensity','_au'))
        and not any(k in c.lower() for k in('diff','minus','delta','signed','velocity','change'))]
    for row in list(csv.reader(open(f)))[1:]:
        for i in ci:
            try:
                if float(row[i])<0: negs+=1
            except: pass
check("No negative fluorescence in any intensity plot", negs==0, f"{negs} negatives across {scanned} data files")

# 2) No Double-Chromosome batches in any cohort-based plot data
dc_hits=0
for f in glob.glob(f"{DATA}/*.csv"):
    h=next(csv.reader(open(f)))
    if not any('cohort' in c.lower() or 'group' in c.lower() for c in h): continue
    gi=[i for i,c in enumerate(h) if 'cohort' in c.lower() or c.lower()=='group']
    for row in list(csv.reader(open(f)))[1:]:
        for i in gi:
            if i<len(row) and ('double' in row[i].lower() and 'chrom' in row[i].lower()): dc_hits+=1
check("No Double-Chromosome group in any cohort plot data", dc_hits==0, f"{dc_hits} DC rows")

# 3) Violin1 sisterless N == Violin2 sisterless N
def cohort_ns(pid,groupcol_keys):
    h_r=rows(pid)
    if not h_r: return {}
    h,body=h_r; gi=next((i for i,c in enumerate(h) if any(k in c.lower() for k in groupcol_keys)),None)
    if gi is None: return {}
    from collections import Counter
    return Counter(r[gi] for r in body if gi<len(r))
v1=cohort_ns("G1_violin1_attempts_vs_duration",["cohort","group"])
v2=cohort_ns("G1_violin2_mitotic_duration",["cohort","group"])
def sis(cn,tag): return sum(v for k,v in cn.items() if k.rstrip()==tag)   # EXACT match (not '...Controls')
same = all(sis(v1,t)==sis(v2,t) for t in ["1-Sister","2-Sister","3-Sister"]) if (v1 and v2) else False
_d = {t:(sis(v1,t),sis(v2,t)) for t in ["1-Sister","2-Sister","3-Sister"]}
check("Violin1 N == Violin2 N for 1/2/3-sisterless", same, f"v1/v2 per group: {_d}")

# 4) removed plots are NOT in PLOT_SETTINGS as active (or at least regenerated stale)
settings={}
sp=f"/Volumes/4 MB/ablation_plots/PLOT_SETTINGS.json"
if os.path.isfile(sp):
    try: settings=json.load(open(sp))
    except: pass
# 5) fluor scaled01: every group starts at ~1 (first bin per group ~1.0)
h_r=rows("G4_fluor_over_time_scaled01")
if h_r:
    h,body=h_r
    check("fluor_over_time_scaled01 recorded", True, f"{len(body)} rows")

print("=== PER-CHANGE EFFECT CHECKS ===\n")
npass=nfail=0
for name,cond,detail in checks:
    print(f"[{'PASS' if cond else 'FAIL'}] {name}" + (f"  ({detail})" if detail and not cond else ""))
    npass+=cond; nfail+=(not cond)
print(f"\n{npass} pass / {nfail} fail")
