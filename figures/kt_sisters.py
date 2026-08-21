#!/usr/bin/env python3
"""Sister-pair determination for PAIRED kinetochores (user 2026-07-23; NOT applicable to polar/lagging).
Two paired tracks in a cell are sisters if, DURING METAPHASE, they stay spatially close (~1-3um) on most
co-occurring frames and move in a coordinated way. Sisters are LINKED for the whole movie (a pair can't
re-form with a different KT), so the decision is made once (in metaphase) and carried to all phases.

Patterns: 1 paired mark/frame -> no sister; 2 -> one sister pair; 3 -> one pair + one lone; 4 -> two pairs.
Matching: mutually-closest paired tracks with metaphase median distance < MAX_SIS_UM, each track in <=1 pair.
Output (NON-DESTRUCTIVE): annotations/KT_SISTERS_20260723.csv."""
import sys, os, csv, collections
sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import numpy as np, matplotlib.pyplot as plt
import lib, kt_stats
import kt_tracks as KT
from kt_landmark_analysis import phase_times
lib.apply_style()
ROOT = "/Volumes/4 MB"; csv.field_size_limit(10 ** 9)
OUT = f"{ROOT}/ablation_figures_20260625/group6_tracks"
OUTCSV = f"{ROOT}/annotations/KT_SISTERS_20260723.csv"
SRC = [f"{ROOT}/annotations/KT_OUTLINE_TRACKS_20260723.csv"]
MAX_SIS_UM = 3.5           # metaphase median sister separation ceiling
MIN_CO_FRAMES = 3          # need this many co-occurring metaphase frames to judge a pair


def load_manual(path=OUTCSV):
    """Her MANUAL sister determinations are GROUND TRUTH and override proximity (2026-07-27).
    Returns (rows, batches) for every row with basis=='manual' already in the output file."""
    if not os.path.exists(path):
        return [], set()
    with open(path, newline="") as f:
        rows = [r for r in csv.DictReader(f)
                if not lib.is_prophase_ablation(r.get("batch", ""))]   # prophase excluded
    man = [r for r in rows if (r.get("basis") or "").strip().lower() == "manual"
           and not lib.is_prophase_ablation(r.get("batch", ""))]   # prophase excluded
    return man, {r["batch"] for r in man}


def _series_for(A, B, mt, at):
    """per-frame k-k series for two track dicts {frame:(t,cx,cy,px)}"""
    ser = []
    for f in sorted(set(A) & set(B)):
        ta, ax, ay, px = A[f]; tb, bx, by_, _ = B[f]
        kk = np.hypot(ax - bx, ay - by_) * px
        phase = ("prometaphase" if (mt is not None and ta < mt)
                 else "anaphase" if (at is not None and ta >= at)
                 else "metaphase" if mt is not None else "")
        ser.append((f, ta, kk, phase))
    return ser


