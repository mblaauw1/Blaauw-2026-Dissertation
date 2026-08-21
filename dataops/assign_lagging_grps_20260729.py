#!/usr/bin/env python3
"""Give every grp-less LAGGING outline row an explicit grp, so the grouping is stated in
the data instead of being inferred (user 2026-07-29).

WHY THIS IS SAFE / WHAT THE RULE IS
  kt_outlines has one row per TRACE. `notes` carries "grp:N;kttype:<label>;trace:M":
  grp identifies ONE kinetochore across frames, trace distinguishes several polygons of
  that kinetochore on ONE frame (NOTES.md:249). 158 lagging rows in 7 batches carry an
  EMPTY notes field, so their kinetochore identity was only implicit.

  User 2026-07-29: "within one batch, these lagging polygons mark just one kinetochore on
  each frame (indicating fracture if there are multiple polygons)". So each of these
  batches has exactly ONE lagging kinetochore and every grp-less lagging row in that batch
  belongs to it -> one grp per batch. Verified: NO batch mixes grp'd and un-grp'd lagging
  rows, so this can never split an existing group.

  SCOPE IS LAGGING ONLY. The 848 grp-less POLAR rows are deliberately untouched - the user
  cautioned that the one-KT-per-frame rule may not hold for other labels.

grp NUMBER: the next free integer above the highest grp already used in that batch by ANY
  label, so the new grp cannot collide with an existing kinetochore's id.
trace NUMBER: 0,1,2... within (batch, frame), ordered by row id - matching the tool's own
  convention (existing rows read "grp:18;kttype:lagging;trace:1").

Writes through dataops.apply_edits: backup -> atomic replace -> VERIFY BY RE-READ ->
restore on any mismatch -> audit log. kt_outlines has 0 duplicate ids (checked), so `id`
is a safe key here - unlike kt_points/meta_plates, where the live S2 bug forces (id,frame).

  python3 assign_lagging_grps_20260729.py           # dry run, writes nothing
  python3 assign_lagging_grps_20260729.py --apply
"""
import csv, os, re, sys, collections

sys.path.insert(0, "/Volumes/4 MB/dataops")
import dataops

csv.field_size_limit(10 ** 9)
SRC = "/Volumes/4 MB/annotations/kt_outlines.csv"
APPLY = "--apply" in sys.argv


def grp_of(row):
    m = re.search(r"grp:([^;]*)", row.get("notes", "") or "")
    g = (m.group(1).strip() if m else "")
    return g or None


rows = list(csv.DictReader(open(SRC)))
lagging = [r for r in rows if (r.get("label") or "").strip() == "lagging"]
targets = [r for r in lagging if grp_of(r) is None]

# guard: refuse if any batch mixes grp'd and un-grp'd lagging rows (would mean the
# one-kinetochore-per-batch premise does not hold there)
mix = collections.defaultdict(set)
for r in lagging:
    mix[r["batch"]].add(grp_of(r) is not None)
mixed = sorted(b for b, v in mix.items() if len(v) > 1)
if mixed:
    sys.exit("REFUSED: these batches mix grp'd and un-grp'd lagging rows: %s" % mixed)

# guard: id must be unique or the key is unsafe
ids = collections.Counter(r["id"] for r in rows)
dup = [i for i, n in ids.items() if n > 1]
if dup:
    sys.exit("REFUSED: %d duplicate ids in kt_outlines - re-key on (id,frame) first" % len(dup))

# next free grp per batch, across ALL labels in that batch
next_grp = {}
for b in sorted({r["batch"] for r in targets}):
    used = []
    for r in rows:
        if r["batch"] != b:
            continue
        g = grp_of(r)
        if g and g.isdigit():
            used.append(int(g))
    next_grp[b] = (max(used) + 1) if used else 1

# trace index within (batch, frame), ordered by id
by_frame = collections.defaultdict(list)
for r in targets:
    by_frame[(r["batch"], r["frame"])].append(r)

edits = {}
summary = collections.defaultdict(lambda: [0, 0])   # batch -> [rows, frames_with_fracture]
for (b, fr), members in by_frame.items():
    members.sort(key=lambda r: int(r["id"]))
    if len(members) > 1:
        summary[b][1] += 1
    for t, r in enumerate(members):
        note = "grp:%d;kttype:lagging;trace:%d" % (next_grp[b], t)
        edits[(r["id"],)] = {"notes": note}
        summary[b][0] += 1

print("grp-less lagging rows: %d in %d batches" % (len(targets), len(next_grp)))
for b in sorted(summary):
    n, frac = summary[b]
    print("  %-50s -> grp %-3d (%3d rows, %2d frames with >1 polygon = fracture)"
          % (b, next_grp[b], n, frac))
print()

changes = dataops.apply_edits(
    SRC, ["id"], edits,
    tag="assign_lagging_grps_20260729",
    reason=("Assign an explicit grp to the 158 grp-less LAGGING outline rows. User "
            "2026-07-29: within one batch these polygons mark ONE kinetochore per frame "
            "(multiple polygons on a frame = a kinetochore fractured under anaphase "
            "force), so one grp per batch. grp chosen above the batch's existing max so "
            "it cannot collide. Polar rows deliberately untouched."),
    dry_run=not APPLY)

if not APPLY:
    print("\nDRY RUN — nothing written. Re-run with --apply.")
