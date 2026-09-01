#!/usr/bin/env python3
"""Per-cell k-k distance from BOTH mark stores, so no cell she annotated is silently dropped.

WHY THIS EXISTS. The G7 movement figures took k-k from `KT_SISTER_KK_20260723.csv`, which is derived from
the kt_OUTLINE tracks only. That store covers 18 single-sisterless and 13 triple cells. Her `kt_points.csv`
`pre_abl`/`pre_abl_pair` marks cover 33 and 21. Reading one store instead of both threw away 16 single and
10 triple cells she had already annotated -- the counts she flagged on 2026-08-09 ("there should be at least
15 triple sisterless and 30 single sisterless that meet this criteria").

PROTOCOL IS HERS, COPIED FROM `group2_kk.py` (lines 37-71), NOT REINVENTED:
  * pair `pre_abl` against `pre_abl_pair` per frame by NEAREST NEIGHBOUR (`pair_nn`)
  * k-k = ||a - b|| * pixel_size
  * drop pairs > 20 um (implausible) and, on prophase/prometaphase, < 0.4 um (mis-clicked sisters)
  * honour KK_LOWKK_EXCLUDE and the standard cohort filters
The outline-derived store is kept as a second source; where a cell has both, both are reported and
`source` says so. Nothing is overwritten -- this file is additive, exactly like the stage-correction columns.

Writes `annotations/KT_KK_PERCELL_MERGED_20260809.csv`.
"""
import csv, sys, statistics
from collections import defaultdict
sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import numpy as np
import lib

csv.field_size_limit(10 ** 9)
A = "/Volumes/4 MB/annotations/"
OUT = A + "KT_KK_PERCELL_MERGED_20260809.csv"

rows_m, _ = lib.load_master()
mr = {r["Batch Name"]: r for r in rows_m}
_dbl = lib.double_chromosome_batches()

# her exclusion list, verbatim from group2_kk.py
KK_LOWKK_EXCLUDE = {
    "20260108 two_sisterless_kinetochores_18",
    "20251029 triple_ablation_4",
    "20250925 triple_ablation_26",
}


def pxsize(b):
    try:
        return float((mr.get(b, {}).get("Pixel Size (um)", "") or 0.062))
    except Exception:
        return 0.062


def nsis(b):
    v = (mr.get(b, {}).get("# Sisterless KTs", "") or "").strip()
    try:
        return int(float(v))
    except Exception:
        return None


def phase_of(b):
    p = (mr.get(b, {}).get("Phase of Ablations", "") or "").strip().lower()
    return ("Prophase" if p.startswith("proph") else
            "Prometaphase" if p.startswith("promet") else
            "Metaphase" if p.startswith("metaph") else None)


