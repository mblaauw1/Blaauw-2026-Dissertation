#!/usr/bin/env python3
"""RETIRE the `paired` grp5 outlines of `20250904 triple_ablation_8` — her instruction, 2026-08-03.

WHY: grp is her "+ New KT" kinetochore identity, so traces sharing a grp are ONE kinetochore and several on
one frame are its pieces. grp5 does not behave like one kinetochore. Across its 127 frames, 31 carry two
traces and those two sit **3.36 - 9.96 um apart (median 6.06)** — a kinetochore is ~0.3-3 um, so this is two
DIFFERENT kinetochores sharing one grp, throughout the group and not only on the 4 frames that tripped the
10 um report. On the 96 single-trace frames there is no way to tell which of the two was traced, so the
whole group is unusable, not just the multi-trace frames. She asked that they be retired so they cannot be
used.

NOT A DELETION OF HER WORK: every row is archived VERBATIM to `_retired/` first, so the tracing survives and
the group can be re-split into two kinetochores later if she wants it back.

DISCIPLINE: backup -> verbatim archive -> atomic replace -> re-read from disk and verify (row count, ids
gone, every other row byte-identical) -> restore + raise if it did not persist -> surgical removal of those
ids from the master `kt_outline_ids` mirror (a STRING edit, never a recompute: the master's `*_ids` columns
are COMMA-separated and hold FILE order) -> audit log.

Run with --apply; the default is a dry run.
"""
import csv, io, json, os, re, shutil, sys, datetime

ROOT = "/Volumes/4 MB"
sys.path.insert(0, f"{ROOT}/dataops")
import dataops as D

csv.field_size_limit(10 ** 9)
SRC = f"{ROOT}/annotations/kt_outlines.csv"
ARCHIVE = f"{ROOT}/_retired/kt_outlines_RETIRED_20260803_triple8_paired_grp5.csv"
MASTER = f"{ROOT}/ABLATION_MASTER.csv"
BATCH = "20250904 triple_ablation_8"
LABEL = "paired"
GRP = "5"
REASON = ("her instruction 2026-08-03: paired grp5 is TWO kinetochores sharing one grp — on 31 of its 127 "
          "frames the two traces sit 3.36-9.96 um apart (median 6.06), far beyond one kinetochore, so the "
          "group cannot be used as a single KT identity")


def _grp(notes):
    m = re.search(r"grp:([^;]*)", notes or "")
    return m.group(1) if (m and m.group(1)) else None


def main(apply):
    raw = open(SRC, encoding="utf-8", newline="").read()
    rows = list(csv.reader(io.StringIO(raw)))
    hdr = rows[0]
    ci = {c: i for i, c in enumerate(hdr)}
    body = rows[1:]

    def targeted(r):
        return (r and len(r) > max(ci["batch"], ci["label"], ci["notes"])
                and r[ci["batch"]].strip() == BATCH
                and r[ci["label"]].strip() == LABEL
                and _grp(r[ci["notes"]]) == GRP)

    hits = [r for r in body if targeted(r)]
    if not hits:
        raise SystemExit("REFUSED: no rows matched — nothing to retire")
    ids = [r[ci["id"]].strip() for r in hits]
    frames = sorted({int(float(r[ci["frame"]])) for r in hits if r[ci["frame"]].strip()})
    print(f"target: {BATCH} | {LABEL} | grp{GRP}")
    print(f"        {len(hits)} traces across {len(frames)} frames (ids {min(ids, key=int)}..{max(ids, key=int)})")
    print(f"rows: {len(body)} -> {len(body) - len(hits)}")
    if not apply:
        print("\nDRY RUN — nothing written. Re-run with --apply.")
        return

    bak = D.backup(SRC, "retire_triple8_grp5_20260803")
    print(f"backup -> {bak}")

    os.makedirs(os.path.dirname(ARCHIVE), exist_ok=True)
    new_archive = not os.path.isfile(ARCHIVE)
    with open(ARCHIVE, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new_archive:
            w.writerow(hdr + ["retired_ts", "retired_reason"])
        ts = datetime.datetime.now().isoformat(timespec="seconds")
        for r in hits:
            w.writerow(r + [ts, REASON])
    print(f"archived {len(hits)} rows -> {ARCHIVE}")

    kept = [r for r in body if not targeted(r)]
    tmp = SRC + ".tmp"
    with open(tmp, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(hdr); w.writerows(kept)
    os.replace(tmp, SRC)

    back = list(csv.reader(io.StringIO(open(SRC, encoding="utf-8", newline="").read())))
    ok = (back[0] == hdr and len(back) - 1 == len(kept)
          and not any(targeted(r) for r in back[1:]) and back[1:] == kept)
    if not ok:
        shutil.copy2(bak, SRC)
        raise SystemExit("REFUSED: verify-by-re-read FAILED — original restored from backup")
    print(f"verified on re-read: {len(back) - 1} rows, 0 grp{GRP} rows remain, all others byte-identical")

    # ---- surgical removal from the master mirror (string edit, order + comma delimiter preserved) ----
    mrows = D.read(MASTER)
    mh = D.header_row(MASTER, mrows)
    mhdr = [c.strip() for c in mrows[mh]]
    mci = {c: i for i, c in enumerate(mhdr)}
    if "kt_outline_ids" in mci and "Batch Name" in mci:
        tgt = [r for r in mrows[mh + 1:]
               if r and len(r) > mci["Batch Name"] and r[mci["Batch Name"]].strip() == BATCH]
        if len(tgt) != 1:
            print(f"WARNING: {len(tgt)} master rows for {BATCH!r} — mirror NOT touched")
        else:
            r = tgt[0]; i = mci["kt_outline_ids"]
            while len(r) <= i:
                r.append("")
            toks = r[i].split(",")
            drop = set(ids)
            remain = [t for t in toks if t.strip() not in drop]
            if len(remain) != len(toks):
                D.backup(MASTER, "retire_triple8_grp5_mirror_20260803")
                r[i] = ",".join(remain)
                mtmp = MASTER + ".tmp"
                with open(mtmp, "w", newline="", encoding="utf-8") as f:
                    csv.writer(f).writerows(mrows)
                os.replace(mtmp, MASTER)
                print(f"master kt_outline_ids: {len(toks)} -> {len(remain)} ids (comma-separated, order kept)")
            else:
                print("master kt_outline_ids listed none of these ids — nothing to remove")

    with open(f"{ROOT}/_retired/README.md", "a") as f:
        f.write(f"\n- `{os.path.basename(ARCHIVE)}` | **{len(hits)} `paired` outline traces RETIRED on her "
                f"2026-08-03 instruction** — `{BATCH}` grp{GRP} is TWO kinetochores sharing one grp: on 31 of "
                f"its 127 frames the two traces sit 3.36-9.96 um apart (median 6.06), and on the remaining 96 "
                f"single-trace frames there is no way to tell which of the two was traced, so the whole group "
                f"is unusable as one KT identity. Archived verbatim so it can be re-split into two "
                f"kinetochores later. | nothing — the batch keeps its `paired` grp6 track\n")

    D.audit({"ts": datetime.datetime.now().isoformat(timespec="seconds"), "op": "retire_rows",
             "path": SRC, "batch": BATCH, "label": LABEL, "grp": GRP, "n": len(hits),
             "ids": ids, "archive": ARCHIVE, "reason": REASON})
    print("done")


if __name__ == "__main__":
    main("--apply" in sys.argv)
