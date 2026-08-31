#!/usr/bin/env python3
"""Retype grp1 in 20250402 ptk_yfpcdc20_2 from `lagging` to `paired` (user 2026-07-29).

WHY: the master says Lagging Chromosomes = No for this cell and the user confirms that flag is
CORRECT - so grp1 was never a lagging kinetochore. It runs f24-125 alongside polar grp4 at ~2-3 um
throughout (they coexist on 60 frames), which is plate-kinetochore behaviour, not a lagging
chromosome appearing at anaphase. User: "'lagging' grp1 is likely a paired, not lagging,
kinetochore... lagging designation as 'no' is still correct" -> "so change the label to paired".

grp stays 1: this is a relabel, not a track join. Whether grp1 is the SISTER of paired grp3 is a
separate question for KT_SISTERS_20260723.csv and is left alone here. Measured separations for that
decision (2026-07-29): grp1 vs grp3 median 2.53 um (IQR 2.29-2.98, 46 shared frames); grp1 vs grp4
2.60 um; grp3 vs grp4 5.49 um.

METHOD: same as _scratch/kt_notes_20260727/apply_edits.py - rewrite the notes triple in memory,
back up, temp file, verify by re-read, atomic swap. dataops.apply_edits cannot be used because R6
forbids replacing a notes column and `kttype` lives inside it; leaving kttype stale would make the
8811 group legend (make_annotation_html.py:786) disagree with the label column.

Geometry, frames, ids and t_sec are never touched.

  python3 retype_grp1_paired_20260729.py            # dry run
  python3 retype_grp1_paired_20260729.py --apply
"""
import csv, os, sys, shutil, time

csv.field_size_limit(10 ** 9)
SRC = "/Volumes/4 MB/annotations/kt_outlines.csv"
BATCH = "20250402 ptk_yfpcdc20_2"
FROM_LABEL, GRP, TO_LABEL = "lagging", "1", "paired"
APPLY = "--apply" in sys.argv


def parse(n):
    d = {}
    for kv in (n or "").split(";"):
        if ":" in kv:
            k, v = kv.split(":", 1)
            d[k.strip()] = v.strip()
    return d


rows = list(csv.DictReader(open(SRC, newline="")))
hdr = list(rows[0].keys())
targets = [r for r in rows
           if r["batch"].strip() == BATCH
           and (r.get("label") or "").strip() == FROM_LABEL
           and parse(r.get("notes")).get("grp") == GRP]
if not targets:
    sys.exit("nothing to do")

# guard: grp1 must not collide with an existing paired grp1 in this cell
clash = [r for r in rows if r["batch"].strip() == BATCH
         and (r.get("label") or "").strip() == TO_LABEL
         and parse(r.get("notes")).get("grp") == GRP]
if clash:
    sys.exit("REFUSED: %s grp%s already exists in %s (%d rows)" % (TO_LABEL, GRP, BATCH, len(clash)))

fr = sorted(int(r["frame"]) for r in targets)
print("%s: %d rows f%d-%d  %s grp%s -> %s grp%s"
      % (BATCH, len(targets), fr[0], fr[-1], FROM_LABEL, GRP, TO_LABEL, GRP))

geom_before = {(r["batch"], r["frame"], r["points"]) for r in rows}
for r in targets:
    p = parse(r.get("notes"))
    r["notes"] = "grp:%s;kttype:%s;trace:%s" % (GRP, TO_LABEL, p.get("trace", "0"))
    r["label"] = TO_LABEL

if not APPLY:
    for r in targets[:3]:
        print("   DRY id=%s frame=%s -> label=%s notes=%s" % (r["id"], r["frame"], r["label"], r["notes"]))
    print("   (%d rows, nothing written)\n\nDRY RUN - re-run with --apply." % len(targets))
    sys.exit(0)

stamp = time.strftime("%Y%m%d_%H%M%S")
bak = "%s.%s_pre_retype_grp1.bak" % (SRC, stamp)
shutil.copy2(SRC, bak)
tmp = SRC + ".tmp"
with open(tmp, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=hdr)
    w.writeheader(); w.writerows(rows)
os.replace(tmp, SRC)

chk = list(csv.DictReader(open(SRC, newline="")))
if len(chk) != len(rows):
    shutil.copy2(bak, SRC); sys.exit("ROW COUNT CHANGED - restored")
if {(r["batch"], r["frame"], r["points"]) for r in chk} != geom_before:
    shutil.copy2(bak, SRC); sys.exit("GEOMETRY CHANGED - restored")
now = [r for r in chk if r["batch"].strip() == BATCH
       and (r.get("label") or "").strip() == TO_LABEL
       and parse(r.get("notes")).get("grp") == GRP]
still = [r for r in chk if r["batch"].strip() == BATCH
         and (r.get("label") or "").strip() == FROM_LABEL]
if len(now) != len(targets) or still:
    shutil.copy2(bak, SRC); sys.exit("RETYPE DID NOT PERSIST - restored")
print("   APPLIED %d rows -> %s grp%s; 0 %s rows left in the cell" % (len(now), TO_LABEL, GRP, FROM_LABEL))
print("   geometry identical, row count identical, backup %s" % os.path.basename(bak))