def pair_nn(A_, B_):
    """nearest-neighbour pairing; return list of (a,b) pairs. VERBATIM from group2_kk.py."""
    A_ = list(A_); B_ = list(B_); pairs = []; used = set()
    for a in A_:
        best = None; bd = 1e18
        for j, b in enumerate(B_):
            if j in used:
                continue
            d = (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2
            if d < bd:
                bd = d; best = j
        if best is not None:
            used.add(best); pairs.append((a, B_[best]))
    return pairs


# ---- source 1: her kt_points pre_abl / pre_abl_pair marks --------------------------------------
raw = list(csv.reader(open(A + "kt_points.csv", newline="", encoding="utf-8", errors="replace")))
ix = {c: i for i, c in enumerate(raw[0])}
byb = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
for r in raw[1:]:
    if len(r) <= max(ix.values()):
        continue
    b = r[ix["batch"]].strip()
    if lib.is_mad1(b) or b in _dbl or b in KK_LOWKK_EXCLUDE:
        continue
    if (lib.is_drug(b) or lib.is_four_sisterless(b) or lib.excluded(b)
            or (mr.get(b, {}).get("Exclude", "") or "").strip().lower() in ("yes", "true", "1")):
        continue
    try:
        x = float(r[ix["x"]]); y = float(r[ix["y"]])
    except Exception:
        continue
    byb[b][r[ix["frame"]]][r[ix["label"]].strip()].append((x, y))

# frame -> t_sec, so the merged per-pair store carries time and time-split builders can use it
FT = defaultdict(dict)
for r in raw[1:]:
    if len(r) <= max(ix.values()):
        continue
    try:
        FT[r[ix["batch"]].strip()][r[ix["frame"]]] = float(r[ix["t_sec"]])
    except Exception:
        pass

pts_kk = defaultdict(list)
pts_pairs = []          # per-pair rows, schema-compatible with KT_SISTER_KK_20260723.csv
for b, frames in byb.items():
    ps = pxsize(b); ph = phase_of(b)
    for fr, labs in frames.items():
        Aa = labs.get("pre_abl", []); Bb = labs.get("pre_abl_pair", [])
        if not Aa or not Bb:
            continue
        for k, (a, bb) in enumerate(pair_nn(Aa, Bb)):
            d = float(np.hypot(a[0] - bb[0], a[1] - bb[1]) * ps)
            if d > 20:
                continue                                   # implausible, her rule
            if ph in ("Prophase", "Prometaphase") and d < 0.4:
                continue                                   # mis-clicked sisters, her rule
            pts_kk[b].append(d)
            t = FT.get(b, {}).get(fr)
            pts_pairs.append([b, f"preabl_{fr}_{k}", "", "", fr,
                              ("" if t is None else f"{t:.3f}"), "pre_abl", f"{d:.4f}"])

# ---- source 2: the outline-track-derived store ---------------------------------------------------
out_kk = defaultdict(list)
try:
    for r in csv.DictReader(open(A + "KT_SISTER_KK_20260723.csv", newline="", encoding="utf-8",
                                 errors="replace")):
        b = r.get("batch", "").strip()
        try:
            d = float(r.get("kk_dist_um", ""))
        except Exception:
            continue
        if 0 < d <= 20:
            out_kk[b].append(d)
except FileNotFoundError:
    pass

# ---- merge ---------------------------------------------------------------------------------------
allb = sorted(set(pts_kk) | set(out_kk))
rows = []
for b in allb:
    p = pts_kk.get(b, []); o = out_kk.get(b, [])
    src = ("both" if p and o else "kt_points_preabl" if p else "outline_tracks")
    # PREFER her direct pre_abl marks when present: they are the native pre-ablation sister distance,
    # measured on the frame she chose. The outline-derived value is a fallback for cells she outlined
    # but never point-marked.
    use = p if p else o
    rows.append([b, nsis(b), phase_of(b) or "", src,
                 f"{statistics.median(use):.4f}", f"{statistics.mean(use):.4f}", len(use),
                 len(p), len(o)])

with open(OUT, "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["batch", "n_sisterless", "phase", "source", "kk_median_um", "kk_mean_um",
                "n_pairs_used", "n_pairs_kt_points", "n_pairs_outline"])
    w.writerows(rows)

# ---- per-pair merged store, SAME SCHEMA as KT_SISTER_KK_20260723.csv ------------------------------
# Builders that split k-k by time can swap this one filename and pick up both sources at once.
OUT_PAIR = A + "KT_SISTER_KK_MERGED_20260809.csv"
pair_rows = []
try:
    for r in csv.DictReader(open(A + "KT_SISTER_KK_20260723.csv", newline="", encoding="utf-8",
                                 errors="replace")):
        pair_rows.append([r.get("batch", ""), r.get("sister_pair_id", ""), r.get("track_a", ""),
                          r.get("track_c", ""), r.get("frame", ""), r.get("t_sec", ""),
                          r.get("phase", ""), r.get("kk_dist_um", "")])
except FileNotFoundError:
    pass
n_out = len(pair_rows)
pair_rows += pts_pairs
with open(OUT_PAIR, "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["batch", "sister_pair_id", "track_a", "track_c", "frame", "t_sec", "phase", "kk_dist_um"])
    w.writerows(pair_rows)
print(f"wrote {OUT_PAIR}\n  pair rows: {len(pair_rows)}  ({n_out} outline-derived + {len(pts_pairs)} "
      f"from her pre_abl marks)   cells: {len({r[0] for r in pair_rows})}")

print(f"wrote {OUT}\n  cells: {len(rows)}")
for n in (1, 2, 3):
    sel = [r for r in rows if r[1] == n]
    npro = [r for r in sel if not lib.is_prophase_ablation(r[0])]
    from collections import Counter
    print(f"  {n}-sisterless: {len(sel)} cells ({len(npro)} after prophase exclusion)  "
          f"sources={dict(Counter(r[3] for r in sel))}")
