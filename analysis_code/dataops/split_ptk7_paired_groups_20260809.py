#!/usr/bin/env python3
"""Give `20250402 ptk_yfpcdc20_7` real kinetochore groups, so its outlines can be tracked and paired.

USER 2026-08-09: "look at the blue traces and separate them into two different paired groups" and
"if youre complaining that All 244 outlines in that cell have no grp, you should resolve this."

THE PROBLEM. Every one of this cell's 244 outlines has NO `grp`. Track identity in `kt_tracks._grp_tracks`
IS her grp, so ungrouped outlines fall back to nearest-neighbour linking, which collapsed all 102 `paired`
traces into ONE track -- a track with nothing to pair with. That is why the cell yields no sister pair.

WHAT THE BLUE TRACES ACTUALLY CONTAIN. 21 of the 102 paired traces are drawn as TWO DISJOINT PIECES about
0.5-0.7 um apart (the two adjacent blue outlines she sees); the other 81 are a single piece. So the second
kinetochore is present, just carried inside the same row rather than as its own trace.

WHAT THIS DOES.
  1. splits every paired trace into its disjoint pieces (a gap > GAP_PX between consecutive points starts
     a new piece -- the same "multi-piece" notion the shape metrics already use);
  2. links piece centroids across frames by nearest neighbour into at most 2 kinetochore tracks;
  3. writes each piece as its own row carrying `grp:1` / `grp:2` in `notes`;
  4. does the same for the `polar` traces so nothing in the cell is left ungrouped.

It does NOT decide that the two groups are sisters -- `kt_sisters.py` applies her own criteria to that, and
the resulting separation is REPORTED here so she can sanity-check it against real sister spacing (~1-3 um).
If it comes out well under that, these two pieces are more likely one kinetochore drawn in two strokes,
and this split should be reverted.

NON-DESTRUCTIVE: backup, verify, atomic swap. Only this batch's rows are touched.
"""
import csv, json, math, os, shutil, sys, collections

csv.field_size_limit(10 ** 9)
KT = "/Volumes/4 MB/annotations/kt_outlines.csv"
TB = "20250402 ptk_yfpcdc20_7"
GAP_PX = 6.0          # a jump larger than this between consecutive points starts a new piece
MAX_LINK_PX = 40.0    # a centroid further than this from a track's last position starts a new track


def pieces(pts):
    out = [[pts[0]]]
    for a, b in zip(pts, pts[1:]):
        if math.hypot(b[0] - a[0], b[1] - a[1]) > GAP_PX:
            out.append([])
        out[-1].append(b)
    return [p for p in out if len(p) >= 3]


def cen(p):
    return (sum(q[0] for q in p) / len(p), sum(q[1] for q in p) / len(p))


with open(KT, newline="", encoding="utf-8", errors="replace") as f:
    rd = csv.DictReader(f); FIELDS = rd.fieldnames; rows = list(rd)

mine = [r for r in rows if r.get("batch", "").strip() == TB]
others = [r for r in rows if r.get("batch", "").strip() != TB]
print(f"{TB}: {len(mine)} outline rows")

maxid = 0
for r in rows:
    try:
        maxid = max(maxid, int(float(str(r.get("id") or 0))))
    except Exception:
        pass

new_rows, report = [], {}
for label in ("paired", "polar"):
    sel = [r for r in mine if (r.get("label") or "").strip() == label]
    # frame -> list of (centroid, piece_points, source_row)
    byframe = collections.defaultdict(list)
    for r in sel:
        try:
            pts = json.loads(r.get("points") or "[]")
        except Exception:
            pts = []
        if not pts:
            continue
        for p in pieces(pts):
            byframe[int(r["frame"])].append((cen(p), p, r))
    # link across frames, nearest neighbour, at most 2 tracks for paired
    tracks = []           # each: {"last": (x,y), "items": [(frame, piece, row)]}
    for fr in sorted(byframe):
        items = sorted(byframe[fr], key=lambda t: (t[0][0], t[0][1]))
        used = set()
        for tr in tracks:
            best, bd = None, MAX_LINK_PX
            for i, (c, p, r) in enumerate(items):
                if i in used:
                    continue
                d = math.hypot(c[0] - tr["last"][0], c[1] - tr["last"][1])
                if d < bd:
                    bd, best = d, i
            if best is not None:
                c, p, r = items[best]
                used.add(best); tr["last"] = c; tr["items"].append((fr, p, r))
        for i, (c, p, r) in enumerate(items):
            if i in used:
                continue
            tracks.append({"last": c, "items": [(fr, p, r)]})
    tracks.sort(key=lambda t: -len(t["items"]))
    report[label] = [len(t["items"]) for t in tracks]
    for gi, tr in enumerate(tracks, 1):
        for fr, p, src in tr["items"]:
            maxid += 1
            row = dict(src)
            row["id"] = maxid
            row["points"] = json.dumps([[round(x, 2), round(y, 2)] for x, y in p])
            row["notes"] = f"grp:{gi};trace:0"
            new_rows.append(row)

print("\ntracks found (traces per track):")
for lab, sizes in report.items():
    print(f"   {lab:8s}: {len(sizes)} tracks -> {sizes[:8]}")

# ---- report the separation between the two paired groups, for her judgement -----------------------
pg = collections.defaultdict(dict)
for r in new_rows:
    if (r.get("label") or "").strip() != "paired":
        continue
    g = r["notes"].split(";")[0].split(":")[1]
    pts = json.loads(r["points"])
    pg[int(r["frame"])][g] = cen(pts)
both = [f for f in pg if len(pg[f]) >= 2]
if both:
    ds = []
    for f in both:
        ks = sorted(pg[f])
        a, b = pg[f][ks[0]], pg[f][ks[1]]
        ds.append(math.hypot(a[0] - b[0], a[1] - b[1]) * 0.062)
    ds.sort()
    print(f"\nframes where BOTH paired groups exist: {len(both)}")
    print(f"   separation median {ds[len(ds)//2]:.2f} um   range {ds[0]:.2f}-{ds[-1]:.2f} um")
    print( "   (real sister k-k in this dataset runs ~1-3 um; well under that suggests ONE kinetochore "
           "drawn in two strokes, and this split should be reverted)")

out = others + new_rows
tmp = KT + ".tmp_split"
with open(tmp, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=FIELDS); w.writeheader(); w.writerows(out)
with open(tmp, newline="", encoding="utf-8", errors="replace") as f:
    chk = list(csv.DictReader(f))
after = [r for r in chk if r.get("batch", "").strip() == TB]
ids = [r.get("id") for r in chk if str(r.get("id") or "").strip()]
if len(chk) != len(others) + len(new_rows) or len(ids) != len(set(ids)) or any(
        "grp:" not in (r.get("notes") or "") for r in after):
    os.remove(tmp); raise SystemExit("ABORT: verification failed")
shutil.copy2(KT, KT + ".bak_pre_ptk7_split_20260809")
os.replace(tmp, KT)
print(f"\nbackup: {KT}.bak_pre_ptk7_split_20260809")
print(f"{TB}: {len(mine)} rows -> {len(after)} rows, all carrying a grp")
