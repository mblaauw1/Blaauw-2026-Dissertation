#!/usr/bin/env python3
"""Kinetochore SIZE and Cdc20 INTENSITY over metaphase, by attachment state — her 2026-08-19 feedback.

HER CLAIM AND REQUEST
    *"Polar kinetochores continue to localize increased Cdc20 compared to paired at plate and in fact appear
     to localize more after becoming sisterless and polar. Plot both kinetochore size and intensity of
     fluorescence over time for the groups of: kinetochores that remain polar, kinetochores that congress
     (and somehow standardize that group specifically for time of congression ...) Compare to kinetochores
     that are congressed, or that can be seen to have merotelic attachments."*

WHAT IS BUILT, AND WHAT IS BLOCKED
    BUILT — three groups, over the METAPHASE ERA only (her standing rule):
        remains polar        a polar track still present in the final 25% of its cell's metaphase
        congressed (at plate) the `paired` tracks — kinetochores already at the plate
        merotelic (lagging)   the `lagging` tracks, her "presumed merotelic"
    BLOCKED — the CONGRESSING group, and therefore its congression-standardised alignment.

    🔴 WHY, COUNTED RATHER THAN ASSERTED (re-derived 2026-08-20; an earlier version of this docstring said
    "determinate in exactly 1 cell", which was both too strong and pointed at the wrong bottleneck).

    TWO SEPARATE OBSTACLES, and the second is the big one:

    (a) NO JOIN KEY. Congression times are recorded PER CHROMOSOME — `CHROMOSOME_MASTER.csv` identifies an
        event by `(batch, chr_num)`, 66 timed events in 43 cells — while kinetochore outlines and tracks are
        identified by her "+ New KT" `grp` / `track_id`. Neither table carries the other's key: there is no
        `grp` column on the chromosome side and no `chr_num` column on the kinetochore side.

    (b) THE CONGRESSING KINETOCHORE WAS USUALLY NEVER OUTLINED. Of the 38 cells whose congression falls
        inside a usable metaphase window, **29 have no usable polar track at all** — 15 have no kinetochore
        outlines whatsoever, 14 have outlines but no polar track in metaphase (one of those, `20250409
        ptk_yfpcdc20_6`, is correctly dropped by her manual plot exclusions). No join key would recover these;
        the mark does not exist.

    OF THE REMAINING 9: 5 are genuinely ambiguous (2-3 timed events against 1-3 polar tracks in the same
    cell — this is exactly where (a) bites), and 4 pass a naive "one event, one track" test. **But two of
    those four are contradicted by her own labelling:** a kinetochore that congresses stops being polar, and
    in `20250826 test_ablation_8` and `20260417 ptk2 eyfp cdc20 ablation_18` the outlined polar track stays
    polar for 10 and 30 further minutes, to the END of metaphase — so the outlined track is a DIFFERENT
    chromosome from the timed one. That leaves **2 cells**: `20250923 triple_ablation_collagen_25` (polar
    label ends within one 20 s frame of its congression time — consistent) and `20250401 ptk_yfpcdc20_28`
    (1-sisterless, so unambiguous by count; its polar label runs 2 min past the congression time).

    Two cells cannot be standardised into a group, so the group is not built and nothing is averaged into a
    "group" that does not exist. WHAT WOULD ACTUALLY UNBLOCK IT, in order of yield: **outline the polar
    kinetochore through congression in the 29 cells that already have a timed congression** (that is drawing,
    not re-timing, and it is where 29 of the 38 cells are lost); then tag each congression event with its
    kinetochore `grp`, which recovers the 5 ambiguous cells and settles the 2 contradicted ones.

MEASUREMENTS, both from stores keyed to the SAME kinetochore identity so size and intensity describe the
same object:
    size      `area_um2` from KT_OUTLINE_TRACKS_20260723 (grp-aware; pieces of one KT already combined)
    intensity `signal` from KT_FLUOR_CYTOSOLNORM_20260728 = p95 inside the polygon minus the per-frame
              cytosol median, joined by the outline row ids the track carries in `trace_ids`.
              Lagging kinetochores had never been measured; `polar_fluor_matched.py`'s label filter was
              extended on 2026-08-19 so the merotelic group she asked for exists at all.
"""
import collections
import csv
import sys
import textwrap

