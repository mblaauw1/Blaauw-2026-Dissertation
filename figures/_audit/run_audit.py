import os, csv, re
import lib

data, hdr = lib.load_master()

MISSING_TOKENS = {"", "n/a", "na", "n.a.", "-", "--", "none", "tbd", "?"}
def missing(v):
    return (v or "").strip().lower() in MISSING_TOKENS
def has(v):
    return not missing(v)

def excluded(r):
    return r.get("Exclude", "") in ("Yes", "yes")

def ev_positive(r):
    """Log Ablation Events is a positive integer."""
    v = (r.get("Log Ablation Events", "") or "").strip()
    return v.isdigit() and int(v) > 0

def sisterless_set(r):
    return has(r.get("# Sisterless KTs", ""))

def source_has_ablation(r):
    sf = (r.get("Source Files", "") or "").lower()
    return ("ablat" in sf) or ("pointandshoot" in sf) or ("pas" in sf)

def has_ablation_movie(r):
    return ev_positive(r) or sisterless_set(r) or source_has_ablation(r)

def meta_ana_dur(r):
    a = lib.parse_time(r.get("Metaphase Start (s)", ""))
    b = lib.parse_time(r.get("Anaphase Onset (s)", ""))
    if a is None or b is None:
        return None
    return (b - a) / 60.0

OT = "On-Target / Off-Target"

# ---------- A1 ----------
# On-target, in main violin (not excl, not mad1, OT=='On-target', parseable Meta->Ana dur>0),
# missing Polar and/or Lagging selection.
a1 = []
for r in data:
    b = r["Batch Name"]
    if excluded(r) or lib.is_mad1(b):
        continue
    if r.get(OT, "") != "On-target":
        continue
    dur = meta_ana_dur(r)
    if dur is None or dur <= 0:
        continue
    polar = r.get("Polar Chromosomes", "")
    lag = r.get("Lagging Chromosomes", "")
    miss = []
    if missing(polar): miss.append("Polar Chromosomes")
    if missing(lag): miss.append("Lagging Chromosomes")
    if miss:
        a1.append((b, miss, polar, lag, lib.is_drug(b)))

# ---------- A2 ----------
# Both Meta & Ana parseable, not excluded, but blank On-Target value (silently dropped from cohorts).
a2 = []
for r in data:
    b = r["Batch Name"]
    if excluded(r):
        continue
    a = lib.parse_time(r.get("Metaphase Start (s)", ""))
    an = lib.parse_time(r.get("Anaphase Onset (s)", ""))
    if a is None or an is None:
        continue
    ot = (r.get(OT, "") or "").strip()
    if missing(ot):
        a2.append((b, lib.is_mad1(b)))

# ---------- A3 ----------
# Ablation file (events positive) AND parseable Meta AND Ana AND not excluded, but no Phase of Ablations.
a3 = []
for r in data:
    b = r["Batch Name"]
    if excluded(r):
        continue
    if not ev_positive(r):
        continue
    a = lib.parse_time(r.get("Metaphase Start (s)", ""))
    an = lib.parse_time(r.get("Anaphase Onset (s)", ""))
    if a is None or an is None:
        continue
    if missing(r.get("Phase of Ablations", "")):
        a3.append((b, r.get(OT, ""), r.get("Log Ablation Events", "")))

# ---------- A6 ----------
# All not-excluded, non-mad1: missing >=1 essential annotation.
# essential = Phase (required only if OT != Unmodified), OT group type,
#             # Sisterless KTs (required only if ablation movie), Metaphase Start, Anaphase Onset
a6 = []
for r in data:
    b = r["Batch Name"]
    if excluded(r) or lib.is_mad1(b):
        continue
    ot = (r.get(OT, "") or "").strip()
    miss = []
    if missing(ot):
        miss.append("On-Target/Off-Target")
    if ot != "Unmodified" and missing(r.get("Phase of Ablations", "")):
        miss.append("Phase of Ablations")
    if has_ablation_movie(r) and missing(r.get("# Sisterless KTs", "")):
        miss.append("# Sisterless KTs")
    if missing(r.get("Metaphase Start (s)", "")):
        miss.append("Metaphase Start (s)")
    if missing(r.get("Anaphase Onset (s)", "")):
        miss.append("Anaphase Onset (s)")
    if miss:
        present = []
        if has(ot): present.append("OT")
        if has(r.get("Metaphase Start (s)", "")): present.append("Meta")
        if has(r.get("Anaphase Onset (s)", "")): present.append("Ana")
        if has(r.get("Phase of Ablations", "")): present.append("Phase")
        if has(r.get("# Sisterless KTs", "")): present.append("Sis")
        a6.append((b, miss, bool(present)))  # started=True if any essential present
