#!/usr/bin/env python3
"""Fill the blank `t_sec` values in kt_outlines.csv from each batch's own frames.json.

USER RULE (two look-alike time bugs): a row with a BLANK t_hms has a WRONG/MISSING TIME and a TRUSTWORTHY
FRAME -- so the time is derived from the frame. (The opposite case, a row that HAS a t_hms, has a stale
FRAME and its t_sec must never be rewritten. All 45 rows here have a blank t_hms, so this is the safe case.)

THE MAPPING IS PROVEN PER BATCH, NEVER ASSUMED. Annotation frames index the per-ROLE clip (`phase` mon/abl),
but two of these batches carry the known outline off-by-one. So for each batch the offset is DERIVED from
that batch's own rows that already have a correct t_sec, and is accepted only when it reproduces EVERY one
of them:
    20260310 ptk2_eyfp_mad1_8           offset -1   (10/10)
    20260310 ptk2_eyfp_mad1_14          offset -1   ( 5/5 )
    20260304 Mad1_ablation_8            offset  0   (23/23)
    20260303 Mad1_Ptk_Eyfpmad1_ablation_10 offset 0 ( 9/9 )
    20251104 ablations_5                offset  0   (221/221)
    20260304 Mad1_ablation_10           NO good rows -> offset UNKNOWABLE -> its 10 blanks are LEFT BLANK.

Leaving those 10 blank is the point: with nothing to validate against, any value would be fabricated.

Also fills `t_hms` for the rows it touches. NON-DESTRUCTIVE: backup, verify, atomic swap.
"""
import csv, json, os, shutil, sys, collections
sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import lib

csv.field_size_limit(10 ** 9)
KT = "/Volumes/4 MB/annotations/kt_outlines.csv"
ROLE = {"mon": "monitoring", "abl": "ablation"}
MIN_GOOD = 3          # need at least this many correct rows to trust a derived offset

rows_m, _ = lib.load_master()
MR = {r["Batch Name"]: r for r in rows_m}


def frames_for(b):
    d = (MR.get(b, {}).get("Drive Path", "") or "").strip()
    if not (d and os.path.isdir(d)):
        d = os.path.join("/Volumes/4 MB/pipeline_session_output", b.split()[0], b)
    p = os.path.join(d, f"{b}_frames.json")
    if not os.path.isfile(p):
        return None
    try:
        return json.load(open(p)).get("frames", [])
    except Exception:
        return None


def hms(t):
    t = float(t); sign = "-" if t < 0 else ""
    t = abs(t); h = int(t // 3600); m = int((t % 3600) // 60); s = int(t % 60)
    return f"{sign}{h}:{m:02d}:{s:02d}"


with open(KT, newline="", encoding="utf-8", errors="replace") as f:
    rd = csv.DictReader(f); FIELDS = rd.fieldnames; rows = list(rd)

blank = [r for r in rows if not (r.get("t_sec") or "").strip()]
print(f"rows with blank t_sec: {len(blank)}")
batches = sorted({r.get("batch", "").strip() for r in blank})

# ---- derive and VALIDATE a per-batch offset --------------------------------------------------------
offset, seqs_by_batch = {}, {}
for b in batches:
    fr = frames_for(b)
    if not fr:
        print(f"   {b[:46]:46s} NO frames.json -> skipped"); continue
    seqs = {rk: [x for x in fr if x.get("role") == rv] for rk, rv in ROLE.items()}
    seqs_by_batch[b] = seqs
    good = [r for r in rows if r.get("batch", "").strip() == b and (r.get("t_sec") or "").strip()]
    # CROSS-STORE VALIDATION (2026-08-09). A batch can have NO correct t_sec in kt_outlines at all --
    # 20260304 Mad1_ablation_10 is exactly that -- which leaves the offset unknowable from this file alone.
    # But her OTHER mark stores for the SAME batch use the same per-role clip indexing, so a row there with
    # a known-good frame+t_sec validates the offset just as well. meta_plates gives 4/4 at offset -1 for
    # that cell. Still validated, never assumed: the offset must reproduce EVERY cross-store row too.
    if len(good) < MIN_GOOD:
        for other in ("meta_plates.csv", "kt_points.csv", "cell_outlines.csv", "chromo_lines.csv"):
            try:
                orows = [r for r in csv.DictReader(open("/Volumes/4 MB/annotations/" + other, newline="",
                                                        encoding="utf-8", errors="replace"))
                         if r.get("batch", "").strip() == b and (r.get("t_sec") or "").strip()
                         and str(r.get("frame") or "").strip()]
            except Exception:
                continue
            if len(orows) >= MIN_GOOD:
                good = orows
                print(f"   {b[:46]:46s} (offset validated against {other}, {len(orows)} rows)")
                break
    best = None
    for off in (0, -1, 1):
        hit = tot = 0
        for r in good:
            try:
                fnum = int(r["frame"]); t = float(r["t_sec"])
            except Exception:
                continue
            s = seqs.get((r.get("phase") or "").strip())
            if not s:
                continue
            tot += 1
            i = fnum + off
            if 0 <= i < len(s) and abs(s[i]["t_sec"] - t) < 0.5:
                hit += 1
        if tot >= MIN_GOOD and hit == tot:
            best = (off, hit, tot); break
    if best:
        offset[b] = best[0]
        print(f"   {b[:46]:46s} offset {best[0]:+d}  validated {best[1]}/{best[2]}")
    else:
        print(f"   {b[:46]:46s} NO validated offset -> its blanks stay BLANK")

# ---- fill -------------------------------------------------------------------------------------------
filled = skipped = 0
for r in rows:
    if (r.get("t_sec") or "").strip():
        continue
    b = r.get("batch", "").strip()
    if b not in offset:
        skipped += 1; continue
    s = seqs_by_batch[b].get((r.get("phase") or "").strip())
    try:
        i = int(r["frame"]) + offset[b]
    except Exception:
        skipped += 1; continue
    if not s or not (0 <= i < len(s)):
        skipped += 1; continue
    t = s[i].get("t_sec")
    if t is None:
        skipped += 1; continue
    r["t_sec"] = f"{float(t):.3f}"
    r["t_hms"] = hms(t)
    filled += 1

print(f"\nfilled {filled}, left blank {skipped}")
if not filled:
    raise SystemExit("nothing to write")

tmp = KT + ".tmp_tsec"
with open(tmp, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=FIELDS); w.writeheader(); w.writerows(rows)
with open(tmp, newline="", encoding="utf-8", errors="replace") as f:
    chk = list(csv.DictReader(f))
if len(chk) != len(rows):
    os.remove(tmp); raise SystemExit("ABORT: row count changed")
still = sum(1 for r in chk if not (r.get("t_sec") or "").strip())
if still != skipped:
    os.remove(tmp); raise SystemExit(f"ABORT: expected {skipped} blanks left, found {still}")
shutil.copy2(KT, KT + ".bak_pre_tsec_fill_20260809")
os.replace(tmp, KT)
print(f"backup: {KT}.bak_pre_tsec_fill_20260809")
print(f"blank t_sec remaining: {still}  (by batch: "
      f"{dict(collections.Counter(r.get('batch','') for r in chk if not (r.get('t_sec') or '').strip()))})")
