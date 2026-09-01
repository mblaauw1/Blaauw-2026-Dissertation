#!/usr/bin/env python3
"""Apply her per-cell LAGGING COUNTS for the 46 multi-sisterless cells served on port 8817 (2026-07-30).

This is the annotation gap that blocked G1_shape_rate_vs_lagging_fraction: the master carried only a
CELL-LEVEL `Lagging Chromosomes` yes/no, so for 2-/3-sisterless cells a *fraction* could not be computed.
She scored the 46 cells and gave the counts in the order the batches appear on 8817.

ORDER VERIFICATION - the mapping was checked before anything was written, not assumed:
  * the order comes from the SERVED index.html itself (its "name" and data-batch orders agree, n=46),
    not from re-running the builder, so it is what she actually clicked through;
  * her own note "batch 46 is 20260417 ptk2 eyfp cdc20 ablation_19" matches position 46;
  * all FOUR of her flag notes independently corroborate the alignment against the master's current values:
      #7  20250904 triple_ablation_22      "change lagging flag from yes to no"  -> master Lagging = 'Yes'
      #10 20250909 triple_ablation_collagen_9 "change polar flag to 'yes'"       -> master Polar   = 'no'
      #15 20250918 triple_ablation_29      "no lagging flag currently - set to no" -> master Lagging = ''
      #34 20251104 ablations_3             "change lagging flag to no"           -> master Lagging = 'Yes'
  * #43 20260417 ptk2 eyfp cdc20 ablation_1, which she left blank as "actually an IF", is confirmed an IF:
    the output holds 405_DAPI / 561_mCherry / 640_Cy5 channels, not a cdc20 timelapse. Its count is left
    EMPTY and the Cell-Type mislabel is reported, not silently corrected.

STORAGE. A new master column `# Lagging Chromosomes` is APPENDED at the end of the two-row header, parallel
to `# Sisterless KTs`. Appending rather than inserting after `Lagging Chromosomes` is deliberate: inserting
would shift every later column index and any consumer reading positionally would break silently.

  python3 apply_lagging_counts_20260730.py --check   # report, write nothing
  python3 apply_lagging_counts_20260730.py           # back up, apply, verify by re-read
"""
import csv
import json
import os
import shutil
import sys
import time

ROOT = "/Volumes/4 MB"
MASTER = os.path.join(ROOT, "ABLATION_MASTER.csv")
ORDER = os.path.join(ROOT, "_deck_jsx_inputs/lagging8817_order.json")
NEWCOL = "# Lagging Chromosomes"
CHECK = "--check" in sys.argv

# her 46 values, in 8817 order. None = left blank.
COUNTS = [1, 0, 1, 1, 3, 0, 0, 1, 0, 2, 1, 2, 0, 2, 0, 0, 1, 2, 0, 0, 0, 0, 3, 1, 1, 2, 1, 0, 2, 1,
          1, 1, 0, 0, 2, 0, 1, 1, 2, 0, 1, 1, None, 1, 1, 1]

# flag edits she asked for, keyed by her 1-based position
FLAGS = {
    7:  [("Lagging Chromosomes", "No")],
    10: [("Polar Chromosomes", "Yes")],
    15: [("Lagging Chromosomes", "No")],
    34: [("Lagging Chromosomes", "No")],
}
# observations to preserve verbatim in Lagging Comments
NOTES = {
    33: "no lagging with visible kinetochores but there appears to be a chromatid from the "
        "kinetochoreless side of a chromosome that floats in the midzone",
    34: "no lagging with visible kinetochores but there appears to be a chromatid from the "
        "kinetochoreless side of a chromosome that floats in the midzone",
    36: "no lagging stretching seen but also division was crazy unhealthy",
    43: "left blank on the 8817 pass because this batch is actually an IF, not a cdc20 timelapse",
}
STAMP = "[8817 lagging-count pass 2026-07-30]"


def main():
    order = json.load(open(ORDER))
    assert len(order) == 46 == len(COUNTS), f"order {len(order)} vs counts {len(COUNTS)}"
    assert order[45] == "20260417 ptk2 eyfp cdc20 ablation_19", "her position-46 check failed"

    rows = list(csv.reader(open(MASTER)))
    grouphdr, hdr = rows[0], rows[1]
    if NEWCOL in hdr:
        ci = hdr.index(NEWCOL)
        print(f"{NEWCOL} already present at {ci}")
    else:
        ci = len(hdr)
        print(f"appending {NEWCOL} at column {ci}")
    name_i = hdr.index("Batch Name")
    idx = {r[name_i].strip(): n for n, r in enumerate(rows[2:], start=2) if len(r) > name_i}

    edits, missing = [], []
    for pos, (batch, val) in enumerate(zip(order, COUNTS), start=1):
        n = idx.get(batch)
        if n is None:
            missing.append((pos, batch)); continue
        cur = rows[n][ci] if ci < len(rows[n]) else ""
        edits.append((pos, batch, n, "count", cur, "" if val is None else str(val)))
        for col, newv in FLAGS.get(pos, []):
            k = hdr.index(col)
            edits.append((pos, batch, n, col, rows[n][k] if k < len(rows[n]) else "", newv))
        if pos in NOTES:
            k = hdr.index("Lagging Comments")
            old = rows[n][k] if k < len(rows[n]) else ""
            add = f"{STAMP} {NOTES[pos]}"
            if STAMP not in old:
                edits.append((pos, batch, n, "Lagging Comments", old[:40], (old + " || " + add).strip(" |")))

    print(f"\n{len(edits)} cell edits across {len(order)-len(missing)} batches; missing {missing}")
    for pos, b, n, col, old, new in edits:
        if col != "count" or old != new:
            print(f"  #{pos:2d} {b[:44]:46s} {col:20s} '{old}' -> '{new}'")
    if CHECK:
        print("\n--check: nothing written")
        return

    bak = MASTER + time.strftime(".%Y%m%d_%H%M%S_pre_lagging_counts.bak")
    shutil.copy2(MASTER, bak)
    print(f"\nbackup -> {bak}")

    if NEWCOL not in hdr:
        grouphdr.append(grouphdr[hdr.index("Lagging Chromosomes")] if len(grouphdr) > hdr.index("Lagging Chromosomes") else "UserInput")
        hdr.append(NEWCOL)
    width = len(hdr)
    for r in rows[2:]:
        while len(r) < width:
            r.append("")
    for pos, b, n, col, old, new in edits:
        k = ci if col == "count" else hdr.index(col)
        rows[n][k] = new

    tmp = MASTER + ".tmp"
    with open(tmp, "w", newline="") as f:
        csv.writer(f).writerows(rows)
    os.replace(tmp, MASTER)

    # verify by RE-READING the file, not by trusting the write
    back = list(csv.reader(open(MASTER)))
    h2 = back[1]; c2 = h2.index(NEWCOL); n2 = h2.index("Batch Name")
    got = {r[n2].strip(): r[c2] for r in back[2:] if len(r) > c2}
    bad = [(b, got.get(b), v) for b, v in zip(order, COUNTS)
           if got.get(b) != ("" if v is None else str(v))]
    print(f"re-read: {NEWCOL} at col {c2}; mismatches {len(bad)} {bad[:4]}")
    filled = sum(1 for b in order if (got.get(b) or "").strip() != "")
    print(f"counts written for {filled} of 46 batches (1 deliberately blank - the IF)")


if __name__ == "__main__":
    main()