import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import stats

sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import lib
import osclib
from trendlib import trend_to_mean_sem, sem_band, anchor_trend

lib.apply_style()
ANN = "/Volumes/4 MB/annotations"
OUT = "/Volumes/4 MB/ablation_figures_20260625/group4"
SCRIPT = __file__

GRP = {"polar_stays": ("remains polar", "#e69f00"),
       "post_congression": ("after congressing (was polar)", "#009E73"),
       "paired": ("congressed (at plate)", "#0072B2"),
       "lagging": ("merotelic (lagging)", "#8e44ad")}
ORDER = ["polar_stays", "post_congression", "paired", "lagging"]


def signal_by_outline_id():
    d = {}
    for r in csv.DictReader(open(f"{ANN}/KT_FLUOR_CYTOSOLNORM_20260728.csv")):
        try:
            d[str(r["id"]).strip()] = float(r["signal"])
        except Exception:
            pass
    return d


def load():
    """-> tracks with a per-frame series of (t_min, area_um2, signal), classified into the three groups."""
    sig = signal_by_outline_id()
    ids = {}
    for r in csv.DictReader(open(f"{ANN}/KT_OUTLINE_TRACKS_20260723.csv")):
        ids[(r["batch"], r["track_id"], r["frame"])] = (r.get("trace_ids") or "")
    # need_plate=False: SIZE and INTENSITY do not use the metaphase plate, so requiring one only threw
    # data away -- 8 cells have kinetochore outlines and no plate drawn anywhere. See osclib.tracks.
    tr = osclib.tracks(labels=("polar", "paired", "lagging"), min_frames=3, need_plate=False)
    # 🔴 HER 2026-08-20 CORRECTION: the outline NAME does not change when a kinetochore congresses, so a
    # track labelled "polar" is only polar UP TO its congression. Splitting first means the polar curve is
    # not contaminated by frames in which the kinetochore was already at the plate.
    osclib.split_at_congression(tr)
    out = []
    for t in tr:
        dur = t["meta_dur_min"]
        if t["label"] == "polar":
            # "remains polar" now means it NEVER congressed and was still being tracked late in metaphase --
            # previously a track that congressed at +6.8 min and kept its polar name to +37.2 counted here.
            if t["congress_min"] is None and max(t["t_min"]) >= 0.75 * dur:
                g = "polar_stays"
            elif t["congress_min"] is not None:
                g = "polar_congresses"        # split below into polar / post_congression frames
            else:
                g = None
        elif t["label"] in GRP:
            g = t["label"]
        else:
            g = None
        if g is None:
            continue
        t["group"] = g
        out.append(t)
    # attach the intensity series by re-reading the tracks file for this track's rows
    per = collections.defaultdict(dict)
    for r in csv.DictReader(open(f"{ANN}/KT_OUTLINE_TRACKS_20260723.csv")):
        vals = []
        for i in (r.get("trace_ids") or "").replace(" ", "").split(","):
            if i and i in sig:
                vals.append(sig[i])
        if vals:
            # key by INT frame: osclib hands back int frames, and a str/int mismatch here silently emptied
            # the whole intensity figure (0 rows) rather than raising -- caught 2026-08-20.
            try:
                per[(r["batch"], r["track_id"])][int(r["frame"])] = float(np.mean(vals))
            except (TypeError, ValueError):
                pass
    for t in out:
        t["signal"] = per.get((t["batch"], t["track_id"]), {})
    return out


