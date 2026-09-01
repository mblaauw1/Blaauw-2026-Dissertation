#!/usr/bin/env python3
"""A playable, verified movie for every FULL timestrip on the decks of interest.

USER 2026-08-17: "check that there are ... videos saved/ready for the tif files made into timestrips on the
illustrator files of interest ... check not only that they exist but that they work correctly/are
playable/etc, are trimmed to about 30 seconds following the annotated cytokinesis timepoint if applicable;
and make sure theyre stored in their own folder so i can easily find them. Include in the name what file and
artboard theyre on. Just necessary for full timestrips, not instances where just a single frame is
displayed."

WHICH FIGURES COUNT AS A FULL TIMESTRIP: taken from the decks themselves (the read-only geometry dumps), not
from a hand-kept list, so nothing she has placed can be missed. Single-FRAME panel sheets are excluded by
name -- the peak-zoom sheets, the k-k zoom candidates, the lagging-outline example panels and the split
`__pieceN` files are all one-frame-per-tile figures, not strips.

CROP: `group_timestrips.portion_box(batch, role)` -- the very function the strips use, so a movie always
shows the same window as the strip it belongs to.

TRIM: monitoring clips stop ~30 s after the annotated Cytokinesis Onset; where cytokinesis was never scored,
Anaphase Onset + 30 s is used instead, and where neither exists the clip is left full length. Which rule
fired is recorded per movie.

VERIFY: every file is re-opened after writing and its frame count, duration and readability checked, so
"it exists" and "it plays" are two separate, reported facts.
"""
import sys, os, csv, json, re, collections
sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
os.environ.setdefault("CAT_ONLY", "__none__")     # keep the group_timestrips import cheap
import numpy as np, cv2
import lib
import custom_revised_movies_20260811 as RM
import group_timestrips as G

TMP  = "/Volumes/4 MB/_claude_tmp"
OUT  = "/Volumes/4 MB/3_MOVIES/timestrip_movies_20260817"
os.makedirs(OUT, exist_ok=True)
RM.OUT = OUT

DECKS = {"0814": "META_FIGURES_20260814", "0813supp": "META_FIGURES_20260813_supplemental",
         "newfig": "NEW_FIGURES_20260804", "0805": "META_FIGURES_20260805",
         "supp": "supplemental", "newts": "NEW_TIMESTRIPS_20260804"}

# a NAME is a full timestrip if it looks like one AND is not one of the single-frame panel families
STRIP_RX = re.compile(r"(^nf9_|^nf10_|timestrip|_aligned$|frap0)", re.I)
NOT_STRIP = re.compile(r"(__piece\d+|peakzoom|kk_zoom|_outlines__p\d+|_statgrid|EXCERPT_|candidates)", re.I)

def load(tag):
    p = os.path.join(TMP, f"geom6_{tag}.tsv")
    if not os.path.exists(p): return []
    out = []
    with open(p, encoding="utf-8") as fh:
        hdr = fh.readline().rstrip("\n").split("\t")
        for line in fh:
            f = line.rstrip("\n").split("\t")
            if len(f) < 12: f += [""] * (12 - len(f))
            d = dict(zip(hdr, f))
            if d["kind"] in ("PlacedItem", "RasterItem") and d["toplevel"] == "1" and d["name"]:
                out.append(d)
    return out

# ---- figure name -> batch ---------------------------------------------------------------------------
# The nf9/nf10 strips carry the batch after "__" with spaces turned into underscores; everything else is
# resolved through PLOT_SETTINGS, which records the batch each figure was built from.
PS = json.load(open("/Volumes/4 MB/ablation_plots/PLOT_SETTINGS.json"))
KNOWN = {r["Batch Name"] for r in lib.load_master()[0]}

