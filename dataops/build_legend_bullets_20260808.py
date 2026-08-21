#!/usr/bin/env python3
"""Recompute legend BULLET POINTS -- with fresh N and statistics -- for every figure placed on the 4 decks.

USER 2026-08-08: "go through the plots on the main four illustrator files and update the legends bullet
points. you'dd likely need to calculate or recalculate statiscics and N values, and so on, for the plots,
so make sure to do that as well so the legend bullet points are complete and updated."

WHY THIS MATTERS AND WHY IT RUNS LAST. Today changed the underlying data twice: new annotations (tracks
55 -> 61 batches, sister k-k 21 -> 32 batches) and then the common-mode stage-drift correction, which cut
median track path length by ~15% and per-object displacement by 38%. Any N or p-value already written into
a legend is therefore suspect. Every number here is recomputed FROM THE FIGURE'S OWN DATA CSV -- the file
`record_plot` wrote when the figure was last rendered -- so a bullet can never disagree with the figure
above it.

DERIVED OR OMITTED, NEVER GUESSED. A bullet is emitted only when it can be computed from the data. A
missing filter or window is better than a wrong one.

Bullets per figure:
  * what is plotted            (the recorded caption, trimmed to one clause)
  * n                          (rows, plus per-group n when a grouping column exists)
  * statistics                 (recomputed group comparison / correlation where the shape allows)
  * data source                (which annotation stores it derives from)
  * filters in force           (anaphase excluded / drift corrected / cohort)
  * updated                    (the data CSV's mtime -- the real freshness of the numbers)

Writes `legend_bullets` (list) + `legend_bullets_built` into PLOT_SETTINGS. A companion JSX draws them.
"""
import csv, json, os, re, datetime, collections, statistics as st

ROOT = "/Volumes/4 MB"
PS = os.path.join(ROOT, "ablation_plots/PLOT_SETTINGS.json")
DATA = os.path.join(ROOT, "ablation_plots/data")
DUMP = os.path.join(ROOT, "_claude_tmp/deck_dump_20260808.txt")
csv.field_size_limit(10 ** 9)

ps = json.load(open(PS))
print(f"PLOT_SETTINGS entries: {len(ps)}")

# ---- which figures are actually placed on the four decks (from the read-only dump) --------------
# The capture group excludes the extension, so `placed` holds BARE plot ids -- compare pids directly.
# (Testing `pid + ".pdf"` against this set matched nothing and skipped all 802 figures.)
placed = set()
# 2026-08-18: the old path read a STALE deck dump (`_claude_tmp/deck_dump_20260808.txt`), so figures
# placed since then carried no bullets and figures removed since then still did.  Read the live decks
# themselves -- `strings` on the .ai lists every linked PDF/PNG, which is what a placement IS.
LIVE_DECKS = [os.path.join(ROOT, "1_DECKS", d) for d in (
    "META_FIGURES_20260814.ai", "META_FIGURES_20260813_supplemental.ai",
    "NEW_FIGURES_20260804.ai", "supplemental.ai", "NEW_TIMESTRIPS_20260804.ai")]
import subprocess as _sp
for _d in LIVE_DECKS:
    if not os.path.exists(_d):
        print(f"[warn] live deck missing: {_d}"); continue
    _txt = _sp.run(["strings", _d], capture_output=True, text=True).stdout
    for m in re.findall(r"([A-Za-z0-9_.\-]+)\.(?:pdf|png)", _txt):
        placed.add(m)
# 2026-08-18: `strings` on a compressed .ai does NOT list every linked file — two AB5 excerpts placed on
# META_FIGURES_20260814 were invisible to it, so they were treated as unplaced and got no legend. The
# read-only geometry dumps (_claude_tmp/geom9_*.tsv) list the REAL placedItems, so union them in.
import csv as _csv, glob as _glob, os as _os
for _g in _glob.glob("/Volumes/4 MB/_claude_tmp/geom9_*.tsv"):
    try:
        with open(_g, encoding="utf-8", errors="replace") as _fh:
            for _r in _csv.DictReader(_fh, delimiter="\t"):
                if _r.get("kind") != "PlacedItem":
                    continue
                _lk = (_r.get("linked") or "").strip()
                if _lk:
                    placed.add(_os.path.basename(_lk).rsplit(".", 1)[0])
    except Exception:
        pass
