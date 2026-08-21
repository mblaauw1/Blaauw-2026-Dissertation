#!/usr/bin/env python3
"""Assign a `grp` to every outline in `20250402 ptk_yfpcdc20_7`. Nothing is split, moved or relabelled.

THE PROBLEM. All 244 outlines in this cell carry NO `grp`. Track identity in `kt_tracks._grp_tracks` IS
her grp, so ungrouped traces fall through to nearest-neighbour linking, which lumped all 102 `paired`
traces into a single track. Grouping them makes tracking deterministic and inspectable.

WHAT THIS IS NOT. An earlier attempt split the multi-piece paired traces into two "kinetochores" and
created a sister pair 0.61 um apart. The trajectory plot disproved it: the second pieces ride the SAME
path as the first, so they are one kinetochore outlined in two strokes, not two kinetochores. That split
was reverted. THIS script does not split pieces, does not create pairs, and does not touch labels -- it
only writes `grp:N` into `notes`. If the paired traces really are one kinetochore, they get one group and
the cell legitimately has no sister pair until the partner is traced.

METHOD. Per LABEL, link whole-trace centroids across frames by nearest neighbour (gate MAX_LINK_PX). A
trace joins the track it is closest to; a trace beyond the gate starts a new track. This is the same
"assign it to whichever it fits best, not randomly" rule she stated for frames carrying only one outline.

NON-DESTRUCTIVE: backup, verify, atomic swap. Only this batch's rows are touched, and only `notes`.
"""
import csv, json, math, os, shutil, collections

csv.field_size_limit(10 ** 9)
KT = "/Volumes/4 MB/annotations/kt_outlines.csv"
TB = "20250402 ptk_yfpcdc20_7"
MAX_LINK_PX = 40.0


def cen(p):
    return (sum(q[0] for q in p) / len(p), sum(q[1] for q in p) / len(p))


with open(KT, newline="", encoding="utf-8", errors="replace") as f:
    rd = csv.DictReader(f); FIELDS = rd.fieldnames; rows = list(rd)

mine = [r for r in rows if r.get("batch", "").strip() == TB]
print(f"{TB}: {len(mine)} outline rows")
pre = sum(1 for r in mine if "grp:" in (r.get("notes") or ""))
print(f"   already carrying a grp: {pre}")

assigned = {}
for label in sorted({(r.get("label") or "").strip() for r in mine}):
    sel = [r for r in mine if (r.get("label") or "").strip() == label]
    byframe = collections.defaultdict(list)
    for r in sel:
        try:
            pts = json.loads(r.get("points") or "[]")
        except Exception:
            pts = []
        if pts:
            byframe[int(r["frame"])].append((cen(pts), r))
    tracks = []
    for fr in sorted(byframe):
        items = byframe[fr]
        used = set()
        for tr in tracks:
            best, bd = None, MAX_LINK_PX
            for i, (c, r) in enumerate(items):
                if i in used:
                    continue
                d = math.hypot(c[0] - tr["last"][0], c[1] - tr["last"][1])
                if d < bd:
                    bd, best = d, i
            if best is not None:
                c, r = items[best]; used.add(best)
                tr["last"] = c; tr["rows"].append(r)
        for i, (c, r) in enumerate(items):
            if i not in used:
                tracks.append({"last": c, "rows": [r]})
    tracks.sort(key=lambda t: -len(t["rows"]))
    print(f"   {label:8s}: {len(sel):4d} traces -> {len(tracks)} track(s) {[len(t['rows']) for t in tracks]}")
    for gi, tr in enumerate(tracks, 1):
        for r in tr["rows"]:
            assigned[id(r)] = gi

changed = 0
for r in mine:
    g = assigned.get(id(r))
    if g is None:
        continue
    note = (r.get("notes") or "").strip()
    if "grp:" in note:
        continue
    r["notes"] = f"grp:{g};trace:0" + (f";{note}" if note else "")
    changed += 1

print(f"\nrows given a grp: {changed}")
tmp = KT + ".tmp_grp"
with open(tmp, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=FIELDS); w.writeheader(); w.writerows(rows)
with open(tmp, newline="", encoding="utf-8", errors="replace") as f:
    chk = list(csv.DictReader(f))
after = [r for r in chk if r.get("batch", "").strip() == TB]
missing = [r for r in after if "grp:" not in (r.get("notes") or "")]
if len(chk) != len(rows) or len(after) != len(mine) or missing:
    os.remove(tmp)
    raise SystemExit(f"ABORT: rows {len(chk)}/{len(rows)}, batch {len(after)}/{len(mine)}, ungrouped {len(missing)}")
shutil.copy2(KT, KT + ".bak_pre_ptk7_grpassign_20260809")
os.replace(tmp, KT)
print(f"backup: {KT}.bak_pre_ptk7_grpassign_20260809")
print(f"{TB}: {len(after)} rows, ALL carrying a grp (row count unchanged, no trace split or relabelled)")