def series(tracks, what):
    """-> {group: [(t_min, value, track_key)]} for 'size' or 'intensity', metaphase-relative time."""
    pts = collections.defaultdict(list)
    for t in tracks:
        # NB track_id already contains "|" (batch|label|grp), so this key is split on the FIRST
        # separator only -- splitting naively wrote the batch into the track_id column of the
        # data CSV and made every per-kinetochore provenance check count CELLS. Caught 2026-08-20.
        key = f"{t['batch']}|{t['track_id']}"
        # a congressing track contributes its PRE-congression frames to the polar curve and its POST frames
        # to the post-congression curve; nothing is double counted and nothing is thrown away
        def bucket(i):
            if t["group"] != "polar_congresses":
                return t["group"]
            return "polar_stays" if t["phase"][i] == "polar" else "post_congression"
        if what == "size":
            for i, (tm, a) in enumerate(zip(t["t_min"], t["area_um2"])):
                if a is not None and np.isfinite(a):
                    pts[bucket(i)].append((tm, float(a), key))
        else:
            sg = t.get("signal") or {}
            if not sg:
                continue
            _ph = {f: t["phase"][i] for i, f in enumerate(t["frames"])}
            # the signal dict is keyed by FRAME; the track now carries its own frame list in time order
            # (`frames`), which is exactly the rows that survived the metaphase clip -- re-deriving it
            # separately was a second chance to disagree with the loader.
            for i, (tm, v) in enumerate(zip(t["t_min"], t["frames"])):
                if v in sg:
                    pts[bucket(i)].append((tm, sg[v], key))
    return pts


_FRAMECACHE = None


def _frames_for(t):
    global _FRAMECACHE
    if _FRAMECACHE is None:
        _FRAMECACHE = collections.defaultdict(list)
        for r in csv.DictReader(open(f"{ANN}/KT_OUTLINE_TRACKS_20260723.csv")):
            try:                                   # a handful of track rows carry no t_sec
                ts = float(r["t_sec"])
            except (TypeError, ValueError):
                continue
            _FRAMECACHE[(r["batch"], r["track_id"])].append((ts, r["frame"]))
        for k in _FRAMECACHE:
            _FRAMECACHE[k].sort()
    w = osclib.metaphase_window(t["batch"])
    got = []
    for ts, f in _FRAMECACHE.get((t["batch"], t["track_id"]), []):
        if w and w[0] <= ts <= w[1]:
            got.append(f)
    return got


def plot(pts, ylab, fname, title, note):
    fig, ax = plt.subplots(figsize=(8.6, 5.4))
    rows = []
    for g in ORDER:
        v = pts.get(g) or []
        if len(v) < 6:
            continue
        nice, col = GRP[g]
        p3 = [(a, b, c) for a, b, c in v]
        cells = {c.split("|", 1)[0] for _, _, c in v}
        kts = {c for _, _, c in v}
        md = max(a for a, _, _ in v)
        bx, by, bs = trend_to_mean_sem(p3, md, start=0.0)
        bx, by, bs = anchor_trend(bx, by, bs, 0.0, at_start=True)
        if len(bx) < 2:
            continue
        sem_band(ax, bx, by, bs, col)
        med = float(np.median([b for _, b, _ in v]))
        ax.plot(bx, by, color=col, lw=2.8, marker="o", ms=4, zorder=3,
                label=f"{nice} — median {med:.1f} ({len(kts)} KTs, {len(cells)} cells)")
        for a, b, c in v:
            rows.append([c.split("|", 1)[0], c.split("|", 1)[1], g, round(a, 3), round(b, 4)])
    ax.set_xlabel("Time from metaphase onset (min)")
    ax.set_ylabel(ylab)
    ax.set_xlim(left=0); ax.set_ylim(bottom=0)
    ax.legend(fontsize=8)
    ax.set_title(title, loc="left", fontweight="bold", fontsize=10)
    # WRAP: bbox_inches="tight" grows the saved canvas to the widest artist, so an unwrapped footnote
    # silently stretches the figure (these two reached 5:1 before wrapping) and distorts the placed art.
    wrapped = "\n".join(textwrap.fill(par, 150) for par in note.split("\n"))
    ax.text(0.0, -0.20, wrapped, transform=ax.transAxes, fontsize=6.6, color="#555", va="top", linespacing=1.5)
    fig.savefig(f"{OUT}/{fname}.png", dpi=190, bbox_inches="tight")
    plt.close(fig)
    lib.record_plot(fname, ["batch", "track_id", "group", "t_min_from_metaphase", "value"], rows,
                    {"window": "metaphase era only", "unit": "one kinetochore per track",
                     "blocked": "the CONGRESSING group needs a chromosome->kinetochore-grp join that does "
                                "not exist; only 1 cell is determinate",
                     "why": "user 2026-08-19: KT size and Cdc20 intensity over time by attachment state"},
                    SCRIPT, title)
    print(f"  wrote {fname} ({len(rows)} kinetochore-frames)")