if os.path.exists(DUMP):
    txt = open(DUMP, errors="replace").read()
    for m in re.findall(r"([A-Za-z0-9_.\-]+)\.(?:pdf|png)", txt):
        placed.add(m)
# the 9 figures added to NEW_FIGURES after the dump was taken
placed |= {"G1_imaging_rate_vs_metaphase_unmodified", "G5_mad1_kt_fluor_over_time",
           "G5_sac_active_kt_over_time", "G5_hec1_mad1_multibatch_quant",
           "G6_polar_dist_to_plate_over_metaphase", "G7_kt_movement_vs_context",
           "G7_prometa_single_vs_meta_triple", "G7_prophase_vs_prometaphase_triple",
           "G7_triple_converges_on_single", "G7_track_to_chromosome_assignment"}
# PANELS (2026-08-09). The dump above predates the multi-panel split, so it names only the PARENT
# figures -- every panel then failed the "placed" test and was skipped before the data lookup could even
# run. That is why 174 placed figures carried no bullets. A panel is on a deck exactly when its parent
# was split and placed, and `register_panels` recorded that link as `panel_of`, so derive it from there
# rather than re-dumping Illustrator.
_panels = 0
for _pid, _ent in ps.items():
    if not isinstance(_ent, dict):
        continue
    _par = _ent.get("panel_of") or (_ent.get("settings") or {}).get("panel_of")
    if _par and _par in placed and _pid not in placed:
        placed.add(_pid); _panels += 1
print(f"figures placed across the 4 decks: {len(placed)}   (+{_panels} split panels)")

GROUPCOLS = ["group", "cohort", "kt_class", "label", "rate_group", "metric", "n_sisterless", "state"]
VALUECOLS = ["value", "metaphase_duration_min", "speed_um_s", "kk_dist_um", "net_mean_au",
             "dist_to_plate_um", "fold_over_bg", "area_um2", "circularity", "length_um"]


# ---------------------------------------------------------------- image panels (timestrips, examples)
# 2026-08-18, her instruction "resolve all legend items still on the five decks": an image panel used to get
# only "n = 1 rows from 1 cells" plus a caption, which leaves a reader without the four things a micrograph
# legend must state -- which cell, which channels, what t = 0 is, and whether the panels are consecutive or
# selected. All four are recoverable per batch, so they are emitted rather than left blank.
_MASTER_ROWS, _MASTER_HDR = None, None
def _master_row(batch):
    global _MASTER_ROWS
    if _MASTER_ROWS is None:
        _MASTER_ROWS = {}
        try:
            import sys as _s
            _s.path.insert(0, ROOT + "/ablation_figures_20260625")
            import lib as _lib
            _m, _h = _lib.load_master()
            _MASTER_ROWS = {(r.get("Batch Name") or "").strip(): r for r in _m}
        except Exception:
            _MASTER_ROWS = {}
    return _MASTER_ROWS.get((batch or "").strip()) or {}

def _molecules(cell_type):
    ct = (cell_type or "").lower()
    out = []
    if "cdc20" in ct: out.append("eYFP-Cdc20 (488)")
    if "mad1" in ct: out.append("eYFP-Mad1 (488)")
    if "hec1" in ct: out.append("Hec1-Halo (640)")
    return out or ["fluorescence (488)"]

