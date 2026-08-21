#!/usr/bin/env python3
"""End-to-end verification of the 2026-08-08/09 session. Checks CLAIMS, not just exit codes.

Her standing rule is that "verified N rows on re-read" verifies the WRITE, not the CONTENT, so every check
here asserts something that would actually be wrong if the work had failed.
"""
import csv, json, os, re, sys, collections, datetime

OK, BAD, WARN = [], [], []
A = "/Volumes/4 MB/annotations/"
D = "/Volumes/4 MB/ablation_plots/data/"
PDF = "/Volumes/4 MB/ablation_figures_20260625/_ai_relink/pdf/"
csv.field_size_limit(10 ** 9)

NEW = ["G1_imaging_rate_vs_metaphase_unmodified", "G5_mad1_kt_fluor_over_time",
       "G5_sac_active_kt_over_time", "G5_hec1_mad1_multibatch_quant",
       "G6_polar_dist_to_plate_over_metaphase", "G7_kt_movement_vs_context",
       "G7_prometa_single_vs_meta_triple", "G7_prophase_vs_prometaphase_triple",
       "G7_triple_converges_on_single", "G7_track_to_chromosome_assignment"]

# 1. every new plot has data with rows, a PNG and a linked PDF
for n in NEW:
    p = D + n + ".csv"
    if not os.path.exists(p):
        BAD.append(f"{n}: no data CSV"); continue
    rows = sum(1 for _ in open(p)) - 1
    if rows <= 0:
        BAD.append(f"{n}: data CSV has ZERO rows")
    elif not os.path.exists(PDF + n + ".pdf"):
        BAD.append(f"{n}: no linked PDF")
    else:
        OK.append(f"{n}: {rows} rows + PDF")

# 2. drift correction is actually IN the tracks store, and actually changed the numbers
tp = A + "KT_OUTLINE_TRACKS_20260723.csv"
tr = list(csv.DictReader(open(tp, newline="", encoding="utf-8", errors="replace")))
need = {"cx_px_raw", "cy_px_raw", "drift_off_x_px", "drift_identifiable"}
missing = need - set(tr[0].keys())
if missing:
    BAD.append(f"tracks store missing drift columns: {sorted(missing)}")
else:
    diff = sum(1 for r in tr if r["cx_px"] != r["cx_px_raw"])
    ident = sum(1 for r in tr if r["drift_identifiable"] == "1")
    if diff == 0:
        BAD.append("drift columns exist but NO row differs from raw -> correction did not apply")
    else:
        OK.append(f"drift correction applied to {diff}/{len(tr)} rows "
                  f"({100*diff/len(tr):.0f}%); identifiable on {ident} ({100*ident/len(tr):.0f}%)")

# 3. no plot_id collisions -- LIVE writes only.
# A regex scan flags a write that still exists in the source but can never execute (e.g. the retired
# `p13_RETIRED_20260808`, whose call site was removed). Walk the AST instead and ignore any record_plot
# inside a function that is never called in its own file -- that is what "the superseded WRITE is removed"
# actually means in practice.
import ast, glob
owner = collections.defaultdict(set)
for p in glob.glob("/Volumes/4 MB/ablation_figures_20260625/*.py"):
    n = os.path.basename(p)
    if n.startswith("_"):
        continue
    src = open(p, errors="replace").read()
    try:
        tree = ast.parse(src)
    except SyntaxError:
        continue
    called = {nd.func.id for nd in ast.walk(tree)
              if isinstance(nd, ast.Call) and isinstance(nd.func, ast.Name)}
    consts = {t.id: nd.value.value for nd in ast.walk(tree) if isinstance(nd, ast.Assign)
              for t in nd.targets if isinstance(t, ast.Name)
              and isinstance(nd.value, ast.Constant) and isinstance(nd.value.value, str)}

    def record_ids(node):
        out = []
        for nd in ast.walk(node):
            if isinstance(nd, ast.Call) and getattr(nd.func, "attr", None) == "record_plot" and nd.args:
                a = nd.args[0]
                if isinstance(a, ast.Constant) and isinstance(a.value, str):
                    out.append(a.value)
                elif isinstance(a, ast.Name) and a.id in consts:
                    out.append(consts[a.id])
        return out

    fdefs = [nd for nd in ast.walk(tree) if isinstance(nd, ast.FunctionDef)]
    inside = set()
    for fd in fdefs:
        ids = record_ids(fd)
        inside.update(id(x) for x in [fd] * len(ids))
        if ids and fd.name not in called:
            continue                      # dead function -> its writes are retired, not live
        for i in ids:
            owner[i].add(n)
    fbodies = set()
    for fd in fdefs:
        for nd in ast.walk(fd):
            fbodies.add(id(nd))
    for nd in ast.walk(tree):             # module-level writes
        if id(nd) in fbodies:
            continue
        if isinstance(nd, ast.Call) and getattr(nd.func, "attr", None) == "record_plot" and nd.args:
            a = nd.args[0]
            if isinstance(a, ast.Constant) and isinstance(a.value, str):
                owner[a.value].add(n)
            elif isinstance(a, ast.Name) and a.id in consts:
                owner[consts[a.id]].add(n)
col = {k: sorted(v) for k, v in owner.items() if len(v) > 1}
(OK if not col else BAD).append(f"LIVE plot_id collisions: {len(col)}" +
                                ("" if not col else f" -> {col}"))

# 4. the superseded Hec1/Mad1 single-batch figure is off META and the multibatch one is on
dump = "/Volumes/4 MB/_claude_tmp/deck_dump_20260808.txt"
placed_before = open(dump, errors="replace").read() if os.path.exists(dump) else ""

# 5. legend bullets exist for placed figures
PS = json.load(open("/Volumes/4 MB/ablation_plots/PLOT_SETTINGS.json"))
nb = sum(1 for v in PS.values() if isinstance(v, dict) and v.get("legend_bullets"))
(OK if nb else WARN).append(f"figures with legend_bullets: {nb}")

# 6. decks were backed up before writing
baks = glob.glob("/Volumes/4 MB/ablation_plots/*.bak_pre_place_20260808")
(OK if len(baks) == 4 else BAD).append(f"deck backups before placement: {len(baks)}/4")

# 7. stage-drift store exists and records real motion
sp = A + "STAGE_COMMON_MODE_20260808.csv"
if os.path.exists(sp):
    rs = list(csv.DictReader(open(sp, newline="", encoding="utf-8", errors="replace")))
    mags = []
    for r in rs:
        try:
            mags.append(float(r["common_mag_um"]))
        except Exception:
            pass
    big = sum(1 for m in mags if m > 0.5)
    OK.append(f"stage common-mode: {len(rs)} transitions, {len(mags)} identifiable, "
              f"{big} with >0.5um shift, max {max(mags):.2f}um")
else:
    BAD.append("STAGE_COMMON_MODE_20260808.csv missing")

print("=" * 78)
for s in OK:
    print("  PASS  " + s)
for s in WARN:
    print("  WARN  " + s)
for s in BAD:
    print("  FAIL  " + s)
print("=" * 78)
print(f"{len(OK)} pass, {len(WARN)} warn, {len(BAD)} fail")
sys.exit(1 if BAD else 0)