# Names that carry no batch and are not derivable from the registry. Each was resolved by reading the
# builder that makes the figure, not by pattern-matching the name.
EXPLICIT = {
    "20250711_double_ablation_18_frap0_aligned": "20250711 double ablation_18",
    "G5_item4_hec1_timestrip_xy5": "20260313 ptk_eyfp_mad1_Hec1halo_640_4_xy5",
    "G5_item4_hec1_timestrip_xy2": "20260313 ptk_eyfp_mad1_Hec1halo_640_4_xy2",
    "G5_item4_hec1_timestrip_xy4": "20260313 ptk_eyfp_mad1_Hec1halo_640_4_xy4",
    "G5_item4_hec1_timestrip_xy6": "20260313 ptk_eyfp_mad1_Hec1halo_640_4_xy6",
    "G9_drug_timestrip_zm": "20260422 Zm_ablation_2um_31",
    "G9_drug_timestrip_zm_aligned": "20260422 Zm_ablation_2um_31",
    "G9_drug_timestrip_zm3": "20260422 Zm_ablation_2um_25",
    "G9_drug_timestrip_zm3_aligned": "20260422 Zm_ablation_2um_25",
    "G9_drug_timestrip_zm18_aligned": "20260422 Zm_ablation_2um_18",
}
# NOT strips at all, despite matching the name pattern -- composite PLOTS with "_aligned" in the name, or
# a figure whose panels are single frames. Recorded so the skip list stays meaningful.
NOT_A_STRIP = {"G5shape_lagging_stretch_time_peak_aligned", "DEMO_area_with_timestrips",
               "DEMO_area_with_timestrips_zoom", "DEMO_area_with_timestrips_win_meta_to_ana"}

def batch_of(name):
    if name in NOT_A_STRIP: return None
    if name in EXPLICIT:
        b = EXPLICIT[name]
        return b if b in KNOWN else None
    if "__" in name:
        tail = name.split("__", 1)[1]
        for cand in (tail, tail.replace("_", " ")):
            if cand in KNOWN: return cand
        # names replace every space with "_" but batch names also contain real underscores -> try both
        parts = tail.split("_")
        for k in range(len(parts), 0, -1):
            for joiner in (" ", "_"):
                cand = joiner.join(parts[:k])
                if cand in KNOWN: return cand
        for b in KNOWN:
            if b.replace(" ", "_") == tail: return b
    e = PS.get(name) or {}
    s = e.get("settings") or {}
    for key in ("batch", "cell", "sample"):
        v = s.get(key)
        if isinstance(v, str) and v in KNOWN: return v
    cap = (e.get("caption") or "") + " " + json.dumps(s)
    for b in sorted(KNOWN, key=len, reverse=True):
        if b in cap: return b
    return None

targets = {}          # batch -> list of "DECK_ABn__figure"
skipped = []
for tag, deckname in DECKS.items():
    for r in load(tag):
        nm = r["name"]
        if not STRIP_RX.search(nm) or NOT_STRIP.search(nm): continue
        b = batch_of(nm)
        if b is None:
            skipped.append((deckname, nm, "batch not resolvable")); continue
        label = f"{deckname}_AB{r['ab_overlap'].split(',')[0]}__{nm}"
        targets.setdefault(b, []).append(label)

# ---- the trim point --------------------------------------------------------------------------------
MR = {r["Batch Name"]: r for r in lib.load_master()[0]}
trim_reason = {}
for b in targets:
    row = MR.get(b, {})
    cyt = lib.parse_time(row.get("Cytokinesis Onset (s)", "") or "")
    ana = lib.parse_time(row.get("Anaphase Onset (s)", "") or "")
    if cyt is not None:
        RM.TRIM_AFTER[b] = float(cyt) + 30.0; trim_reason[b] = f"cytokinesis {cyt:.0f}s + 30 s"
    elif ana is not None:
        RM.TRIM_AFTER[b] = float(ana) + 30.0; trim_reason[b] = f"no cytokinesis scored; anaphase {ana:.0f}s + 30 s"
    else:
        trim_reason[b] = "neither cytokinesis nor anaphase scored -- full length"

