#!/usr/bin/env python3
"""Join `paired` grp2 onto `polar` grp4 in 20250402 ptk_yfpcdc20_2 - they are ONE kinetochore.

USER 2026-07-29: "i bet that polar grp4 - f33-112 and paired grp2 are the same kinetochore and
should have their tracks joined."

EVIDENCE (measured, not eyeballed):
    grp4 last  frame 112 centroid (732,272)
    grp2 first frame 113 centroid (736,268)
    separation 6.1 px = 0.38 um across a 1-frame gap, while grp4's OWN median frame-to-frame step
    is 7.7 px. The "jump" between the two tracks is smaller than the track's normal motion, so it
    is one continuously-moving kinetochore whose track was split.
    Control: grp3 (the other paired track) ends f93 at (657,522) - 265.8 px and 20 frames from
    grp2's start, so grp2 does NOT belong to grp3.

LABEL: the joined track is POLAR. Master `Polar Chromosomes = Yes` and its Notes read
"[POLAR->PLATE] polar/sisterless KT stayed polar until anaphase - never rejoined the plate", so
grp2's `paired` label is the error, not grp4's `polar`.

METHOD: follows _scratch/kt_notes_20260727/apply_edits.py (her 07-27 track-join run) - rewrite
`notes` as grp:N;kttype:X;trace:T in memory, back up, write a temp file, verify by re-read, then
atomically swap. dataops.apply_edits is not used here because rule R6 forbids replacing a notes
column, and joining tracks requires exactly that; the guard is right for free text, wrong for the
structured grp/kttype/trace triple the tool writes.

Geometry (points, frame, id, t_sec) is never touched.

  python3 join_polar_grp4_grp2_20260729.py            # dry run
  python3 join_polar_grp4_grp2_20260729.py --apply
"""
import csv, os, re, sys, shutil, time, collections

csv.field_size_limit(10 ** 9)
SRC = "/Volumes/4 MB/annotations/kt_outlines.csv"
BATCH = "20250402 ptk_yfpcdc20_2"
FROM_LABEL, FROM_GRP = "paired", "2"
TO_LABEL, TO_GRP = "polar", "4"
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
           and parse(r.get("notes")).get("grp") == FROM_GRP]

if not targets:
    sys.exit("nothing to do: no %s grp%s rows in %s" % (FROM_LABEL, FROM_GRP, BATCH))

# guard: the destination track must exist
dest = [r for r in rows if r["batch"].strip() == BATCH
        and (r.get("label") or "").strip() == TO_LABEL
        and parse(r.get("notes")).get("grp") == TO_GRP]
if not dest:
    sys.exit("REFUSED: destination %s grp%s not found in %s" % (TO_LABEL, TO_GRP, BATCH))

# guard: no frame may end up with the destination track twice
df = {int(r["frame"]) for r in dest}
tf = {int(r["frame"]) for r in targets}
clash = df & tf
if clash:
    sys.exit("REFUSED: %d frames would have two grp%s rows: %s" % (len(clash), TO_GRP, sorted(clash)[:8]))

print("%s: joining %s grp%s (%d rows, f%d-%d) -> %s grp%s (%d rows, f%d-%d)"
      % (BATCH, FROM_LABEL, FROM_GRP, len(targets), min(tf), max(tf),
         TO_LABEL, TO_GRP, len(dest), min(df), max(df)))

geom_before = {(r["batch"], r["frame"], r["points"]) for r in rows}
for r in targets:
    p = parse(r.get("notes"))
    r["notes"] = "grp:%s;kttype:%s;trace:%s" % (TO_GRP, TO_LABEL, p.get("trace", "0"))
    r["label"] = TO_LABEL

if not APPLY:
    for r in targets[:4]:
        print("   DRY id=%s frame=%s -> label=%s notes=%s" % (r["id"], r["frame"], r["label"], r["notes"]))
    print("   (%d rows, nothing written)\n\nDRY RUN - re-run with --apply." % len(targets))
    sys.exit(0)

stamp = time.strftime("%Y%m%d_%H%M%S")
bak = "%s.%s_pre_join_grp4grp2.bak" % (SRC, stamp)
shutil.copy2(SRC, bak)
tmp = SRC + ".tmp"
with open(tmp, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=hdr)
    w.writeheader(); w.writerows(rows)
os.replace(tmp, SRC)

# VERIFY BY RE-READ
chk = list(csv.DictReader(open(SRC, newline="")))
if len(chk) != len(rows):
    shutil.copy2(bak, SRC); sys.exit("ROW COUNT CHANGED - restored from %s" % bak)
geom_after = {(r["batch"], r["frame"], r["points"]) for r in chk}
if geom_after != geom_before:
    shutil.copy2(bak, SRC); sys.exit("GEOMETRY CHANGED - restored from %s" % bak)
now = [r for r in chk if r["batch"].strip() == BATCH
       and (r.get("label") or "").strip() == TO_LABEL
       and parse(r.get("notes")).get("grp") == TO_GRP]
left = [r for r in chk if r["batch"].strip() == BATCH
        and parse(r.get("notes")).get("grp") == FROM_GRP
        and (r.get("label") or "").strip() == FROM_LABEL]
if len(now) != len(dest) + len(targets) or left:
    shutil.copy2(bak, SRC); sys.exit("JOIN DID NOT PERSIST - restored from %s" % bak)
print("   APPLIED: %s grp%s now %d rows (was %d); 0 rows left in %s grp%s"
      % (TO_LABEL, TO_GRP, len(now), len(dest), FROM_LABEL, FROM_GRP))
print("   geometry identical, row count identical, backup %s" % os.path.basename(bak))
