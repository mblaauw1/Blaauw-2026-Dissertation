#!/usr/bin/env python3
"""Re-file the 4 annotation rows keyed to a batch name that does not exist (checks.py [R1]).

THE ROWS: 3 in `CHROMOSOME_MASTER.csv` (ids 187/188/189) and 1 in `SISTERLESS_PLATE_JOIN_TIMES.csv`
(id 62), all keyed to `20260417 ptk2 eyfp cdc20 IF stained slide 2 pos0_2` -- a name that is in neither
the master nor on disk.

THIS IS A RE-LABEL, NOT A MERGE.  The destination holds ZERO rows in both files, so nothing is combined,
nothing is overwritten, and no value has to be reconciled.

WHO OWNS THEM -- evidence, not inference:
  1. the master row for `20260417 ptk2 eyfp cdc20 ablation_1` ALREADY carries
     `sisterless_plate_join_ids = 62` -- the master itself points at the orphan row from that cell;
  2. that cell is `# Sisterless KTs = 3`, matching the orphan row's `n_sisterless = 3`;
  3. it is a TIMELAPSE, so it can carry a congression time of 0:24:05 and a plate-join of "anaphase";
     the only same-name alternative, `...IF stained slide 2 pos0_1`, is a Z-STACK (a fixed image) and
     cannot have either;
  4. `IF_ABLATION_PAIRING_20260627.csv` pairs `_pos0_2` to that same ablation batch at HIGH confidence
     (36.4 um, vs 150.7 um for `_pos0_1`).

Also mirrors `chromosome_annotation_ids` into the master so the id-key convention (§3c) resolves both ways.
Run with --apply. Backs up, writes atomically, verifies by re-reading.
"""
import csv, os, sys, shutil, datetime

ROOT = "/Volumes/4 MB"
OLD = "20260417 ptk2 eyfp cdc20 IF stained slide 2 pos0_2"
NEW = "20260417 ptk2 eyfp cdc20 ablation_1"
APPLY = "--apply" in sys.argv
csv.field_size_limit(10 ** 9)

moved = {}
for name in ("CHROMOSOME_MASTER", "SISTERLESS_PLATE_JOIN_TIMES"):
    p = f"{ROOT}/annotations/{name}.csv"
    rows = list(csv.DictReader(open(p)))
    hdr = list(rows[0].keys())
    src = [r for r in rows if r.get("batch", "").strip() == OLD]
    dst = [r for r in rows if r.get("batch", "").strip() == NEW]
    print(f"{name}: rows on the orphan name = {len(src)}   rows already on the destination = {len(dst)}")
    if dst:
        print("   DESTINATION IS NOT EMPTY -- stopping, this would be a merge and needs a human")
        sys.exit(1)
    for r in src:
        r["batch"] = NEW
    moved[name] = [r.get("id", "") for r in src]
    if APPLY and src:
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        shutil.copy(p, f"{ROOT}/_master_backups/{name}_pre_r1_refile_{ts}.csv")
        tmp = p + ".tmp"
        with open(tmp, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=hdr); w.writeheader(); w.writerows(rows)
        os.replace(tmp, p)
        chk = list(csv.DictReader(open(p)))
        n = sum(1 for r in chk if r.get("batch", "").strip() == NEW)
        print(f"   WROTE {p} -- {n} rows now on {NEW}")

if APPLY:
    MP = f"{ROOT}/ABLATION_MASTER.csv"
    allr = list(csv.reader(open(MP)))
    hi = next(i for i, r in enumerate(allr) if r and r[0].strip() == "Batch Name")
    hdr = [c.strip() for c in allr[hi]]
    bi = hdr.index("Batch Name")
    ci = hdr.index("chromosome_annotation_ids") if "chromosome_annotation_ids" in hdr else None
    si = hdr.index("sisterless_plate_join_ids") if "sisterless_plate_join_ids" in hdr else None
    n = 0
    for r in allr[hi + 1:]:
        if not r or len(r) <= bi or r[bi].strip() != NEW:
            continue
        while len(r) < len(hdr):
            r.append("")
        if ci is not None and moved.get("CHROMOSOME_MASTER"):
            v = ",".join(moved["CHROMOSOME_MASTER"])
            if r[ci] != v:
                r[ci] = v; n += 1
        if si is not None and moved.get("SISTERLESS_PLATE_JOIN_TIMES"):
            v = ",".join(moved["SISTERLESS_PLATE_JOIN_TIMES"])
            if r[si] != v:
                r[si] = v; n += 1
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    shutil.copy(MP, f"{ROOT}/_master_backups/ABLATION_MASTER_pre_r1_refile_{ts}.csv")
    tmp = MP + ".tmp"
    with open(tmp, "w", newline="") as f:
        csv.writer(f).writerows(allr)
    os.replace(tmp, MP)
    print(f"master id-pointer cells updated: {n}")
else:
    print("(dry run -- pass --apply to write)")
