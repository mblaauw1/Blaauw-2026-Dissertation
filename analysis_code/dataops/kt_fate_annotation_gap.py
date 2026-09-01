#!/usr/bin/env python3
"""Which sisterless kinetochores still need a PLATE-JOIN FATE annotation, per CHROMOSOME.

WHY: G3_kt_fate / G3_plate_join_timing classify every ablated sisterless KT into one of three fates,
read from annotations/SISTERLESS_PLATE_JOIN_TIMES.csv:

    "anaphase"        -> stayed polar; never rejoined the plate before anaphase
    "0" / "0:00:00"   -> was at the plate the whole time (never went polar)
    h:mm:ss           -> went polar, then rejoined the plate at this ELAPSED time

Blank / "n/a" in a chromosome slot that the cell actually HAS is the gap: not "never rejoined",
just not yet looked at. A 1-sisterless cell legitimately has chromosome_2/3 blank -- only the first
n_sisterless slots are required, which is why this counts CHROMOSOMES, not cells.

Eligibility mirrors the figures: prometaphase, on-target, master Exclude != yes, 1-3 sisterless.
(An earlier inline version of this report counted only cells already adjacent to the store and so
under-reported the gap; this is the archived, reproducible replacement.)
"""
import csv, io, collections, os, sys

ROOT   = "/Volumes/4 MB"
MASTER = f"{ROOT}/ABLATION_MASTER.csv"
STORE  = f"{ROOT}/annotations/SISTERLESS_PLATE_JOIN_TIMES.csv"
OUT    = f"{ROOT}/4_TABLES_AND_REPORTS/KT_FATE_ANNOTATION_GAP_20260821.csv"

BLANK = ("", "n/a", "na", "?", "-", "tbd")

def load_master():
    raw = io.open(MASTER, encoding="utf-8-sig", errors="replace").read().splitlines()
    hi  = next(i for i, l in enumerate(raw) if l.startswith("Batch Name,"))   # header is NOT line 1
    return [r for r in csv.DictReader(raw[hi:]) if (r.get("Batch Name") or "").strip()]

def n_sisterless(r):
    v = (r.get("# Sisterless KTs") or "").strip()
    return int(v) if v.isdigit() else None

def eligible(r):
    return ((r.get("Phase of Ablations") or "").strip().lower() == "prometaphase"
            and (r.get("On-Target / Off-Target") or "").strip().lower() == "on-target"
            and (r.get("Exclude") or "").strip().lower() not in ("yes", "y")
            and n_sisterless(r) in (1, 2, 3))

def cohort(b):
    s = b.lower()
    for k in ("collagen", "colcemid", "washout", "noc", "zm", "cdc20"):
        if k in s:
            return k
    return "untreated/unlabelled"

def main():
    M     = load_master()
    elig  = {r["Batch Name"].strip(): r for r in M if eligible(r)}
    store = {r["batch"].strip(): r for r in csv.DictReader(io.open(STORE, encoding="utf-8"))}

    rows, done = [], 0
    for b, m in sorted(elig.items()):
        n   = n_sisterless(m)
        s   = store.get(b)
        for k in range(1, n + 1):
            if s is None:
                rows.append(dict(batch=b, chromosome=k, n_sisterless=n, cohort=cohort(b),
                                 date=(m.get("Date") or "").strip(), gap="NO ROW IN STORE",
                                 detail="cell absent from SISTERLESS_PLATE_JOIN_TIMES.csv"))
                continue
            if (s.get("exclude_this_data") or "").strip().lower() in ("yes", "y"):
                continue                                    # she already ruled this cell out
            v = (s.get(f"chromosome_{k}_plate_join") or "").strip()
            if v.lower() in BLANK:
                rows.append(dict(batch=b, chromosome=k, n_sisterless=n, cohort=cohort(b),
                                 date=(m.get("Date") or "").strip(), gap="SLOT BLANK",
                                 detail=f"row present, chromosome_{k}_plate_join empty"))
            else:
                done += 1

    need_cells = len({r["batch"] for r in rows})
    total_kt   = done + len(rows)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with io.open(OUT, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["batch", "chromosome", "n_sisterless", "cohort", "date", "gap", "detail"])
        w.writeheader(); w.writerows(rows)

    print(f"eligible cells                 {len(elig)}")
    print(f"sisterless KTs they contain    {total_kt}")
    print(f"  annotated                    {done}")
    print(f"  NEEDING ANNOTATION           {len(rows)}   across {need_cells} cells")
    for k, v in collections.Counter(r["gap"] for r in rows).most_common():
        print(f"     {v:4d}  {k}")
    print("  by cohort:")
    for k, v in collections.Counter(r["cohort"] for r in rows).most_common():
        print(f"     {v:4d}  {k}")
    print("  by n_sisterless:")
    for k, v in sorted(collections.Counter(r["n_sisterless"] for r in rows).items()):
        print(f"     {v:4d}  in {k}-sisterless cells")
    print(f"\nwrote {OUT}")

if __name__ == "__main__":
    sys.exit(main())
