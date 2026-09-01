#!/usr/bin/env python3
"""Retype a kinetochore track's label in annotations/kt_outlines.csv (or kt_points.csv).

  python3 retype_kt_track_20260729.py --batch "<name>" --from lagging --to polar [--grp 1] [--apply]

WHY THIS EXISTS SEPARATELY FROM dataops.apply_edits: the tool stores a track's identity inside
`notes` as "grp:N;kttype:X;trace:T". dataops rule R6 forbids replacing a notes column - correct for
free text, but a retype must keep `kttype` in step with `label` or the 8811 group legend
(make_annotation_html.py:786) shows a type the data no longer has. So this follows the method used
by _scratch/kt_notes_20260727/apply_edits.py: edit in memory -> back up -> temp file -> verify by
re-read (row count AND geometry) -> atomic swap, restoring from the backup on any mismatch.

Geometry (points), frame, id and t_sec are never touched - only `label` and the kttype inside `notes`.

LABEL SEMANTICS (user 2026-07-29, worth keeping straight):
  * the outline label `polar` denotes the SISTERLESS kinetochore's identity - the same object the
    circle store often calls `sisterless`;
  * the master's `Polar Chromosomes` / `Lagging Chromosomes` columns are BEHAVIOURAL flags about
    what that chromosome did.
  A cell can therefore carry `polar` outlines while the master says Polar = No. The two are not in
  conflict and the master should not be "corrected" to match a label.
"""
import argparse, csv, os, sys, shutil, time

csv.field_size_limit(10 ** 9)
ANN = "/Volumes/4 MB/annotations"


def parse_notes(n):
    d = {}
    for kv in (n or "").split(";"):
        if ":" in kv:
            k, v = kv.split(":", 1)
            d[k.strip()] = v.strip()
    return d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--store", default="kt_outlines", choices=["kt_outlines", "kt_points"])
    ap.add_argument("--batch", required=True)
    ap.add_argument("--from", dest="src", required=True)
    ap.add_argument("--to", dest="dst", required=True)
    ap.add_argument("--grp", default=None, help="restrict to one grp; omit for every row of --from")
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()

    path = os.path.join(ANN, a.store + ".csv")
    rows = list(csv.DictReader(open(path, newline="")))
    hdr = list(rows[0].keys())

    def match(r):
        if r["batch"].strip() != a.batch:
            return False
        if (r.get("label") or "").strip() != a.src:
            return False
        return a.grp is None or parse_notes(r.get("notes")).get("grp") == a.grp

    targets = [r for r in rows if match(r)]
    if not targets:
        sys.exit("nothing to do: no %s rows%s in %s" %
                 (a.src, ("" if a.grp is None else " with grp=" + a.grp), a.batch))

    # guard: destination label+grp must not already exist in this cell (would silently merge tracks)
    if a.grp is not None:
        clash = [r for r in rows if r["batch"].strip() == a.batch
                 and (r.get("label") or "").strip() == a.dst
                 and parse_notes(r.get("notes")).get("grp") == a.grp]
        if clash:
            sys.exit("REFUSED: %s grp%s already exists in %s (%d rows) - use a join, not a retype"
                     % (a.dst, a.grp, a.batch, len(clash)))

    fr = sorted(int(float(r["frame"])) for r in targets)
    print("%s [%s]: %d rows f%d-%d   %s%s -> %s"
          % (a.batch, a.store, len(targets), fr[0], fr[-1], a.src,
             "" if a.grp is None else " grp" + a.grp, a.dst))

    geom_before = {(r["batch"], r["frame"], r.get("points", ""), r.get("x", ""), r.get("y", "")) for r in rows}
    for r in targets:
        p = parse_notes(r.get("notes"))
        if p.get("grp"):
            r["notes"] = "grp:%s;kttype:%s;trace:%s" % (p["grp"], a.dst, p.get("trace", "0"))
        r["label"] = a.dst

    if not a.apply:
        for r in targets[:3]:
            print("   DRY id=%s frame=%s -> label=%s notes=%s" % (r["id"], r["frame"], r["label"], r.get("notes")))
        print("   (%d rows, nothing written)\n\nDRY RUN - re-run with --apply." % len(targets))
        return

    stamp = time.strftime("%Y%m%d_%H%M%S")
    bak = "%s.%s_pre_retype.bak" % (path, stamp)
    shutil.copy2(path, bak)
    tmp = path + ".tmp"
    with open(tmp, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=hdr)
        w.writeheader(); w.writerows(rows)
    os.replace(tmp, path)

    chk = list(csv.DictReader(open(path, newline="")))
    if len(chk) != len(rows):
        shutil.copy2(bak, path); sys.exit("ROW COUNT CHANGED - restored from %s" % bak)
    geom_after = {(r["batch"], r["frame"], r.get("points", ""), r.get("x", ""), r.get("y", "")) for r in chk}
    if geom_after != geom_before:
        shutil.copy2(bak, path); sys.exit("GEOMETRY CHANGED - restored from %s" % bak)
    left = [r for r in chk if match(r)]
    if left:
        shutil.copy2(bak, path); sys.exit("RETYPE DID NOT PERSIST (%d rows remain) - restored" % len(left))
    print("   APPLIED %d rows -> %s; geometry identical, row count identical" % (len(targets), a.dst))
    print("   backup %s" % os.path.basename(bak))


if __name__ == "__main__":
    main()