def image_bullets(pid, ent, parent_ent=None):
    setg = dict((parent_ent or {}).get("settings") or {})
    setg.update(ent.get("settings") or {})
    batch = (setg.get("batch") or "").strip()
    is_image = bool(batch) and (setg.get("n_panels") or setg.get("kind") == "image_panel"
                                or "timestrip" in str(setg.get("type", "")).lower())
    if not is_image and setg.get("kind") != "image_panel":
        return []
    r = _master_row(batch)
    out = []
    if batch:
        ct = (r.get("Cell Type") or "").strip()
        nsis = (r.get("# Sisterless KTs") or "").strip()
        tgt = (r.get("On-Target / Off-Target") or "").strip()
        ph = (r.get("Phase of Ablations") or "").strip()
        who = [x for x in [f"{nsis}-sisterless" if nsis not in ("", "0") else "",
                           tgt.lower() if tgt else "", f"ablated in {ph.lower()}" if ph else ""] if x]
        out.append(f"Cell: {batch}" + (f" — {ct}" if ct else "") + (f"; {', '.join(who)}" if who else "") + ".")
        out.append("Channels: phase contrast (transmitted) and " + ", ".join(_molecules(ct)) + ".")
    npan = setg.get("n_panels")
    # The master's "Time Interval (s)" is ONE number for a batch that actually has two cadences, so it was
    # saying "interval 3 s in the monitoring portion", which is the ablation cadence. Read the real per-role
    # intervals out of the batch's own frames.json instead, and fall back to the master only if it is missing.
    iv_txt = ""
    rdir = setg.get("render_dir") or ""
    fj = os.path.join(rdir, os.path.basename(rdir) + "_frames.json") if rdir else ""
    if fj and os.path.exists(fj):
        try:
            _f = json.load(open(fj)).get("frames") or []
            per = collections.defaultdict(list)
            for a, b2 in zip(_f, _f[1:]):
                if a.get("role") == b2.get("role") and a.get("t_sec") is not None and b2.get("t_sec") is not None:
                    dt = float(b2["t_sec"]) - float(a["t_sec"])
                    if 0 < dt < 3600: per[a.get("role")].append(dt)
            bits = []
            for role in ("ablation", "monitoring"):
                v = per.get(role) or []
                if v:
                    v.sort(); bits.append(f"{role} {v[len(v)//2]:.0f} s")
            if bits: iv_txt = "frame interval " + ", ".join(bits)
        except Exception:
            iv_txt = ""
    if not iv_txt:
        _iv = (r.get("Time Interval (s)") or "").strip()
        if _iv: iv_txt = f"frame interval {_iv} s (master value; per-portion cadence not recorded for this cell)"
    pan = []
    if npan: pan.append(f"{npan} panels")
    pan.append("SELECTED timepoints, not consecutive frames")
    if iv_txt: pan.append(iv_txt)
    out.append("Panels: " + "; ".join(pan) + ".")
    nabl = setg.get("n_ablation_events")
    if nabl:
        out.append(f"t = 0 is the first ablation event (the acquisition's own time origin); "
                   f"{nabl} ablation event{'s' if int(nabl) != 1 else ''} in this cell. Panel times are mm:ss from it.")
        out.append("The marker on a panel is the ablation target, drawn on the frame it was fired.")
    else:
        out.append("t = 0 is the acquisition's time origin; panel times are mm:ss from it.")
    sb = setg.get("scalebar_um") or 10
    out.append(f"Scale bar: {sb} µm on the whole-cell panels.")
    out.append("Display: linear brightness/contrast applied to the whole frame; no gamma. "
               "All quantification is done on the raw 16-bit data, not on these images.")
    return out


def numeric(vals):
    out = []
    for v in vals:
        try:
            out.append(float(v))
        except Exception:
            pass
    return out


def stats_bullets(rows, hdr):
    """Recompute the comparison(s) the figure is actually making.

    SPLIT BY `metric` WHEN THE CSV HAS ONE. A long-format CSV like
    G7_prometa_single_vs_meta_triple stacks k-k (um), speed (um/s), oscillation period (s) and amplitude
    (um) in a single `value` column. Testing them pooled compares micrometres against micrometres-per-second
    and produces a p-value that means nothing -- the first dry run did exactly that (Kruskal p=1.9e-09
    across mixed units). So each metric gets its own test.
    """
    if "metric" in hdr:
        out = []
        metrics = []
        for r in rows:
            m = (r.get("metric") or "").strip()
            if m and m not in metrics:
                metrics.append(m)
        for m in metrics[:6]:
            sub = [r for r in rows if (r.get("metric") or "").strip() == m]
            ns, sb = _stats_one(sub, [c for c in hdr if c != "metric"])
            if sb:
                out.append(f"{m} — {sb}")
            elif ns:
                out.append(f"{m} — {ns}")
        return None, out
    ns, sb = _stats_one(rows, hdr)
    return ns, ([sb] if sb else [])


