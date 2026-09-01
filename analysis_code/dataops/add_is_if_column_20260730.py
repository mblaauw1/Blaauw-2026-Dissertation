#!/usr/bin/env python3
"""Make IF-vs-timelapse queryable from the master (2026-07-30, her rule).

BACKGROUND. I claimed the master could not distinguish an IF acquisition from a timelapse. She pushed back
and was right: it can, via the BATCH NAME - `IF` as a standalone word appears in 73 of 73 IF batches and 0
of 1539 others. What is true is the narrower statement: no CATEGORICAL COLUMN distinguishes them
(`Cell Type` is 'eYFP cdc20' for all 73), so nothing can be filtered on without string-matching the name -
and the name misses the one batch that has IF channels but no `IF` in its name.

HER RULE, given verbatim:
  * a batch named `IF` is an automatic pass;
  * otherwise it must have AT LEAST 405 AND 561 channels.

Applying that: 74 IF batches = the 73 named + `20260417 ptk2 eyfp cdc20 ablation_1` (405_DAPI /
561_mCherry / 640_Cy5 on disk, no `IF` in the name) - exactly the batch she flagged from the 8817 pass.

CHANNEL EVIDENCE, and why it needs two sources. frames.json is NOT reliable here: 40 of the 73 IF batches
have a sidecar reading ['488 (GFP)', 'Brightfield'], which is the known P11 IF role/channel misassignment
in the pipeline, and the offending batch has the same wrong sidecar. So the evidence is the union of
  (a) frames.json ch_names, trusted only when it lists MORE than 2 channels, and
  (b) the per-channel rendered filenames (405_DAPI / 561_mCherry / 640_Cy5 / 488_GFP).
Do NOT match those tokens with \\b - an underscore is a word character, so `\\b405\\b` never matches
`_405_`. That bug made a first pass report zero channels for every batch.

  python3 add_is_if_column_20260730.py --check    # report, write nothing
  python3 add_is_if_column_20260730.py            # back up, apply, verify by re-read
"""
import csv
import glob
import json
import os
import re
import shutil
import sys
import time

ROOT = "/Volumes/4 MB"
MASTER = os.path.join(ROOT, "ABLATION_MASTER.csv")
NEWCOL = "Is IF"
CHECK = "--check" in sys.argv
LAS = re.compile(r'(?<![0-9])(405|488|561|640)(?![0-9])')


def channels(batch, path):
    """Returns (readable, channels). readable=False only when the output folder is genuinely absent -
    a folder that IS readable and simply has no 405/561 is a decisive NO under her rule, not an unknown."""
    if not path or not os.path.isdir(path):
        return False, set()
    ch = set()
    for fj in glob.glob(os.path.join(path, "*_frames.json")):
        try:
            cn = json.load(open(fj)).get("ch_names") or []
            if len(cn) > 2:                     # >2 means the sidecar was not collapsed by P11
                ch |= set(LAS.findall(" ".join(cn)))
        except Exception:
            pass
        break
    try:
        ch |= set(LAS.findall(" ".join(os.listdir(path))))
    except OSError:
        return False, ch
    return True, ch


def main():
    rows = list(csv.reader(open(MASTER)))
    ghdr, hdr = rows[0], rows[1]
    ni = hdr.index("Batch Name")
    dpi = hdr.index("Drive Path")
    ci = hdr.index(NEWCOL) if NEWCOL in hdr else len(hdr)

    yes, no, unknown = [], [], []
    verdict = {}
    for r in rows[2:]:
        if len(r) <= ni:
            continue
        b = r[ni].strip()
        if not b:
            continue
        named = "IF" in b.split()
        readable, ch = channels(b, r[dpi] if len(r) > dpi else "")
        if named:
            v, why = "Yes", "named IF (automatic pass)"
            yes.append(b)
        elif "405" in ch and "561" in ch:
            v, why = "Yes", "405+561 present: " + ",".join(sorted(ch))
            yes.append(b)
        elif readable:
            v, why = "No", ""
            no.append(b)
        else:
            v, why = "", "output folder not present - cannot tell"
            unknown.append(b)
        verdict[b] = (v, why)

    print(f"Is IF = Yes : {len(yes)}   No : {len(no)}   blank (output folder absent) : {len(unknown)}")
    print("\nYes by the 405+561 rule rather than by name:")
    for b in yes:
        if "IF" not in b.split():
            print(f"   {b:56s} {verdict[b][1]}")
    if CHECK:
        print("\n--check: nothing written")
        return

    bak = MASTER + time.strftime(".%Y%m%d_%H%M%S_pre_is_if.bak")
    shutil.copy2(MASTER, bak)
    print(f"\nbackup -> {bak}")
    if NEWCOL not in hdr:
        ghdr.append("Auto")
        hdr.append(NEWCOL)
    w = len(hdr)
    for r in rows[2:]:
        while len(r) < w:
            r.append("")
    for r in rows[2:]:
        if len(r) > ni and r[ni].strip() in verdict:
            r[ci] = verdict[r[ni].strip()][0]

    tmp = MASTER + ".tmp"
    with open(tmp, "w", newline="") as f:
        csv.writer(f).writerows(rows)
    os.replace(tmp, MASTER)

    back = list(csv.reader(open(MASTER)))
    h2 = back[1]; c2 = h2.index(NEWCOL); n2 = h2.index("Batch Name")
    got = {r[n2].strip(): r[c2] for r in back[2:] if len(r) > c2}
    nyes = sum(1 for v in got.values() if v == "Yes")
    bad = [b for b in yes if got.get(b) != "Yes"]
    print(f"re-read: {NEWCOL} at col {c2}; Yes={nyes} (expected {len(yes)}); mismatches {len(bad)} {bad[:3]}")


if __name__ == "__main__":
    main()
