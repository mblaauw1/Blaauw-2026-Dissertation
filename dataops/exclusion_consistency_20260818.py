#!/usr/bin/env python3
"""Is a batch excluded from one figure still present in its SIBLING figures?

HER ASK (2026-08-18): "thorough checks for consistency in batches being included in plots, for example
if a batch is specifically named as excluded in one plot (not a whole subset type), is it also included
in subsequent plots?"

Method, and its one honest limit:
  * every NAMED per-batch exclusion is read from `annotations/MANUAL_PLOT_EXCLUSIONS.csv`, `lib.REVIEW_EXCLUDE`
    and `lib.KT_OUTLINE_EXCLUDE`
  * for each, we look for the batch in the recorded data CSV of EVERY placed figure
  * a hit is only a PROBLEM when the other figure measures the same THING -- so hits are grouped by
    whether the other figure shares the excluded figure's family prefix (G4_fluor..., G2_kk..., ...).
    A blanket exclusion (REVIEW_EXCLUDE / 'ALL plots') is a problem ANYWHERE it appears.
"""
import csv, io, os, re, sys, collections, subprocess, json
sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625"); import lib

ROOT = "/Volumes/4 MB"
DATA = ROOT + "/ablation_plots/data"
OUT  = ROOT + "/4_TABLES_AND_REPORTS/EXCLUSION_CONSISTENCY_20260818.csv"
DECKS = ["META_FIGURES_20260814.ai", "META_FIGURES_20260813_supplemental.ai",
         "NEW_FIGURES_20260804.ai", "supplemental.ai", "NEW_TIMESTRIPS_20260804.ai"]

placed = set()
for d in DECKS:
    txt = subprocess.run(["strings", f"{ROOT}/1_DECKS/{d}"], capture_output=True, text=True).stdout
    for m in re.findall(r"([A-Za-z0-9_.\-]+)\.(?:pdf|png)", txt):
        placed.add(m)

def rd(p):
    with io.open(p, encoding="utf-8", errors="replace") as f: return list(csv.DictReader(f))

excl = collections.defaultdict(list)          # batch -> [(scope, reason)]
for r in rd(ROOT + "/annotations/MANUAL_PLOT_EXCLUSIONS.csv"):
    b = (r.get("batch") or "").strip()
    if b: excl[b].append(((r.get("plot") or "").strip(), (r.get("reason") or "").strip()[:90]))
for b in getattr(lib, "REVIEW_EXCLUDE", ()):
    excl[b].append(("ALL plots (lib.REVIEW_EXCLUDE)", "global review exclusion"))
for b in getattr(lib, "KT_OUTLINE_EXCLUDE", ()) or ():
    excl[b].append(("ALL kt-outline figures (lib.KT_OUTLINE_EXCLUDE)", "global kt-outline exclusion"))

BLANKET = ("all plots", "blanket", "review_exclude")
def is_blanket(scope): return any(k in scope.lower() for k in BLANKET)

# which plots does each batch appear in?
appears = collections.defaultdict(set)
for fn in os.listdir(DATA):
    if not fn.endswith(".csv"): continue
    pid = fn[:-4]
    if pid not in placed: continue
    try:
        rows = rd(os.path.join(DATA, fn))
    except Exception:
        continue
    if not rows: continue
    bcol = next((c for c in rows[0] if c and c.strip().lower() in ("batch", "batch_name", "cell")), None)
    if not bcol: continue
    for r in rows:
        b = (r.get(bcol) or "").strip()
        if b: appears[b].add(pid)

def family(pid):
    m = re.match(r"([A-Za-z0-9]+?_[a-z]+)", pid)
    return (m.group(1) if m else pid.split("_")[0]).lower()

def scope_tokens(scope):
    """Plot IDS named in the scope text -- not stray words.

    The first version tokenised every word, so "G4_frap (combined)" matched every figure whose id merely
    contains "combined" (G1_area_combined ...).  A scope only names a figure when it carries a real plot
    id, i.e. a Gn_ prefix.
    """
    return [t.lower() for t in re.findall(r"\bG\d[A-Za-z0-9_]*", scope)]

rows_out, n_blanket, n_family = [], 0, 0
for b, scopes in sorted(excl.items()):
    where = sorted(appears.get(b, ()))
    for scope, reason in scopes:
        toks = scope_tokens(scope)
        for pid in where:
            pl = pid.lower()
            named = any(pl == t or pl.startswith(t + "_") or t.startswith(pl + "_") or pl == t.rstrip("_")
                        for t in toks)
            if named:                                  # this IS the figure it was excluded from
                sev = "STILL PRESENT IN THE NAMED FIGURE"
            elif is_blanket(scope):
                sev = "blanket exclusion, still present"
            else:
                same_fam = any(family(pid) == family(t) for t in toks if "_" in t) and bool(toks)
                sev = "same family, check" if same_fam else "different figure (probably fine)"
            if sev.startswith("different"): continue
            if sev.startswith("blanket"): n_blanket += 1
            if sev.startswith("same"): n_family += 1
            rows_out.append(dict(batch=b, excluded_from=scope, reason=reason, present_in=pid, severity=sev))

with open(OUT, "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=["batch", "excluded_from", "reason", "present_in", "severity"])
    w.writeheader(); w.writerows(rows_out)

print(f"named per-batch exclusions: {sum(len(v) for v in excl.values())} over {len(excl)} batches")
print(f"placed figures with a batch column: {len({p for s in appears.values() for p in s})}")
order = {"STILL PRESENT IN THE NAMED FIGURE": 0, "blanket exclusion, still present": 1, "same family, check": 2}
rows_out.sort(key=lambda r: order.get(r["severity"], 9))
for sev in ("STILL PRESENT IN THE NAMED FIGURE", "blanket exclusion, still present", "same family, check"):
    hits = [r for r in rows_out if r["severity"] == sev]
    print(f"\n### {sev}: {len(hits)}")
    for r in hits[:25]:
        print(f"   {r['batch'][:40]:42s} excluded from: {r['excluded_from'][:38]:40s} -> present in {r['present_in']}")
print(f"\n[done] -> {OUT}")