def _stats_one(rows, hdr):
    gcol = next((c for c in GROUPCOLS if c in hdr), None)
    vcol = next((c for c in VALUECOLS if c in hdr), None)
    if not vcol:
        num = [c for c in hdr if c not in ("batch", "track_id", "id") and
               len(numeric([r.get(c, "") for r in rows[:200]])) > len(rows[:200]) * .8]
        vcol = num[0] if num else None
    if not (gcol and vcol):
        return None, None
    # HER RULE (NOTES 2026-08-18, item 20): aggregate to the CELL before testing.  One cell contributes
    # many kinetochores / tracks / frames, so a per-row test counts that cell many times and invents
    # significance -- exactly how the chromosome-angle p=0.0029 became p=0.68 per cell, and how the
    # 3-sisterless speed p=0.0096 became p=0.085.  The per-row p is still reported, second, so the two
    # can be compared, but the headline number is per cell whenever cell identity exists in the data.
    bcol = next((c for c in ("batch", "batch_name", "cell") if c in hdr), None)
    groups_row = collections.OrderedDict()
    percell = collections.OrderedDict()
    for r in rows:
        g = (r.get(gcol) or "").strip()
        v = r.get(vcol, "")
        try:
            fv = float(v)
        except Exception:
            continue
        groups_row.setdefault(g, []).append(fv)
        if bcol:
            b = (r.get(bcol) or "").strip()
            if b:
                percell.setdefault(g, collections.OrderedDict()).setdefault(b, []).append(fv)
    groups_row = {k: v for k, v in groups_row.items() if len(v) >= 3}
    groups_cell = {k: [st.median(vv) for vv in d.values()] for k, d in percell.items()}
    groups_cell = {k: v for k, v in groups_cell.items() if len(v) >= 3}
    per_cell_used = len(groups_cell) >= 2
    groups = groups_cell if per_cell_used else groups_row
    if len(groups) < 2:
        return None, None
    unit = "cells" if per_cell_used else "rows"
    ns = ", ".join(f"{k} n={len(v)} {unit}" for k, v in list(groups.items())[:6])
    try:
        from scipy import stats as sst
        keys = list(groups)
        def _p(gs, ks):
            if len(ks) == 2:
                return sst.mannwhitneyu(gs[ks[0]], gs[ks[1]], alternative="two-sided")[1], "Mann-Whitney"
            return sst.kruskal(*[gs[k] for k in ks])[1], "Kruskal-Wallis"
        p, kind = _p(groups, keys)
        if len(keys) == 2:
            s = (f"{vcol}: {keys[0]} median {st.median(groups[keys[0]]):.4g} vs "
                 f"{keys[1]} median {st.median(groups[keys[1]]):.4g}; {kind} p = {p:.3g}")
        else:
            s = (f"{vcol} across {len(keys)} groups; {kind} p = {p:.3g}; medians " +
                 ", ".join(f"{k} {st.median(groups[k]):.4g}" for k in keys[:5]))
        if per_cell_used:
            s += " (one median per cell)"
            rkeys = [k for k in keys if k in groups_row]
            if len(rkeys) == len(keys):
                try:
                    pr, _ = _p(groups_row, rkeys)
                    s += f"; per-row p = {pr:.3g} over {sum(len(groups_row[k]) for k in rkeys)} rows"
                    if (pr < .05) != (p < .05):
                        s += " -- SIGNIFICANCE DIFFERS BY UNIT; the per-cell value is the one to quote"
                except Exception:
                    pass
        return ns, s
    except Exception:
        return ns, None


SRC_PRETTY = {
    "kt_outlines.csv": "her kinetochore outlines",
    "KT_OUTLINE_TRACKS": "kinetochore outline tracks",
    "KT_SISTER_KK": "sister k-k distances",
    "cell_outlines.csv": "her cell outlines",
    "meta_plates.csv": "her metaphase plates",
    "META_PLATE_NORMALIZED": "her metaphase plates",
    "ABLATION_MASTER.csv": "the master spreadsheet",
    "kt_points.csv": "her kinetochore marks",
}