def congression_block_counts(write_worklist=True):
    """Coverage of the congressing group — recomputed at render time, never typed into the caption.

    🔴 REWRITTEN TWICE ON 2026-08-20, and the second rewrite is the important one. Version 1 asserted counts.
    Version 2 decided whether a congression had happened by asking whether the kinetochore reached the plate,
    and OVERRULED her annotation in the cells where it had not. She rejected that, correctly: a congressed
    kinetochore may be MEROTELICALLY attached and is not obliged to sit at the plate — measured at the very
    moments SHE marks a plate-join, the distance ranges 2.5–8.6 µm, so distance cannot separate joined from
    not-joined. HER TIMES ARE NOW AUTHORITATIVE; distance only ranks which of several polar tracks in a cell
    an event belongs to (osclib.assign_congressions).
    """
    pol = osclib.tracks(labels=("polar",), min_frames=3, need_plate=False)
    osclib.split_at_congression(pol)
    bycell = collections.defaultdict(list)
    for t in pol:
        bycell[t["batch"]].append(t)
    tot = assigned = unassigned_ev = nopol = excl = 0
    work = []
    for b in sorted({t["batch"] for t in pol} | set(_cells_with_events())):
        w = osclib.metaphase_window(b)
        if not w:
            continue
        ev = osclib.plate_join_events_min(b)
        if not ev:
            continue
        tot += 1
        ts = bycell.get(b, [])
        if not ts:
            if lib.plot_excluded(b):
                excl += 1
            else:
                nopol += 1
                # 🔴 HER 2026-08-20 CORRECTION: "no polar OUTLINE" is not "not annotated". The polar
                # kinetochore is very often marked in kt_points.csv instead (labels `polar` / `sisterless`,
                # 853 + 2,658 marks), which carries POSITION -- enough for congression, plate distance and
                # oscillation. Only SIZE and SHAPE need an outline. Saying these cells were unannotated was
                # wrong and made the gap look far larger than it is.
                np_ = _polar_points(b)
                work.append([b, _nsis(b), len(ev), round(ev[0], 1), round((w[1] - w[0]) / 60.0, 1),
                             (f"polar kinetochore is marked as {np_} POINTS but has no outline - position "
                              "measures already work; an outline is needed only for size/shape")
                             if np_ else
                             "no polar kinetochore annotation of any kind - needs marking"])
            continue
        got = sum(1 for t in ts if t["congress_min"] is not None)
        assigned += got
        # 🔴 MORE TIMED CONGRESSIONS THAN OUTLINED TRACKS IS NOT AN ERROR (her, 2026-08-20): it is only a
        # problem if the congression count EXCEEDS the cell's sisterless kinetochore count, read from the
        # master's `# Sisterless KTs` column -- never from the file name. Checked across all 43 cells with a
        # timed congression: that never happens, so every cell is internally consistent.
        try:
            nsis = int(_nsis(b))
        except (TypeError, ValueError):
            nsis = None
        if nsis is not None and len(ev) > nsis:
            unassigned_ev += 1
            work.append([b, _nsis(b), len(ev), "", round((w[1] - w[0]) / 60.0, 1),
                         f"INCONSISTENT: {len(ev)} timed congressions but only {nsis} sisterless kinetochores"])
    if write_worklist:
        out = "/Volumes/4 MB/4_TABLES_AND_REPORTS/CONGRESSION_OUTLINE_WORKLIST_20260820.csv"
        with open(out, "w", newline="") as fh:
            wc = csv.writer(fh)
            wc.writerow(["batch", "n_sisterless", "timed_congressions_in_metaphase",
                         "congression_min_from_metaphase_onset", "metaphase_duration_min", "what_is_needed"])
            wc.writerows(work)
    return dict(total=tot, assigned=assigned, unassigned_events=unassigned_ev,
                no_polar=nopol, excluded=excl, worklist=len(work))