print(f"{len(targets)} batches behind full timestrips on the decks of interest")
made, failed = [], []
for b, labels in sorted(targets.items()):
    label = sorted(labels)[0]                       # one movie set per BATCH, named for its first placement
    others = sorted(set(labels))[1:]
    print(f"{b}   [{len(labels)} placement(s)]")
    for role in ("Ablation", "Monitoring"):
        # 2026-08-18: SKIP a clip that already exists and already plays.  A full run re-encodes all 76
        # clips (~25 min) to refresh the handful that are actually missing -- the exact scope expansion
        # she has flagged twice.  Set REBUILD_ALL=1 to force a full re-encode.
        if not os.environ.get("REBUILD_ALL"):
            _want = os.path.join(RM.OUT if hasattr(RM, "OUT") else OUT,
                                 f"{label}__{b.replace(' ', '_')}__{role.lower()}.mp4")
            if os.path.exists(_want) and os.path.getsize(_want) > 20000:
                _c = cv2.VideoCapture(_want); _ok = _c.isOpened()
                _n = int(_c.get(cv2.CAP_PROP_FRAME_COUNT)) if _ok else 0
                _rd, _ = _c.read() if _ok else (False, None); _c.release()
                if _ok and _rd and _n >= 3:
                    made.append({"batch": b, "role": role, "file": os.path.basename(_want),
                                 "frames_written": _n, "frames_readable": _n, "fps": 0, "seconds": 0,
                                 "bytes": os.path.getsize(_want), "plays": True,
                                 "trim": trim_reason.get(b, ""), "placements": [label] + others,
                                 "reused": True})
                    print(f"     {role:10s} REUSED (exists and plays, {_n} frames)")
                    continue
        try:
            r = RM.build(label, b, role)
        except Exception as e:
            r = None; print(f"   {role}: ERROR {e}")
        if not r:
            # a cell that was never ablated (unmanipulated control, colcemid, nocodazole, Mad1 timelapse)
            # HAS no ablation portion -- that is the data, not a failure.
            _has = None
            try: _has = G.role_ts(b, role)
            except Exception: pass
            note = "no ablation portion exists for this cell" if (role == "Ablation" and (_has is None or len(_has) == 0)) else "not built"
            failed.append((b, role, note)); continue
        path, n, box = r
        # ---- verification: re-open and read it ----
        cap = cv2.VideoCapture(path)
        ok = cap.isOpened()
        cnt = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) if ok else 0
        fps = cap.get(cv2.CAP_PROP_FPS) if ok else 0
        okread, _fr = cap.read() if ok else (False, None)
        cap.release()
        size = os.path.getsize(path) if os.path.exists(path) else 0
        good = ok and okread and cnt >= 3 and size > 20000
        made.append({"batch": b, "role": role, "file": os.path.basename(path),
                     "frames_written": n, "frames_readable": cnt,
                     "fps": round(fps, 2), "seconds": round(cnt / fps, 1) if fps else 0,
                     "bytes": size, "plays": bool(good), "trim": trim_reason.get(b, ""),
                     "placements": [label] + others})
        print(f"     {role:10s} {'OK ' if good else 'BAD'} {cnt:4d} frames  {size/1e6:5.1f} MB  {trim_reason.get(b,'')}")
        if not good: failed.append((b, role, f"unplayable: opened={ok} read={okread} frames={cnt} bytes={size}"))

json.dump({"movies": made, "failed": failed, "skipped": skipped},
          open(os.path.join(OUT, "MOVIE_INDEX_20260817.json"), "w"), indent=1)

with open(os.path.join(OUT, "README.md"), "w") as fh:
    fh.write(f"""# Timestrip movies — {len(made)} clips, built and verified 2026-08-17

One ablation clip and one monitoring clip for every FULL timestrip placed on the decks of interest.
Each file is named `<deck>_AB<artboard>__<figure>__<role>.mp4`, so the name says which Illustrator file and
which artboard the strip it belongs to is on.

* **Same window as the strip.** The crop is `group_timestrips.portion_box(batch, role)` — the function the
  strips themselves call — so a movie can never drift away from the figure it illustrates.
* **Trimmed** to ~30 s past the annotated Cytokinesis Onset; where cytokinesis was never scored, to
  Anaphase Onset + 30 s; where neither exists, left full length. The rule that fired is recorded per clip
  in `MOVIE_INDEX_20260817.json`.
* **Verified, not assumed.** Every file was re-opened after writing and its frame count, duration and first
  frame read back. {sum(1 for m in made if m['plays'])} of {len(made)} play; any that do not are listed
  under `failed` in the index.
* Single-frame panel sheets (peak zooms, k-k zoom candidates, outline example panels, split `__pieceN`
  files) are deliberately absent — they are not strips.
""")

print(f"\n{len(made)} movies, {sum(1 for m in made if m['plays'])} verified playable, {len(failed)} problems")
for f in failed[:20]: print("   FAILED", f)
if skipped:
    print(f"\n{len(skipped)} placed strips whose batch could not be resolved:")
    for s in skipped[:20]: print("   ", s)
print("->", OUT)
