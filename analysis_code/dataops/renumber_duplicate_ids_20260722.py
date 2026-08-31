#!/usr/bin/env python3
"""Renumber duplicate ids in the annotation stores (check S2) and re-mirror the master's *_ids columns.

Do this only AFTER the allocator fix in serve_annotation._autosave_replace_batch, otherwise the
duplicates come straight back (they grew kt_points 36->119 during a single afternoon of annotation).

Rule: the FIRST batch to use an id keeps it; every later batch's rows with that id are renumbered
above the store's live maximum.  Geometry is never touched.  The master's <type>_ids pointer column
is rewritten from the renumbered rows so both directions still resolve (§3c id-key convention).
"""
import csv, os, sys, shutil, datetime
from collections import defaultdict

ROOT = "/Volumes/4 MB"
ANN = f"{ROOT}/annotations"
APPLY = "--apply" in sys.argv
csv.field_size_limit(10**9)

STORES = {"kt_points": "kt_point_ids", "meta_plates": "meta_plate_ids",
          "cell_outlines": "cell_outline_ids", "chromo_lines": "chromo_line_ids"}

remap = {}      # store -> batch -> {old_id: new_id}
summary = []
for st in STORES:
    p = f"{ANN}/{st}.csv"
    rows = list(csv.DictReader(open(p)))
    if not rows:
        continue
    hdr = list(rows[0].keys())
    owner = {}                       # id -> the batch that keeps it
    mx = max([int(r["id"]) for r in rows if str(r.get("id", "")).strip().isdigit()] + [0])
    changed = 0
    rm = defaultdict(dict)
    for r in rows:
        v = str(r.get("id", "")).strip()
        b = r.get("batch", "")
        if not v.isdigit():
            mx += 1; r["id"] = str(mx); changed += 1; continue
        if v not in owner:
            owner[v] = b; continue
        if owner[v] == b:
            continue                 # same batch reusing an id across frames is legitimate
        if v in rm[b]:
            r["id"] = rm[b][v]
        else:
            mx += 1
            rm[b][v] = str(mx)
            r["id"] = str(mx)
        changed += 1
    dupes_left = len({i for i, c in
                      __import__("collections").Counter(
                          (r["batch"], r["id"]) for r in rows).items()})
    summary.append((st, len(rows), changed))
    remap[st] = rm
    if APPLY and changed:
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        shutil.copy(p, f"{ROOT}/_master_backups/{st}_pre_id_renumber_{ts}.csv")
        tmp = p + ".tmp"
        with open(tmp, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=hdr); w.writeheader(); w.writerows(rows)
        os.replace(tmp, p)

print(f"{'store':16s} {'rows':>7s} {'ids_renumbered':>15s}")
for s in summary:
    print(f"{s[0]:16s} {s[1]:7d} {s[2]:15d}")

# ---- re-mirror the master's *_ids columns from the renumbered stores ----
if APPLY:
    MP = f"{ROOT}/ABLATION_MASTER.csv"
    allrows = list(csv.reader(open(MP)))
    hi = next(i for i, r in enumerate(allrows) if r and r[0].strip() == "Batch Name")
    hdr = [c.strip() for c in allrows[hi]]
    bi = hdr.index("Batch Name")
    ids = {}
    for st, col in STORES.items():
        if col not in hdr:
            continue
        ci = hdr.index(col)
        per = defaultdict(list)
        for r in csv.DictReader(open(f"{ANN}/{st}.csv")):
            if r.get("batch"):
                per[r["batch"]].append(str(r["id"]))
        ids[ci] = per
    n = 0
    for r in allrows[hi + 1:]:
        if not r or len(r) <= bi:
            continue
        b = r[bi].strip()
        for ci, per in ids.items():
            if b in per and len(r) > ci:
                v = ",".join(dict.fromkeys(per[b]))
                if r[ci] != v:
                    r[ci] = v; n += 1
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    shutil.copy(MP, f"{ROOT}/_master_backups/ABLATION_MASTER_pre_id_remirror_{ts}.csv")
    tmp = MP + ".tmp"
    with open(tmp, "w", newline="") as f:
        csv.writer(f).writerows(allrows)
    os.replace(tmp, MP)
    print(f"master *_ids cells rewritten: {n}")
elif not APPLY:
    print("(dry run -- pass --apply to write)")