a6_partial = [(b, miss) for b, miss, started in a6 if started]
a6_blank = [(b, miss) for b, miss, started in a6 if not started]

# ---------- A4 gotchas ----------
a4 = []
# 1. On-Target values that are neither Unmodified/On-target/Off-target/blank
VALID_OT = {"", "Unmodified", "On-target", "Off-target"}
bad_ot = sorted({(r["Batch Name"], r.get(OT, "")) for r in data
                 if r.get(OT, "") not in VALID_OT})
# 2. casing variants (any non-exact match of canonical when lowercased equals canonical)
canon = {"unmodified": "Unmodified", "on-target": "On-target", "off-target": "Off-target"}
ot_casing = sorted({(r["Batch Name"], r.get(OT, "")) for r in data
                    if r.get(OT, "").strip() and r.get(OT, "").strip() not in canon.values()
                    and r.get(OT, "").strip().lower() in canon})
# 3. # Sisterless KTs non-numeric labels
sis_nonnum = sorted({(r["Batch Name"], r.get("# Sisterless KTs", "")) for r in data
                     if has(r.get("# Sisterless KTs", "")) and not r.get("# Sisterless KTs", "").strip().isdigit()})
# 4. Polar/Lagging non Yes/No values
poslag_bad = []
for r in data:
    for col in ("Polar Chromosomes", "Lagging Chromosomes"):
        v = r.get(col, "")
        if has(v) and v.strip() not in ("Yes", "No"):
            poslag_bad.append((r["Batch Name"], col, v))
# 5. stray whitespace in OT
ot_ws = sorted({(r["Batch Name"], repr(r.get(OT, ""))) for r in data
                if r.get(OT, "") != r.get(OT, "").strip()})

# ===== write outputs =====
AD = "/Volumes/4 MB/ablation_figures_20260625/_audit"
os.makedirs(AD, exist_ok=True)

def fmt_list(items):
    return "\n".join(items) if items else "(none)"