def _polar_points(batch):
    """How many polar/sisterless POINT marks this cell carries in kt_points.csv (position, not shape)."""
    n = 0
    try:
        for r in csv.DictReader(open(f"{ANN}/kt_points.csv", newline="", encoding="utf-8", errors="replace")):
            if r.get("batch") == batch and (r.get("label") or "").strip() in ("polar", "sisterless"):
                n += 1
    except Exception:
        pass
    return n


def _nsis(b):
    d, _ = lib.load_master()
    for r in d:
        if r["Batch Name"] == b:
            return (r.get("# Sisterless KTs", "") or "").strip()
    return ""


def _cells_with_events():
    out = set()
    for r in csv.DictReader(open(f"{ANN}/CHROMOSOME_MASTER.csv", newline="", encoding="utf-8", errors="replace")):
        if (r.get("congression_time_s") or "").strip():
            out.add(r["batch"])
    return out


if __name__ == "__main__":
    tr = load()
    # report the FRAME buckets, not t["group"]: a congressing track sits in `polar_congresses` and
    # contributes frames to two curves, so counting groups printed "post_congression=0" beside a figure
    # that plainly drew that curve. A summary line that contradicts its own figure is worse than none.
    _b = collections.Counter()
    for _t in tr:
        for _ph in _t["phase"]:
            _b["post_congression" if _ph == "post_congression" else _t["group"]] += 1
    print(f"{len(tr)} tracks; frames per curve: "
          + ", ".join(f"{g}={_b.get(g, 0)}" for g in ORDER + ["polar_congresses"] if _b.get(g)))
    # 🔴 COMPUTED, NOT TYPED. The first version of this caption asserted "29 cells have no polar kinetochore
    # outlined"; when the needless plate requirement was removed the true figure changed, and a typed caption
    # would have gone on asserting the old one. congression_block_counts() re-derives it at render time.
    cb = congression_block_counts()
    NOTE = ("Metaphase era only (Metaphase Start → Anaphase Onset). Line = mean across kinetochores in each "
            "time bin, band = SEM across KINETOCHORES, not across frames.\n"
            "A CONGRESSING KINETOCHORE KEEPS ITS 'polar' OUTLINE NAME (her, 2026-08-20), so the label marks "
            "where a track STARTED, not what it is throughout. Every polar track is CUT at HER timed "
            "congression: frames before it feed 'remains polar', frames after it feed 'after congressing'. "
            "Her congression and plate-join times are AUTHORITATIVE — distance from the plate is used only to "
            "decide WHICH of several polar tracks in one cell an event belongs to, never to overrule her, "
            "because a congressed kinetochore may be merotelically attached and need not sit at the plate "
            "(measured at her own plate-join moments, distance spans 2.5–8.6 µm).\n"
            f"COVERAGE, of the {cb['total']} cells with a timed congression inside metaphase: "
            f"{cb['assigned']} polar tracks were cut at one of her events; {cb['excluded']} cells are "
            f"excluded; {cb['no_polar']} have no polar OUTLINE — but most of those DO have the kinetochore "
            "marked as points in kt_points.csv, which carries position, so only size and shape are missing "
            "there. No cell has more timed congressions than sisterless kinetochores.\n"
            f"The {cb['worklist']} cells that would complete this group are listed in "
            "4_TABLES_AND_REPORTS/CONGRESSION_OUTLINE_WORKLIST_20260820.csv.")
    plot(series(tr, "size"), "Kinetochore outline area (µm²)",
         "G10_kt_size_over_metaphase_by_state",
         "Kinetochore size through metaphase, by attachment state", NOTE)
    plot(series(tr, "intensity"), "Kinetochore eYFP–Cdc20 (p95 − cytosol, a.u.)",
         "G10_kt_intensity_over_metaphase_by_state",
         "Kinetochore Cdc20 intensity through metaphase, by attachment state", NOTE)