def build():
    objs = [o for o in KT.tracked_objects() if o["label"] == "paired"]
    ph = phase_times(sorted({o["batch"] for o in objs}))
    # per track: {frame: (t_sec, cx, cy, px)}
    tracks = collections.defaultdict(dict)
    tbatch = {}
    for o in objs:
        tracks[o["track_id"]][o["frame"]] = (o["t_sec"], o["cx"], o["cy"], o["px"])
        tbatch[o["track_id"]] = o["batch"]
    by_batch = collections.defaultdict(list)
    for tid, b in tbatch.items():
        by_batch[b].append(tid)

    manual_rows, manual_batches = load_manual()

    pair_rows, sister_of = [], {}
    pair_series = []   # (batch, pair_id, [(t_min, dist_um)])
    for b, tids in by_batch.items():
        # 2026-08-09: THE PROPHASE SKIP WAS REMOVED. It was a PLOT rule applied inside a DATA STORE, so
        # prophase cells she had traced never got sister pairs at all and were invisible to every
        # downstream figure -- including the ones that legitimately draw a prophase group. Cohort
        # filtering belongs at plot time (`lib.plot_excluded` / `lib.is_prophase_ablation`), which every
        # consumer already calls. The store now covers EVERY cell with paired outline tracks; each row
        # carries `ablation_phase` so a consumer can filter explicitly rather than relying on the store
        # having silently pre-filtered for it.
        #
        # Acceptance test is HER structural rule (2026-08-09): a triple-sisterless cell with paired
        # outlines has 2 sister sets (4 traced KTs); a single-sisterless cell with paired traces has at
        # least 1, sometimes more.
        mt, at = ph.get(b, (None, None))
        # ---- MANUAL cells: her determination wins outright; never recompute by proximity ----
        if b in manual_batches:
            mrows = [r for r in manual_rows if r["batch"] == b]
            covered = {r["track_id"] for r in mrows}
            pair_rows.extend(dict(r) for r in mrows)          # preserved verbatim
            for tid in tids:                                   # lone paired tracks in a manual cell
                if tid not in covered:
                    pair_rows.append(dict(track_id=tid, batch=b, sister_pair_id="", partner_track="",
                                          metaphase_median_dist_um="", n_coframes="", basis="",
                                          n_paired_tracks_in_cell=len(tids)))
            bypid = collections.defaultdict(list)
            for r in mrows:
                if r["sister_pair_id"]:
                    bypid[r["sister_pair_id"]].append(r["track_id"])
            for spid, members in bypid.items():
                mem = sorted(set(members))
                if len(mem) != 2:
                    print(f"  ! manual pair {b} {spid} has {len(mem)} members - skipped for k-k")
                    continue
                a, c = mem
                if a not in tracks or c not in tracks:
                    # HER MANUAL CALL NAMES A TRACK THAT HAS NO OUTLINES (e.g. 20250826 test_ablation_14
                    # pairs grp2 with grp3, and grp3 was never traced). Do NOT auto-pair the orphan by
                    # proximity: with the true sister untraced, the nearest remaining track may be an
                    # unrelated kinetochore, and sister identity is her determination to make. Report it
                    # and leave the cell short -- a visibly missing pair is safer than an invented one.
                    print(f"  ! manual pair {b} {spid}: track_id not in current tracks ({a} / {c}) - k-k skipped")
                    continue
                ser = _series_for(tracks[a], tracks[c], mt, at)
                med = float(np.median([s[2] for s in ser])) if ser else float("nan")
                pair_series.append((b, spid, a, c, med, len(ser), ser))
            # A MANUAL CELL IS FINISHED HERE. This `continue` is what keeps her determination exclusive:
            # without it the cell also falls through to the proximity branch below, which appends a SECOND,
            # auto-generated pair for the same tracks. That is exactly how `20250826 test_ablation_14` ended
            # up with contradictory rows (grp2->grp3 manual alongside grp2->grp19 proximity) and how two
            # triples came to report 4 sister sets instead of 2.
            continue
        # ---- AUTOMATIC cells: proximity fallback (only where she has made no determination) ----
        # candidate metaphase-window distance between every pair of paired tracks
        cand = []
        for i in range(len(tids)):
            for j in range(i + 1, len(tids)):
                A, B = tracks[tids[i]], tracks[tids[j]]
                common = set(A) & set(B)
                meta_ds, all_ds = [], []
                for f in common:
                    ta, ax, ay, px = A[f]; tb, bx, by_, _ = B[f]
                    d = np.hypot(ax - bx, ay - by_) * px
                    all_ds.append(d)
                    if (mt is not None and at is not None) and (mt <= ta < at):
                        meta_ds.append(d)
                # decide in metaphase; fall back to any-phase co-frames when the pair has no metaphase
                # outlines (user: determination can be carried to prometaphase/anaphase)
                if len(meta_ds) >= MIN_CO_FRAMES:
                    ds, basis = meta_ds, "proximity"
                elif len(all_ds) >= MIN_CO_FRAMES:
                    ds, basis = all_ds, "proximity-anyphase"
                else:
                    continue
                # qualify sisters by their CLOSEST-APPROACH (25th-pct) distance, not the median: a real
                # bioriented pair that later SEGREGATES (k-k rising to 5-6um at/after anaphase) has an inflated
                # median and was wrongly rejected by the 3.5um ceiling (e.g. 20260420 _13: sisters 1.8um then
                # segregate). The 25th percentile captures "were they ever a tight bioriented pair".
                close = float(np.percentile(ds, 25))
                cand.append((float(np.median(ds)), tids[i], tids[j], len(ds), basis, close))
        cand.sort(key=lambda c: c[5])   # tightest closest-approach first
        used = set(); pid = 0
        for med, a, c, n, basis, close in cand:
            if a in used or c in used or close > MAX_SIS_UM:
                continue
            used.add(a); used.add(c); pid += 1
            spid = f"{b}|sis{pid}"
            sister_of[a] = (spid, c, med, n, basis); sister_of[c] = (spid, a, med, n, basis)
            # full-movie k-k (sister centroid-to-centroid) distance series, per frame possible
            A, B = tracks[a], tracks[c]
            ser = []
            for f in sorted(set(A) & set(B)):
                ta, ax, ay, px = A[f]; tb, bx, by_, _ = B[f]
                kk = np.hypot(ax - bx, ay - by_) * px
                phase = ("prometaphase" if (mt is not None and ta < mt)
                         else "anaphase" if (at is not None and ta >= at)
                         else "metaphase" if mt is not None else "")
                ser.append((f, ta, kk, phase))
            pair_series.append((b, spid, a, c, med, n, ser))
        for tid in tids:
            s = sister_of.get(tid)
            pair_rows.append(dict(track_id=tid, batch=b,
                                  sister_pair_id=(s[0] if s else ""),
                                  partner_track=(s[1] if s else ""),
                                  metaphase_median_dist_um=(round(s[2], 3) if s else ""),
                                  n_coframes=(s[3] if s else ""),
                                  basis=(s[4] if s else ""),
                                  n_paired_tracks_in_cell=len(tids)))
    # SAFETY: every manual row that was on disk must still be on disk, unchanged.
    out_key = {(r["track_id"], r.get("sister_pair_id", ""), r.get("partner_track", "")) for r in pair_rows
               if (r.get("basis") or "").strip().lower() == "manual"}
    missing = [r["track_id"] for r in manual_rows
               if (r["track_id"], r["sister_pair_id"], r["partner_track"]) not in out_key]
    if missing:
        raise SystemExit(f"ABORT: {len(missing)} manual sister rows would be lost: {missing[:5]}")
    # non-destructive: backup existing, write temp, verify, atomic swap
    if os.path.exists(OUTCSV):
        import shutil, time
        shutil.copy2(OUTCSV, OUTCSV + time.strftime(".%Y%m%d_%H%M%S.bak"))
    tmp = OUTCSV + ".tmp"
    with open(tmp, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["track_id", "batch", "sister_pair_id", "partner_track",
                                          "metaphase_median_dist_um", "n_coframes", "basis", "n_paired_tracks_in_cell"])
        w.writeheader(); w.writerows(pair_rows)
    with open(tmp, newline="") as f:
        chk = list(csv.DictReader(f))
    nman = sum(1 for r in chk if (r.get("basis") or "").strip().lower() == "manual")
    if len(chk) != len(pair_rows) or nman != len(manual_rows):
        raise SystemExit(f"ABORT: verify failed ({len(chk)}/{len(pair_rows)} rows, {nman}/{len(manual_rows)} manual)")
    os.replace(tmp, OUTCSV)
    print(f"  preserved {len(manual_rows)} manual rows across {len(manual_batches)} cells")
    return pair_rows, pair_series