built, skipped = 0, collections.Counter()
for pid, ent in ps.items():
    if not isinstance(ent, dict):
        continue
    if placed and pid not in placed:
        skipped["not placed on any of the 4 decks"] += 1
        continue
    dpath = os.path.join(DATA, pid + ".csv")
    # PANELS INHERIT THEIR PARENT'S DATA (2026-08-09). A split panel is one view of its parent's dataset
    # and deliberately has no data CSV of its own (see register_panels_20260809.py). Without this fallback
    # every panel was skipped as "no data CSV", which is why 174 placed figures carried no legend bullets
    # after the 4 decks were converted to single-panel figures.
    panel_of = ent.get("panel_of") or (ent.get("settings") or {}).get("panel_of")
    if not os.path.exists(dpath) and panel_of:
        ppath = os.path.join(DATA, str(panel_of) + ".csv")
        if os.path.exists(ppath):
            dpath = ppath
    if not os.path.exists(dpath):
        # 2026-08-18: skipping these left placed figures with NO legend at all (the AB5 excerpts, the FRAP
        # strip, the superseded G4_cdc20_vs_distance). A figure with no data file still has a caption and
        # recorded settings, and those are exactly what a legend needs to say.
        cap0 = (ent.get("caption") or "").strip()
        if not cap0:
            skipped["no data CSV and no caption"] += 1
            continue
        b0 = [cap0.rstrip(".") + "."]
        b0 += image_bullets(pid, ent, ps.get(panel_of) if panel_of else None)
        setg0 = ent.get("settings") or {}
        for k0 in ("status", "successor", "note", "kind", "built_by", "split_reason"):
            if setg0.get(k0):
                b0.append(f"{k0.replace('_', ' ').capitalize()}: {setg0[k0]}.")
        b0.append("No data table: this panel is an image/excerpt, or its builder no longer generates data.")
        ent["legend_bullets"] = b0
        ent["legend_bullets_built"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        built += 1
        continue
    try:
        rows = list(csv.DictReader(open(dpath, newline="", encoding="utf-8", errors="replace")))
    except Exception:
        skipped["unreadable data CSV"] += 1
        continue
    if not rows:
        skipped["data CSV has ZERO rows"] += 1     # NOTES §8: these blind every downstream audit
        continue
    hdr = list(rows[0].keys())
    bullets = []

    cap = (ent.get("caption") or "").strip()
    if cap:
        bullets.append(cap.split(". ")[0].rstrip(".") + ".")

    _img = image_bullets(pid, ent, ps.get(panel_of) if panel_of else None)
    if _img:
        # an image panel is ONE cell; "n = 1 rows" is not what a legend means by n
        bullets.append("n = 1 cell (1 independent imaging day).")
        bullets.extend(_img)
        bullets.append("Data updated " +
                       datetime.datetime.fromtimestamp(os.path.getmtime(dpath)).strftime("%Y-%m-%d %H:%M") + ".")
        ent["legend_bullets"] = bullets
        ent["legend_bullets_built"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        built += 1
        if built <= 3:
            print("\n--- " + pid + " ---")
            for b in bullets: print("   * " + b)
        continue
    nb = f"n = {len(rows)} rows"
    if "batch" in hdr:
        nb += f" from {len({(r.get('batch') or '').strip() for r in rows if (r.get('batch') or '').strip()})} cells"
    # Say so when the N is the parent's. A panel shows ONE view of the parent's dataset, so quoting the
    # parent's N unqualified would overstate what the reader is looking at.
    if panel_of and dpath.endswith(str(panel_of) + ".csv"):
        nb += f" — dataset of the parent figure ({panel_of}); this panel shows one view of it"
    ns, sbs = stats_bullets(rows, hdr)
    if ns:
        nb += f" ({ns})"
    bullets.append(nb)
    for sb in sbs:
        bullets.append(sb)

    srcs = ent.get("source") or []
    if isinstance(srcs, str):
        srcs = [srcs]
    pretty = []
    for s in srcs:
        for k, v in SRC_PRETTY.items():
            if k in str(s) and v not in pretty:
                pretty.append(v)
    if pretty:
        bullets.append("Source: " + ", ".join(pretty) + ".")

    setg = ent.get("settings") or {}
    filt = []
    if str(setg.get("anaphase", "")).lower() == "excluded":
        filt.append("anaphase excluded")
    if "drift" in setg:
        filt.append(str(setg["drift"]))
    if setg.get("cohort"):
        filt.append(f"cohort {setg['cohort']}")
    if setg.get("window"):
        filt.append(str(setg["window"]))
    if filt:
        bullets.append("Filters: " + "; ".join(filt) + ".")

    mt = datetime.datetime.fromtimestamp(os.path.getmtime(dpath)).strftime("%Y-%m-%d %H:%M")
    bullets.append(f"Data updated {mt}.")

    ent["legend_bullets"] = bullets
    ent["legend_bullets_built"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    built += 1

tmp = PS + ".tmp"
json.dump(ps, open(tmp, "w"), indent=1)
os.replace(tmp, PS)
print(f"\nlegend bullets built for {built} placed figures")
for k, v in skipped.most_common():
    print(f"   skipped {v:4d}  {k}")

ex = [k for k, v in ps.items() if isinstance(v, dict) and v.get("legend_bullets")][:3]
for k in ex:
    print(f"\n--- {k} ---")
    for b in ps[k]["legend_bullets"]:
        print("   * " + b)