with open(os.path.join(AD, "AUDIT_completeness_20260629.md"), "w") as f:
    w = f.write
    w("# Ablation master completeness audit — 2026-06-29\n\n")
    w(f"Master: `{lib.MASTER}`  \nTotal data rows parsed: **{len(data)}**\n\n")
    w("Missing = value is blank or one of {n/a, na, -, --, none, tbd, ?} (case-insensitive).\n\n")
    w("---\n\n")

    w(f"## A1 — On-target batches IN the main mitotic-duration violin but missing Polar and/or Lagging selection\n\n")
    w(f"Criteria: not Exclude, not mad1, On-Target=='On-target', parseable Meta->Ana duration > 0.\n\n")
    n_drug = sum(1 for x in a1 if x[4])
    w(f"**Count: {len(a1)}**  (of which {n_drug} are is_drug=ZM/noc — those are actually excluded "
      f"from baseline violin cohorts by `is_drug()`, so {len(a1)-n_drug} are truly in the violin)\n\n")
    w("| Batch Name | Missing | Polar value | Lagging value | is_drug (not in baseline violin) |\n|---|---|---|---|---|\n")
    for b, miss, polar, lag, drug in sorted(a1):
        w(f"| {b} | {', '.join(miss)} | `{polar}` | `{lag}` | {'yes' if drug else 'no'} |\n")
    w("\n---\n\n")

    w(f"## A2 — Meta & Ana both set, not excluded, but BLANK On-Target (silently dropped from cohorts)\n\n")
    w(f"**Count: {len(a2)}**  (of these, mad1 batches noted — they're dropped anyway by is_mad1)\n\n")
    w("| Batch Name | is_mad1 (dropped regardless) |\n|---|---|\n")
    for b, mad in sorted(a2):
        w(f"| {b} | {'yes' if mad else 'no'} |\n")
    w("\n---\n\n")

    w(f"## A3 — Has ablation file (events>0) + Meta + Ana, not excluded, but NO Phase of Ablations\n\n")
    w(f"**Count: {len(a3)}**\n\n")
    w("| Batch Name | On-Target | Log Ablation Events |\n|---|---|---|\n")
    for b, ot, ev in sorted(a3):
        w(f"| {b} | `{ot}` | {ev} |\n")
    w("\n---\n\n")

    w(f"## A6 — Actionable: not-excluded, non-mad1 batches missing >=1 ESSENTIAL annotation\n\n")
    w("essential = {On-Target/Off-Target; Phase (if OT!=Unmodified); # Sisterless KTs (if ablation movie); Metaphase Start; Anaphase Onset}\n\n")
    w(f"**Total Count: {len(a6)}**  (full machine-readable list in `AUDIT_missing_essential_A6.csv`)\n\n")
    w(f"Breakdown:\n- **{len(a6_partial)} partially-annotated** (at least one essential already filled — these are the realistic, started-but-incomplete batches to finish).\n")
    w(f"- **{len(a6_blank)} completely unannotated** (no essential field set at all — mostly raw inventory rows never touched).\n\n")
    w(f"### A6a — Partially-annotated / started-but-incomplete ({len(a6_partial)}) — PRIORITY\n\n")
    w("| Batch Name | Missing essential fields |\n|---|---|\n")
    for b, miss in sorted(a6_partial):
        w(f"| {b} | {', '.join(miss)} |\n")
    w(f"\n### A6b — Completely unannotated ({len(a6_blank)}) — likely raw inventory\n\n")
    w("<details><summary>Expand full list</summary>\n\n")
    w("| Batch Name | Missing essential fields |\n|---|---|\n")
    for b, miss in sorted(a6_blank):
        w(f"| {b} | {', '.join(miss)} |\n")
    w("\n</details>\n\n---\n\n")

    w("## A4 — Other conditions that silently route batches out of cohorts\n\n")
    w(f"### Non-canonical On-Target values (neither Unmodified/On-target/Off-target/blank) — **{len(bad_ot)}**\n\n")
    for b, v in bad_ot:
        w(f"- {b}: `{v}`\n")
    w(f"\n### On-Target casing/whitespace mismatches — casing **{len(ot_casing)}**, whitespace **{len(ot_ws)}**\n\n")
    for b, v in ot_casing:
        w(f"- casing: {b}: `{v}`\n")
    for b, v in ot_ws:
        w(f"- whitespace: {b}: {v}\n")
    if not ot_casing and not ot_ws:
        w("(none — all non-blank On-Target values are exact canonical strings)\n")
    w(f"\n### # Sisterless KTs non-numeric labels (route to Double-Chromosome or nowhere) — **{len(sis_nonnum)}**\n\n")
    for b, v in sis_nonnum:
        w(f"- {b}: `{v}`\n")
    w(f"\n### Polar/Lagging Chromosomes values that are not exactly Yes/No — **{len(poslag_bad)}**\n\n")
    for b, col, v in poslag_bad:
        w(f"- {b} [{col}]: `{v}`\n")
    w("\n")

a6_started = {b for b, _, started in a6 if started}
with open(os.path.join(AD, "AUDIT_missing_essential_A6.csv"), "w", newline="") as f:
    wr = csv.writer(f)
    wr.writerow(["Batch Name", "missing_fields", "started_incomplete"])
    for b, miss, started in sorted(a6):
        wr.writerow([b, "; ".join(miss), "yes" if started else "no"])

# console summary
print("A1", len(a1))
print("A2", len(a2), "mad1 of those:", sum(1 for _, m in a2 if m))
print("A3", len(a3))
print("A6", len(a6))
print("A4 bad_ot", len(bad_ot), "casing", len(ot_casing), "ws", len(ot_ws),
      "sis_nonnum", len(sis_nonnum), "poslag_bad", len(poslag_bad))
print("A1 truly-in-violin (non-drug):", sum(1 for x in a1 if not x[4]))
print("--- A1 sample ---")
for x in sorted(a1)[:10]: print(x[0], x[1], 'drug' if x[4] else '')
print("--- A3 sample ---")
for x in sorted(a3)[:10]: print(x[0], x[2])
print("--- A6 sample ---")
for x in sorted(a6)[:12]: print(x[0], '|', ', '.join(x[1]))
print("--- A6 missing-field frequency ---")
from collections import Counter
c=Counter()
for _,miss,_s in a6:
    for m in miss: c[m]+=1
for k,v in c.most_common(): print(' ',k,v)
print("--- bad_ot ---", bad_ot)
print("--- sis_nonnum ---", sis_nonnum[:10])
print("--- poslag_bad ---", poslag_bad)
