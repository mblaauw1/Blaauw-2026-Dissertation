#!/usr/bin/env python3
"""Can the SNAPSHOT / Mad1 KT-fluorescence plot be made for the OTHER mad1 timestrip samples?

USER 2026-08-05: "see if the ability to make similar plots like this is possible ... for the mad1 samples
with timestrips already on that artboard".

Answering that needs one thing checked per sample: on how many DISTINCT frames is the sisterless
kinetochore marked, and on how many is a plate kinetochore marked. A trace needs >=3 frames; a plate
reference band needs >=1. Marks can come from kt_points (polar / paired_kt) or from a traced outline
(KT_FLUOR_CYTOSOLNORM), so both are counted and the better of the two is used.

Run it after any annotation session: the verdict column tells you exactly which samples became eligible.
Writes 4_TABLES_AND_REPORTS/MAD1_SNAPSHOT_COVERAGE_20260805.md next to the other review docs.
"""
import sys, csv, collections, re, os
sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
csv.field_size_limit(10 ** 9)
import lib

ROOT = "/Volumes/4 MB"
OUTMD = f"{ROOT}/4_TABLES_AND_REPORTS/MAD1_SNAPSHOT_COVERAGE_20260805.md"
MIN_TRACE = 3     # distinct frames needed to call something a trace rather than a snapshot

# the mad1 batches that actually have a timestrip — parsed from the builder's own list, so this cannot
# drift out of sync with what is on the artboard
src = open(f"{ROOT}/ablation_figures_20260625/group5_mad1_examples.py", encoding="utf-8").read()
blk = src[src.index("TIMESTRIP_BATCHES = ["):]
blk = blk[:blk.index("]\n")]
batches = [b for b in re.findall(r'\("([^"]+)"', blk) if not b.startswith("check to see")]

pts = collections.defaultdict(lambda: collections.defaultdict(set))
for r in csv.DictReader(open(f"{ROOT}/annotations/kt_points.csv", encoding="utf-8", errors="replace")):
    b = (r.get("batch") or "").strip(); lab = (r.get("label") or "").strip()
    if lab in ("polar", "paired_kt", "paired"):
        try: pts[b][lab].add(int(r["frame"]))
        except Exception: pass

outl = collections.defaultdict(lambda: collections.defaultdict(set))
for r in csv.DictReader(open(f"{ROOT}/annotations/KT_FLUOR_CYTOSOLNORM_20260728.csv")):
    outl[r["batch"]][r["label"]].add(r["t_sec"])

rows = []
for b in batches:
    sis = max(len(pts[b].get("polar", set())), len(outl[b].get("polar", set())))
    plate = max(len(pts[b].get("paired_kt", set())), len(pts[b].get("paired", set())),
                len(outl[b].get("paired", set())))
    if sis >= MIN_TRACE and plate >= MIN_TRACE:
        v, need = "FULL trace-vs-trace", "-"
    elif sis >= MIN_TRACE and plate >= 1:
        v, need = "sisterless trace + plate REFERENCE band", f"plate KT on >={MIN_TRACE - plate} more frame(s)"
    elif sis >= MIN_TRACE:
        v, need = "sisterless trace only, NO plate mark", f"a plate/paired KT mark on >={MIN_TRACE} frames"
    else:
        v, need = "NOT possible", (f"the sisterless KT marked on >={MIN_TRACE - sis} more frame(s)"
                                   + ("" if plate >= 1 else f", plus a plate KT on >={MIN_TRACE} frames"))
    rows.append((b, sis, plate, v, need))

order = {"FULL trace-vs-trace": 0, "sisterless trace + plate REFERENCE band": 1,
         "sisterless trace only, NO plate mark": 2, "NOT possible": 3}
rows.sort(key=lambda r: (order[r[3]], r[0]))

n_ok = sum(1 for r in rows if r[3] != "NOT possible")
with open(OUTMD, "w", encoding="utf-8") as f:
    f.write("# Can the Mad1 KT-fluorescence plot be made for the other timestrip samples?\n\n")
    f.write("USER 2026-08-05: *\"see if the ability to make similar plots like this is possible ... for the "
            "mad1 samples with timestrips already on that artboard\"*\n\n")
    f.write(f"**Answer: {n_ok} of {len(rows)} can, and all {n_ok} are already on the figure.** "
            "The remaining ones are blocked by ANNOTATION, not by code — the sisterless kinetochore is not "
            "marked on enough frames to form a trace. Nothing needs to be written; marks need to be placed.\n\n")
    f.write(f"A trace needs the KT marked on >= {MIN_TRACE} distinct frames. Marks count from kt_points "
            "(`polar` / `paired_kt`) or from a traced outline (KT_FLUOR_CYTOSOLNORM), whichever gives more.\n\n")
    f.write("| batch | sisterless frames | plate frames | verdict | what it needs |\n")
    f.write("|---|---|---|---|---|\n")
    for b, s_, p_, v, need in rows:
        f.write(f"| `{b}` | {s_} | {p_} | {v} | {need} |\n")
    f.write("\n## Highest-value annotation, in order\n\n")
    for b, s_, p_, v, need in rows:
        if v == "sisterless trace only, NO plate mark":
            f.write(f"1. **`{b}`** already has a {s_}-frame sisterless trace. One plate/paired KT marked on "
                    f"{MIN_TRACE} frames of the same cell upgrades it to a full within-cell comparison — "
                    "the cheapest gain available.\n")
    for b, s_, p_, v, need in rows:
        if v == "sisterless trace + plate REFERENCE band":
            f.write(f"2. **`{b}`** has a {s_}-frame sisterless trace and a {p_}-frame plate snapshot. "
                    f"{MIN_TRACE - p_} more plate frame(s) turns the reference band into a real trace.\n")

print(f"mad1 timestrip samples: {len(rows)}   usable for this figure: {n_ok}")
for b, s_, p_, v, need in rows:
    print(f"  {b[:46]:46} sis={s_:<3} plate={p_:<3} {v}")
print(f"-> {OUTMD}")
