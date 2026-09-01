#!/usr/bin/env python3
"""Record HER sister determination for `20250826 test_ablation_14`, and purge the fabricated rows.

USER 2026-08-09, after reviewing the slide: "paired 1 and 2 are sisters, and paired 3 and 4 are sisters."

Her numbers are the UI's DISPLAY names, which `ktDisplayName()`/`ktGroupNumbers()` assign per TYPE in order
of FIRST FRAME -- not the stored grp. Resolved from her own traces:
    paired 1 -> grp4   (first frame 12, 18 traces)
    paired 2 -> grp5   (first frame 12, 13 traces)
    paired 3 -> grp2   (first frame 33, 14 traces)
    paired 4 -> grp19  (first frame 33, 12 traces)
=> sisters are grp4+grp5 and grp2+grp19.

WHAT WAS WRONG. The store held her stale call `grp2+grp3` (grp3 has no outlines at all, so that pair
produced nothing), AND a `grp2+grp19` pair with basis='proximity' that an earlier run of kt_sisters.py had
written. That proximity row was a GUESS -- it happened to match what she has now confirmed, but it was
never her determination and must not stand as one. Root cause: `load_manual()` reads the same file the
script writes, so successive runs accumulate rows and an auto-generated pair can masquerade as ground
truth on the next pass.

This script rewrites the batch's rows to exactly her two pairs, basis='manual', and drops everything else
for that batch. Non-destructive: backup, verify, atomic swap.
"""
import csv, os, shutil

A = "/Volumes/4 MB/annotations/"
SIS = A + "KT_SISTERS_20260723.csv"
TB = "20250826 test_ablation_14"
PAIRS = [("1", f"{TB}|paired|4", f"{TB}|paired|5"),
         ("2", f"{TB}|paired|2", f"{TB}|paired|19")]

with open(SIS, newline="", encoding="utf-8", errors="replace") as f:
    rd = csv.DictReader(f)
    FIELDS = rd.fieldnames
    rows = list(rd)

before = [r for r in rows if r.get("batch", "").strip() == TB]
print(f"rows for {TB} before: {len(before)}")
for r in before:
    print(f"   track={r.get('track_id','').split('|')[-1]:>4s} pair={r.get('sister_pair_id',''):<34s} "
          f"partner={r.get('partner_track','').split('|')[-1]:>4s} basis={r.get('basis','')!r}")

keep = [r for r in rows if r.get("batch", "").strip() != TB]

# preserve whatever measured stats the old rows carried for the pairs she confirmed
stat = {}
for r in before:
    stat[(r.get("track_id"), r.get("partner_track"))] = (
        r.get("metaphase_median_dist_um", ""), r.get("n_coframes", ""))

new = []
for spid, a, c in PAIRS:
    for t, p in ((a, c), (c, a)):
        md, nc = stat.get((t, p), ("", ""))
        row = {k: "" for k in FIELDS}
        row.update({"track_id": t, "batch": TB, "sister_pair_id": spid, "partner_track": p,
                    "metaphase_median_dist_um": md, "n_coframes": nc,
                    "basis": "manual", "n_paired_tracks_in_cell": "4"})
        new.append(row)

out = keep + new
tmp = SIS + ".tmp_fix"
with open(tmp, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=FIELDS)
    w.writeheader(); w.writerows(out)

with open(tmp, newline="", encoding="utf-8", errors="replace") as f:
    chk = list(csv.DictReader(f))
after = [r for r in chk if r.get("batch", "").strip() == TB]
ok = True
if len(chk) != len(keep) + len(new):
    print("ABORT: row count mismatch"); ok = False
if len({r["track_id"] for r in after}) != 4 or len(after) != 4:
    print(f"ABORT: expected 4 rows / 4 tracks, got {len(after)}"); ok = False
if any((r.get("basis") or "") != "manual" for r in after):
    print("ABORT: a row is not basis=manual"); ok = False
if len({r.get("batch") for r in keep} & {TB}) != 0:
    print("ABORT: old rows survived"); ok = False
if not ok:
    os.remove(tmp); raise SystemExit("verification failed — nothing written")

shutil.copy2(SIS, SIS + ".bak_pre_ts14_sisterfix_20260809")
os.replace(tmp, SIS)
print(f"\nbackup: {SIS}.bak_pre_ts14_sisterfix_20260809")
print(f"rows for {TB} after: {len(after)}")
for r in after:
    print(f"   track={r.get('track_id','').split('|')[-1]:>4s} pair={r.get('sister_pair_id',''):<3s} "
          f"partner={r.get('partner_track','').split('|')[-1]:>4s} basis={r.get('basis','')}")
print("\nNOTE: kt_sisters.py must be re-run to regenerate the per-frame k-k series from these pairs.")