if __name__ == "__main__":
    rows, series = build()
    npairs = len({r["sister_pair_id"] for r in rows if r["sister_pair_id"]})
    paired_tracks = sum(1 for r in rows if r["sister_pair_id"])
    lone = sum(1 for r in rows if not r["sister_pair_id"])
    print(f"wrote {len(rows)} paired tracks -> {OUTCSV}")
    print(f"  sister pairs: {npairs}; tracks in a pair: {paired_tracks}; lone paired tracks: {lone}")

    def _save(fig, name, cap, header=None, rows=None):
        fig.tight_layout(); fig.savefig(f"{OUT}/{name}.png", dpi=200, bbox_inches="tight"); plt.close(fig)
        # 2026-08-03: was record_plot(["x"], []) - a placeholder registering an EMPTY data table, so
        # the figure could not be checked against its own data and any _zoom companion was built from
        # nothing. Same bug fixed in kt_phase_split.py on 2026-07-29 and never propagated here.
        try:
            lib.record_plot(name, header or ["x"], rows or [], {"family": "sisters"},
                            script=__file__, caption=cap, source=SRC,
                            key_column=("batch" if header and "batch" in header else None))
        except Exception as _e:
            print("    record_plot(%s) failed: %s" % (name, _e))
        print("  " + name)

    # per-frame k-k (sister centroid-to-centroid) distance table
    kkrows = []
    for b, spid, a, c, med, n, ser in series:
        for f, ta, kk, phase in ser:
            kkrows.append(dict(batch=b, sister_pair_id=spid, track_a=a, track_c=c, frame=f,
                               t_sec=round(ta, 2), phase=phase, kk_dist_um=round(kk, 4)))
    with open(f"{ROOT}/annotations/KT_SISTER_KK_20260723.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["batch", "sister_pair_id", "track_a", "track_c", "frame", "t_sec", "phase", "kk_dist_um"])
        w.writeheader(); w.writerows(kkrows)
    print(f"  wrote {len(kkrows)} per-frame k-k distances -> annotations/KT_SISTER_KK_20260723.csv")

    # 1) sister separation over time (breathing)
    fig, ax = plt.subplots(figsize=(7.6, 5.0))
    for b, spid, a, c, med, n, ser in series:
        if len(ser) < 3: continue
        ser = sorted(ser, key=lambda s: s[1]); t = np.array([s[1] for s in ser]) / 60.0; d = np.array([s[2] for s in ser])
        ax.plot(t, d, "-", lw=1, alpha=0.7)
    ax.axhspan(1, 3, color="#3b6fb6", alpha=0.08)
    ax.set_xlabel("time (min, t=0 at first ablation)"); ax.set_ylabel("sister–sister separation (µm)")
    ax.set_title(f"Sister-kinetochore separation over time ({len(series)} pairs)", loc="left", fontweight="bold", fontsize=11)
    _save(fig, "G6sis_separation_time", "Sister separation over time",
          header=["batch","sister_pair_id","t_min_from_first_ablation","separation_um"],
          rows=[[b, spid, round(sv[1]/60.0,4), round(float(sv[2]),5)]
                for b, spid, a, c, med, nn, ser in series if len(ser) >= 3 for sv in sorted(ser, key=lambda z: z[1])])

    # 2) metaphase median sister distance distribution
    md = [r["metaphase_median_dist_um"] for r in rows if r["metaphase_median_dist_um"] != ""]
    md = [float(x) for x in md]
    fig, ax = plt.subplots(figsize=(6.0, 5.0))
    if md:
        ax.hist(md, bins=np.arange(0, MAX_SIS_UM + 0.5, 0.35), color="#3b6fb6", alpha=0.8, edgecolor="white")
        ax.axvspan(1, 3, color="#2ca02c", alpha=0.1)
        ax.text(0.98, 0.98, f"N pairs={len(md)}\nmedian={np.median(md):.2f}µm\nIQR {np.percentile(md,25):.2f}-{np.percentile(md,75):.2f}",
                transform=ax.transAxes, ha="right", va="top", fontsize=7.5, family="monospace",
                bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="#bbb", alpha=0.85))
    ax.set_xlabel("metaphase median sister separation (µm)"); ax.set_ylabel("# sister pairs")
    ax.set_title("Sister-pair separation (metaphase)", loc="left", fontweight="bold", fontsize=11)
    _save(fig, "G6sis_distance_hist", "Sister-pair metaphase separation",
          header=["metaphase_median_separation_um"], rows=[[round(float(v),5)] for v in md])

    # 3) paired-mark pattern per cell (how many paired tracks -> how many sister pairs)
    bycell = collections.defaultdict(lambda: [0, 0])
    seenp = set()
    for r in rows:
        bycell[r["batch"]][0] = int(r["n_paired_tracks_in_cell"])   # manual rows come back as str
        if r["sister_pair_id"] and r["sister_pair_id"] not in seenp:
            seenp.add(r["sister_pair_id"]); bycell[r["batch"]][1] += 1
    fig, ax = plt.subplots(figsize=(7.0, 5.0))
    xs = [v[0] for v in bycell.values()]; ys = [v[1] for v in bycell.values()]
    jit = (np.random.RandomState(0).rand(len(xs)) - 0.5) * 0.2
    ax.scatter(np.array(xs) + jit, ys, s=50, color="#3b6fb6", alpha=0.7, edgecolor="white")
    ax.plot([0, max(xs + [1])], [0, max(xs + [1]) / 2], ls=":", color="#999", label="2 tracks : 1 pair")
    ax.set_xlabel("# paired tracks in cell"); ax.set_ylabel("# sister pairs found")
    ax.set_title(f"Paired-track pattern to sister pairs (N={len(bycell)} cells)", loc="left", fontweight="bold", fontsize=10.5)
    ax.legend(fontsize=8)
    _save(fig, "G6sis_pattern_per_cell", "Paired pattern to sister pairs",
          header=["n_paired_tracks","n_sister_pairs"], rows=[[int(a), int(b2)] for a, b2 in zip(xs, ys)])

    # 4) k-k (sister separation) BY PHASE — should widen at anaphase (segregation)
    PHASE = ["prometaphase", "metaphase", "anaphase"]
    PHCOL = {"prometaphase": "#7a7a7a", "metaphase": "#3b6fb6", "anaphase": "#d1495b"}
    g = {p: [r["kk_dist_um"] for r in kkrows if r["phase"] == p] for p in PHASE}
    fig, ax = plt.subplots(figsize=(6.6, 5.0))
    dmax = max((max(v) for v in g.values() if v), default=1)
    for i, p in enumerate(PHASE):
        d = g[p]
        if len(d) < 3: continue
        lib.journal_violin(ax, d, i, PHCOL[p], alpha=0.28, lw=1.0, min_n=3)
        ax.scatter(np.full(len(d), i)+(np.random.RandomState(i).rand(len(d))-0.5)*0.2, d, s=lib.VIOLIN_DOT_S, color=PHCOL[p], alpha=lib.VIOLIN_DOT_ALPHA_DENSE, lw=0)
        ax.hlines(np.median(d), i-0.34, i+0.34, color=PHCOL[p], lw=2.4)
        ax.text(i, dmax*1.02, f"med {np.median(d):.2f}µm\nN={len(d)}", ha="center", va="bottom", fontsize=7.5)
    ax.set_xticks(range(len(PHASE))); ax.set_xticklabels(PHASE, fontsize=9); ax.set_ylabel("sister k–k distance (µm)")
    ax.set_ylim(top=dmax*1.25)
    kt_stats.add_group_stats(ax, g, PHASE, loc="upper left")
    ax.set_title("Sister k–k distance by mitotic phase", loc="left", fontweight="bold", fontsize=11)
    _save(fig, "G6sis_kk_by_phase", "Sister k-k distance by phase",
          header=["phase","kk_um"], rows=[[ph, round(float(v),5)] for ph in PHASE for v in g.get(ph, [])])

    # 5) k-k distribution (all frames) with metaphase median
    fig, ax = plt.subplots(figsize=(6.4, 5.0))
    allkk = [r["kk_dist_um"] for r in kkrows]
    metakk = [r["kk_dist_um"] for r in kkrows if r["phase"] == "metaphase"]
    if allkk:
        ax.hist(allkk, bins=np.arange(0, max(allkk) + 0.5, 0.4), color="#3b6fb6", alpha=0.55, edgecolor="white", label="all frames")
        if metakk:
            ax.hist(metakk, bins=np.arange(0, max(allkk) + 0.5, 0.4), color="#2ca02c", alpha=0.6, edgecolor="white", label="metaphase")
        ax.text(0.98, 0.98, f"all: N={len(allkk)}, med={np.median(allkk):.2f}µm\nmetaphase: N={len(metakk)}, med={np.median(metakk):.2f}µm" if metakk else f"N={len(allkk)}",
                transform=ax.transAxes, ha="right", va="top", fontsize=7.5, family="monospace",
                bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="#bbb", alpha=0.85))
    ax.set_xlabel("sister k–k distance (µm)"); ax.set_ylabel("# frames"); ax.legend(fontsize=8)
    ax.set_title("Sister k–k distance distribution", loc="left", fontweight="bold", fontsize=11)
    _save(fig, "G6sis_kk_distribution", "Sister k-k distance distribution",
          header=["subset","kk_um"], rows=[["all", round(float(v),5)] for v in allkk]
               + [["metaphase", round(float(v),5)] for v in (metakk or [])])
    print("done sisters")
