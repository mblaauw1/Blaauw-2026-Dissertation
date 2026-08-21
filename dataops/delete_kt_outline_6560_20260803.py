#!/usr/bin/env python3
"""Delete ONE degenerate kinetochore-outline trace, on her instruction (2026-08-03).

TARGET: `annotations/kt_outlines.csv` id **6560** — `20250930 four_ablation_59`, label `paired`,
frame 32, notes `grp:4;kttype:paired;trace:1`.

WHY: all 12 of its points share x = 495.42 exactly. It is a perfectly vertical, ZERO-WIDTH stroke
0.209 um long and 0.0001 um wide, so the fitted ellipse gives aspect_ratio = 3136 — the only trace
above aspect 20 in 4218. It stretched the y-axis of `G5shape_aspect` (and its ECDF) to 4000 and
flattened all three violins to a line. It is a slipped stroke, not a kinetochore.

It is `trace:1` of grp 4; the real trace:0 of that group on that frame is NOT touched, and `paired`
traces are measured one record per trace, so removing this one removes exactly one shape record.

DISCIPLINE (this project has lost annotations to silent writes):
  backup -> archive the removed row VERBATIM -> atomic replace -> re-read from disk and verify
  (row gone, count -1, every other row byte-identical) -> restore + raise if it did not persist ->
  audit to _logs/dataops_audit.jsonl -> re-sync the master `kt_outline_ids` mirror.

Run with --apply; the default is a dry run.
"""
import csv, io, json, os, shutil, sys, datetime

ROOT = "/Volumes/4 MB"
sys.path.insert(0, f"{ROOT}/dataops")
import dataops as D

csv.field_size_limit(10 ** 9)
SRC = f"{ROOT}/annotations/kt_outlines.csv"
ARCHIVE = f"{ROOT}/_retired/kt_outlines_REMOVED_20260803_degenerate_trace.csv"
MASTER = f"{ROOT}/ABLATION_MASTER.csv"
TARGET_ID = "6560"
TARGET_BATCH = "20250930 four_ablation_59"
REASON = ("her instruction 2026-08-03: degenerate zero-width stroke (12 points all at x=495.42), "
          "aspect_ratio 3136, only trace >20 in 4218, wrecked G5shape_aspect")


