"""Audit N per sisterless group across the 3 violin scripts' CURRENT filtering logic."""
import sys; sys.path.insert(0,"/Volumes/4 MB/ablation_figures_20260625")
import lib, re, json, os

data,_=lib.load_master()
dbl=lib.double_chromosome_batches()

# ---- g1_violin2 logic: assign_cohorts (Exclude, mad1, drug, dbl excluded, IQR screened) ----
coh=lib.assign_cohorts()
g1={s:len(coh[f"{s}-Sister"]) for s in "1234"}
g1_batches={s:set(b for b,_ in coh[f"{s}-Sister"]) for s in "123"}

# ---- group2_build phase-split logic ----
act2=[r for r in data if r.get("Exclude") not in ("Yes","yes") and r["Batch Name"] not in dbl and not lib.is_drug(r["Batch Name"])]
def phase_of(r):
    p=r.get("Phase of Ablations","").strip().lower()
    return ("Prophase" if p.startswith("proph") else "Prometaphase" if p.startswith("promet") else "Metaphase" if p.startswith("metaph") else None)
def mdur(r):
    d,ok=lib.mitotic_duration_min(r); return d if ok else None
ps={}
ps_batches={s:set() for s in "123"}
for s in "123":
    cnt=0
    for r in act2:
        if r.get("On-Target / Off-Target")=="On-target" and r.get("# Sisterless KTs")==s and phase_of(r) in ("Prophase","Prometaphase"):
            if mdur(r) is not None:
                cnt+=1; ps_batches[s].add(r["Batch Name"])
    ps[s]=cnt

# phase distribution of the canonical g1 cohort
phase_dist={s:{} for s in "123"}
mr={r["Batch Name"]:r for r in data}
for s in "123":
    for b in g1_batches[s]:
        ph=phase_of(mr.get(b,{})) or "NONE"
        phase_dist[s][ph]=phase_dist[s].get(ph,0)+1

# ---- group4_exhaustion_violin logic ----
ex={}
ex_batches={s:set() for s in "123"}
for s in "123":
    cnt=0
    for r in data:
        if r.get("On-Target / Off-Target")=="On-target" and not lib.is_drug(r["Batch Name"]) and not lib.is_mad1(r["Batch Name"]) and r.get("# Sisterless KTs")==s:
            d,ok=lib.mitotic_duration_min(r)
            if ok: cnt+=1; ex_batches[s].add(r["Batch Name"])
    ex[s]=cnt

print("=== N per sisterless group (BEFORE) ===")
print(f"{'group':<12}{'g1_violin2':>12}{'phase_split':>14}{'exhaustion':>12}")
for s in "123":
    print(f"{s}-sisterless{'':<2}{g1[s]:>12}{ps[s]:>14}{ex[s]:>12}")
print(f"4-sisterless{'':<2}{g1['4']:>12}{'-':>14}{'-':>12}")

print("\n=== phase distribution of g1 canonical cohort ===")
for s in "123":
    print(f"{s}-sisterless: {phase_dist[s]}")

print("\n=== batch-set differences (exhaustion minus g1) ===")
for s in "123":
    extra=ex_batches[s]-g1_batches[s]
    missing=g1_batches[s]-ex_batches[s]
    print(f"{s}-sis: in exhaustion-not-g1 ({len(extra)}): {sorted(extra)}")
    print(f"       in g1-not-exhaustion ({len(missing)}): {sorted(missing)}")
print("\n=== phase-split vs g1 (g1 minus phase-split) ===")
for s in "123":
    miss=g1_batches[s]-ps_batches[s]
    print(f"{s}-sis: in g1-not-phasesplit ({len(miss)}): {sorted(miss)}")