def main(apply):
    raw = open(SRC, encoding="utf-8", newline="").read()
    rows = list(csv.reader(io.StringIO(raw)))
    hdr = rows[0]
    ci = {c: i for i, c in enumerate(hdr)}
    body = rows[1:]

    hits = [r for r in body if r and r[ci["id"]].strip() == TARGET_ID]
    if len(hits) != 1:
        raise SystemExit(f"REFUSED: expected exactly 1 row with id {TARGET_ID}, found {len(hits)}")
    row = hits[0]
    if row[ci["batch"]].strip() != TARGET_BATCH:
        raise SystemExit(f"REFUSED: id {TARGET_ID} is on {row[ci['batch']]!r}, not {TARGET_BATCH!r}")
    pts = json.loads(row[ci["points"]])
    xs = {round(p[0], 4) for p in pts}
    if len(xs) != 1:
        raise SystemExit(f"REFUSED: not the degenerate stroke — {len(xs)} distinct x values, expected 1")

    print(f"target: id={TARGET_ID} batch={row[ci['batch']]} label={row[ci['label']]} "
          f"frame={row[ci['frame']]} notes={row[ci['notes']]}")
    print(f"        {len(pts)} points, all at x={xs.pop()}  -> zero-width stroke")
    print(f"rows: {len(body)} -> {len(body) - 1}")
    if not apply:
        print("\nDRY RUN — nothing written. Re-run with --apply.")
        return

    bak = D.backup(SRC, "delete6560_20260803")
    print(f"backup -> {bak}")

    # archive the removed row VERBATIM (header + row), append if the archive already exists
    os.makedirs(os.path.dirname(ARCHIVE), exist_ok=True)
    new_archive = not os.path.isfile(ARCHIVE)
    with open(ARCHIVE, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new_archive:
            w.writerow(hdr + ["removed_ts", "removed_reason"])
        w.writerow(row + [datetime.datetime.now().isoformat(timespec="seconds"), REASON])
    print(f"archived -> {ARCHIVE}")

    kept = [r for r in body if not (r and r[ci["id"]].strip() == TARGET_ID)]
    tmp = SRC + ".tmp"
    with open(tmp, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(hdr)
        w.writerows(kept)
    os.replace(tmp, SRC)

    # ---- verify by RE-READING FROM DISK ----------------------------------------------------------
    back = list(csv.reader(io.StringIO(open(SRC, encoding="utf-8", newline="").read())))
    ok = (back[0] == hdr
          and len(back) - 1 == len(body) - 1
          and not any(r and r[ci["id"]].strip() == TARGET_ID for r in back[1:])
          and back[1:] == kept)
    if not ok:
        shutil.copy2(bak, SRC)
        raise SystemExit("REFUSED: verify-by-re-read FAILED — original restored from backup")
    print(f"verified on re-read: {len(back) - 1} rows, id {TARGET_ID} gone, all others byte-identical")

    # ---- drop the id from the master kt_outline_ids mirror (check K1) ----------------------------
    # SURGICAL, not a re-sync. A first version RECOMPUTED the whole list from the store and wrote it
    # back sorted and semicolon-joined — but the master's `*_ids` columns are **COMMA**-separated
    # (40/40 kt_outline_ids rows use commas, 0 use semicolons) and the stored order is FILE order, not
    # numeric. That rewrote 280 ids to fix one. Remove the single id from the existing string instead:
    # one cell, one token, delimiter and order untouched.
    mrows = D.read(MASTER)
    mh = D.header_row(MASTER, mrows)
    mhdr = [c.strip() for c in mrows[mh]]
    mci = {c: i for i, c in enumerate(mhdr)}
    if "kt_outline_ids" in mci and "Batch Name" in mci:
        target = [r for r in mrows[mh + 1:]
                  if r and len(r) > mci["Batch Name"] and r[mci["Batch Name"]].strip() == TARGET_BATCH]
        if len(target) != 1:
            print(f"WARNING: {len(target)} master rows for {TARGET_BATCH!r} — mirror NOT touched")
        else:
            r = target[0]
            i = mci["kt_outline_ids"]
            while len(r) <= i:
                r.append("")
            old = r[i]
            toks = old.split(",")
            if TARGET_ID not in [t.strip() for t in toks]:
                print(f"master kt_outline_ids does not list {TARGET_ID} — nothing to remove")
            else:
                D.backup(MASTER, "delete6560_mirror_20260803")
                r[i] = ",".join(t for t in toks if t.strip() != TARGET_ID)
                mtmp = MASTER + ".tmp"
                with open(mtmp, "w", newline="", encoding="utf-8") as f:
                    csv.writer(f).writerows(mrows)
                os.replace(mtmp, MASTER)
                chk = D.read(MASTER)
                got = [x for x in chk[mh + 1:]
                       if x and len(x) > mci["Batch Name"]
                       and x[mci["Batch Name"]].strip() == TARGET_BATCH][0][i]
                assert TARGET_ID not in [t.strip() for t in got.split(",")] and ";" not in got
                print(f"master kt_outline_ids: {len(toks)} -> "
                      f"{len([t for t in got.split(',') if t.strip()])} ids (comma-separated, order kept)")

    D.audit({"ts": datetime.datetime.now().isoformat(timespec="seconds"),
             "op": "delete_rows", "path": SRC, "ids": [TARGET_ID], "batch": TARGET_BATCH,
             "n_before": len(body), "n_after": len(kept), "archive": ARCHIVE, "reason": REASON})
    print("done")


if __name__ == "__main__":
    main("--apply" in sys.argv)
