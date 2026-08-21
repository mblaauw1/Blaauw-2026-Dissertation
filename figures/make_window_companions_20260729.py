#!/usr/bin/env python3
"""Mitotic-WINDOW companion plots: <plot_id>_win<WINDOW>.

USER 2026-07-29: several plots span the whole traced range, so a trendline is diluted by timepoints
outside the interval the plot is actually about. Make a companion restricted to the relevant mitotic
window - and do NOT replace the original ("dont replace the original, just create another version").
Also: "if it would be useful to generate a version of a plot where t=0 is the laser, what weve been
doing is instead in the other version of the plot using metaphase onset for a cell as t=0" - so an
ablation-anchored plot is a legitimate candidate for a metaphase-anchored companion, not a reason to skip.

WINDOW PER PLOT is chosen from what the plot is showing, not applied uniformly:
  meta_to_ana   metaphase onset -> anaphase onset. For anything about behaviour DURING metaphase
                (distance to plate, oscillation, velocity, rotation, intensity over mitosis).
  to_ana        first measurement -> anaphase onset. For plots whose point is the run-up to anaphase
                where metaphase onset is not the meaningful start (fate, lagging length over time).
  meta_on       everything from metaphase onset onward, t=0 at metaphase onset. The metaphase-anchored
                counterpart of an ablation-anchored plot.

Rows are kept when their own t_sec/t_min falls in the window for THEIR cell, using the master's
User-Input event times through lib.parse_time. A cell missing the needed event is dropped from the
companion and logged - never given an assumed time.

  python3 make_window_companions_20260729.py            # build all configured companions
"""
import sys, os, csv, json, collections
sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import lib

lib.apply_style()
ROOT = "/Volumes/4 MB"
DATA = f"{ROOT}/ablation_plots/data"
csv.field_size_limit(10 ** 9)

# plot_id -> (window, why)
PLAN = {
    "G4_distance_vs_roundness":              ("meta_to_ana", "cell rounding vs KT distance is a metaphase relationship"),
    "G4_plate_distance_time_roundness":      ("meta_to_ana", "distance-to-plate only exists while a plate exists"),
    "G4_velocity_paired_comparison":         ("meta_to_ana", "polar vs paired speed compared over the same metaphase interval"),
    "G4_fluor_over_time_zoom":               ("meta_to_ana", "KT fluorescence over mitosis, restricted to metaphase"),
    "G4_lagging_vs_control_length_over_time": ("to_ana",     "the point is the approach to anaphase; metaphase onset is not the meaningful start"),
    "G4_lagging_auto_shape_v2":              ("to_ana",      "auto shape vs time up to anaphase, where lagging is defined"),
    # G4_exhaustion_violin_journal is NOT windowable and is deliberately absent: its `minutes` column is
    # the metaphase DURATION of a cell (one row per cell), not a timepoint, so there is no time axis to
    # restrict. The meaningful variants there would filter on `censored` / `in_metaphase_at_start`.
    "G3_kt_fate":                            ("to_ana",      "fate resolves by anaphase; later frames add nothing"),
    "G4_oscillation_effective":              ("meta_to_ana", "oscillation amplitude is a metaphase property"),
}

# RETIRED (item M2-11/M2-19, 2026-08-03) -- these three were REMOVED from PLAN above; kept here as a record
# of why, and RETIRE_NOW below stamps the already-built companion PNGs so a stale copy on disk (or already
# linked into copy.ai's _ai_relink PDF) can't be mistaken for a current figure:
#   "DEMO_area_with_timestrips"      -- companion is now redundant: DEMO_area_with_timestrips was rebuilt
#       today (2026-08-03) to aggregate ONE point per cell fit strictly within Metaphase Start->Anaphase
#       Onset (see its own PLOT_SETTINGS "type"), so a meta_to_ana-windowed companion of it duplicates the
#       parent exactly.
#   "G4_cdc20_intensity_chronological" -- its parent's x-axis is now t_min RELATIVE TO METAPHASE START
#       (already clipped to [Metaphase Start, Anaphase Onset] per cell -- see its own PLOT_SETTINGS
#       "window"), but this script's win_bounds() compares against ABSOLUTE elapsed-from-ablation seconds.
#       Comparing a metaphase-relative x-axis to absolute bounds is not just redundant, it silently drops
#       EVERY row for any cell whose metaphase doesn't start near t=0 on the ablation clock -- BROKEN, not
#       just superseded. Retired rather than "fixed" because fixing would only reproduce the parent, which
#       already exists.
#   "metaplate_rotation_by_sisterless" -- item M2-11 restricted the PARENT itself to Metaphase Start ->
#       Anaphase Onset (see metaplate_rotation_by_sisterless.py), so this companion now duplicates its
#       parent exactly (same window, same rows).
RETIRE_NOW = {
    "DEMO_area_with_timestrips_win_meta_to_ana": "parent rebuilt 2026-08-03 to already be one point per cell strictly within metaphase -- companion is an exact duplicate",
    "G4_cdc20_intensity_chronological_win_meta_to_ana": "parent x-axis is metaphase-relative but this companion filters on ABSOLUTE elapsed-from-ablation bounds -- broken, not just redundant",
    "metaplate_rotation_by_sisterless_win_meta_to_ana": "parent windowed to meta_to_ana directly 2026-08-03 (item M2-11) -- companion is an exact duplicate",
}

data, _ = lib.load_master_plots()
mr = {r["Batch Name"]: r for r in data}


def ev(b, col):
    return lib.parse_time((mr.get(b) or {}).get(col, ""))


def win_bounds(b, mode):
    a = ev(b, "Anaphase Onset (s)")
    m = ev(b, "Metaphase Start (s)") or ev(b, "Metaphase Onset (s)")
    if mode == "meta_to_ana":
        return (m, a) if (m is not None and a is not None and a > m) else None
    if mode == "to_ana":
        return (None, a) if a is not None else None
    if mode == "meta_on":
        return (m, None) if m is not None else None
    return None


TCOLS = ("t_sec", "t_min", "time_s", "rel_time_s", "time_from_ablation_s", "minutes")
built, skipped = [], []
for pid, (mode, why) in sorted(PLAN.items()):
    p = f"{DATA}/{pid}.csv"
    if not os.path.isfile(p):
        skipped.append((pid, "no data CSV")); continue
    rows = list(csv.reader(open(p)))
    if len(rows) < 5:
        skipped.append((pid, "too few rows")); continue
    hdr, body = rows[0], rows[1:]
    tcol = next((c for c in TCOLS if c in hdr), None)
    bcol = next((c for c in ("batch", "cell") if c in hdr), None)
    # kt track tables key on track_id = "<batch>|<label>|<grp>" instead of a bare batch column, so the
    # batch is recoverable by splitting on the first '|'. Without this, every track-keyed plot was
    # rejected for "needs a time and a batch column" (2026-07-29).
    track_keyed = False
    if bcol is None and "track" in hdr:
        bcol, track_keyed = "track", True
    if not tcol or not bcol:
        skipped.append((pid, f"needs a time and a batch column (has {hdr[:6]})")); continue
    ti, bi = hdr.index(tcol), hdr.index(bcol)
    scale = 60.0 if tcol in ("t_min", "minutes") else 1.0
    keep, dropped_cells = [], set()
    for r in body:
        if bi >= len(r) or ti >= len(r):
            continue
        b = r[bi].strip()
        if track_keyed:
            b = b.split("|")[0].strip()
        wb = win_bounds(b, mode)
        if wb is None:
            dropped_cells.add(b); continue
        lo, hi = wb
        try:
            t = float(r[ti]) * scale
        except (TypeError, ValueError):
            continue
        if lo is not None and t < lo:
            continue
        if hi is not None and t > hi:
            continue
        keep.append(r)
    if len(keep) < 8:
        skipped.append((pid, f"only {len(keep)} rows inside the {mode} window")); continue

    # numeric y = the first numeric non-time, non-id column
    def nums(col_i, rr):
        out = []
        for r in rr:
            try:
                out.append(float(r[col_i]))
            except Exception:
                out.append(np.nan)
        return np.array(out)

    ycol = None
    for i, c in enumerate(hdr):
        if c in TCOLS or c in (bcol,) or c.lower().startswith(("n_", "id", "track", "seq", "frame")):
            continue
        v = nums(i, keep)
        if np.isfinite(v).sum() >= max(6, 0.4 * len(v)) and len(set(v[np.isfinite(v)])) > 2:
            ycol = c; break
    if ycol is None:
        # CATEGORICAL y (e.g. G3_kt_fate's `fate`): there is no continuous axis to trend, but the window
        # still matters - restricting to rows resolved inside it changes the composition. Draw the
        # category fractions before/after windowing instead of a scatter+trend.
        ccol = next((c for c in hdr if c.lower() in
                     ("fate", "behavior", "behaviour", "outcome", "class", "state", "label")), None)
        if ccol is None:
            skipped.append((pid, "no numeric or categorical y column")); continue
        ci = hdr.index(ccol)
        allc = collections.Counter((r[ci] if ci < len(r) else "").strip() for r in body)
        keepc = collections.Counter((r[ci] if ci < len(r) else "").strip() for r in keep)
        cats = [c for c, _ in allc.most_common() if c]
        LBLc = {"meta_to_ana": "metaphase onset to anaphase onset",
                "to_ana": "first measurement to anaphase onset",
                "meta_on": "metaphase onset onward"}[mode]
        fig, ax = plt.subplots(figsize=(6.6, 4.4))
        xs = np.arange(len(cats)); w = 0.38
        tot_a = max(sum(allc[c] for c in cats), 1); tot_k = max(sum(keepc[c] for c in cats), 1)
        ax.bar(xs - w / 2, [100.0 * allc[c] / tot_a for c in cats], w, label=f"all rows (n={tot_a})",
               color="#9e9e9e")
        ax.bar(xs + w / 2, [100.0 * keepc[c] / tot_k for c in cats], w,
               label=f"inside window (n={tot_k})", color="#1b7837")
        ax.set_xticks(xs); ax.set_xticklabels(cats, rotation=20, ha="right", fontsize=8)
        ax.set_ylabel("%% of rows"); ax.legend(fontsize=8, frameon=False)
        ax.set_title(f"{pid} — composition restricted to {LBLc}\nwhy: {why}",
                     loc="left", fontweight="bold", fontsize=9)
        gd = lib.group_dir(pid) if hasattr(lib, "group_dir") else f"{ROOT}/ablation_figures_20260625/group4"
        os.makedirs(gd, exist_ok=True)
        nm = f"{pid}_win_{mode}"
        fig.savefig(f"{gd}/{nm}.png", bbox_inches="tight", dpi=130); plt.close(fig)
        lib.record_plot(nm, hdr, keep,
                        {"window": mode, "window_label": LBLc, "category_column": ccol,
                         "why": why, "n_rows_kept": len(keep), "n_rows_parent": len(body),
                         "type": "category composition, all rows vs inside the window"},
                        __file__,
                        f"{pid} composition restricted to {LBLc}. {why}. Companion only.",
                        source=[f"{DATA}/{pid}.csv", f"{ROOT}/ABLATION_MASTER.csv"], key_column=bcol)
        built.append((nm, len(keep), len(body), len(dropped_cells)))
        continue
    yi = hdr.index(ycol)
    X, Y = nums(ti, keep) * (1.0 if scale == 1.0 else 1.0), nums(yi, keep)
    m = np.isfinite(X) & np.isfinite(Y)
    X, Y = X[m], Y[m]
    if len(X) < 8:
        skipped.append((pid, "too few finite points")); continue

    LBL = {"meta_to_ana": "metaphase onset to anaphase onset",
           "to_ana": "first measurement to anaphase onset",
           "meta_on": "metaphase onset onward (t=0 at metaphase onset)"}[mode]
    fig, ax = plt.subplots(figsize=(6.6, 4.6))
    ax.scatter(X, Y, s=20, alpha=.75, color="#1b7837", edgecolor="none")
    if len(X) >= 6:
        try:
            from scipy import stats as st
            rho, pv = st.spearmanr(X, Y)
            k, c0 = np.polyfit(X, Y, 1)
            xr = np.linspace(X.min(), X.max(), 40)
            ax.plot(xr, k * xr + c0, "--", color="#b30000", lw=1.5)
            sub = f"Spearman ρ={rho:.2f}, p={pv:.3g}, n={len(X)}"
        except Exception:
            sub = f"n={len(X)}"
    else:
        sub = f"n={len(X)}"
    # 2026-08-04: these companions were labelled with the raw CSV column names (t_sec,
    # effective_disp_um_per_20s, ...), which reads as a data dump rather than a figure. Map the columns this
    # family actually uses to readable labels with units; anything unmapped falls back to the column name.
    _AXLAB = {
        "t_sec": "Time (s)",
        "t_min": "Time (min)",
        "t_min_from_meta": "Time from metaphase onset (min)",
        "t_sec_from_meta": "Time from metaphase onset (s)",
        "t_rel_min": "Time relative to the event (min)",
        "effective_disp_um_per_20s": "Displacement per 20 s (µm)",
        "value": "Value",
        "intensity": "Intensity (a.u.)",
        "plate_dist_um": "Distance to the metaphase plate (µm)",
        "major_um": "Kinetochore length, major axis (µm)",
        "aspect_ratio": "Aspect ratio (major / minor)",
        "kk_or_equiv_um": "k–k / equivalent k–k (µm)",
        "fluor_mean_au": "Cell fluorescence (a.u.)",
        "area_um2": "Cross-sectional area (µm²)",
        "roundness": "Roundness (4πA / P²)",
        # remaining columns these companions actually plot (checked against each parent's data CSV)
        "velocity_um_per_min": "Velocity relative to the plate (µm/min)",
        "cell_roundness": "Cell roundness (4πA / P²)",
        "length_um": "Kinetochore length (µm)",
        "auto_length_um": "Kinetochore length, automated (µm)",
        "auto_width_um": "Kinetochore width, automated (µm)",
        "auto_aspect": "Aspect ratio, automated (major / minor)",
        "auto_area_um2": "Cross-sectional area, automated (µm²)",
        "manual_length_um": "Kinetochore length, manual (µm)",
        "time_s": "Time (s)",
        "fate": "Fate",
    }
    ax.set_xlabel(_AXLAB.get(tcol, tcol)); ax.set_ylabel(_AXLAB.get(ycol, ycol))
    ax.set_title(f"{pid} — restricted to {LBL}\n{sub}\nwhy: {why}",
                 loc="left", fontweight="bold", fontsize=9)
    gd = lib.group_dir(pid) if hasattr(lib, "group_dir") else f"{ROOT}/ablation_figures_20260625/group4"
    os.makedirs(gd, exist_ok=True)
    nm = f"{pid}_win_{mode}"
    fig.savefig(f"{gd}/{nm}.png", bbox_inches="tight", dpi=130)
    plt.close(fig)
    lib.record_plot(nm, hdr, keep,
                    {"window": mode, "window_label": LBL, "x": tcol, "y": ycol,
                     "why": why, "n_rows_kept": len(keep), "n_rows_parent": len(body)},
                    __file__,
                    f"{pid} restricted to {LBL}. {why}. Companion only — the parent keeps its full range.",
                    source=[f"{DATA}/{pid}.csv", f"{ROOT}/ABLATION_MASTER.csv"], key_column=bcol)
    built.append((nm, len(keep), len(body), len(dropped_cells)))

print("WINDOW companions built: %d" % len(built))
for nm, k, tot, dc in built:
    print("   %-52s kept %5d of %5d rows   (cells lacking the event: %d)" % (nm, k, tot, dc))
if skipped:
    print("\nnot built: %d" % len(skipped))
    for pid, why in skipped:
        print("   %-52s %s" % (pid, why))


# ---- RETIRE_NOW: stamp the already-built PNGs for entries removed from PLAN above (item M2-11/M2-19,
# 2026-08-03) so a stale/duplicate/broken companion still on disk (or still linked into the copy.ai
# _ai_relink PDF) is unmistakable at a glance, matching the "RETIRED" convention lib.mark_retired() uses
# elsewhere in this codebase. mark_retired() draws onto a LIVE matplotlib figure, but these companions are
# already-saved PNGs with no live figure to redraw (their builder code -- this file's own PLAN loop -- no
# longer runs them), so the watermark is stamped directly onto the saved image with PIL instead.
def _stamp_retired(png_path, note):
    from PIL import Image, ImageDraw, ImageFont
    if not os.path.isfile(png_path):
        return False
    im = Image.open(png_path).convert("RGBA")
    overlay = Image.new("RGBA", im.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    w, h = im.size
    try:
        big = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", int(min(w, h) * 0.16))
        small = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 13)
    except Exception:
        big = ImageFont.load_default(); small = ImageFont.load_default()
    txt_layer = Image.new("RGBA", (w * 2, h), (0, 0, 0, 0))
    td = ImageDraw.Draw(txt_layer)
    td.text((w, h // 2), "RETIRED", font=big, fill=(208, 0, 0, 72), anchor="mm")
    txt_layer = txt_layer.rotate(30, resample=Image.BICUBIC, center=(w, h // 2))
    overlay.alpha_composite(txt_layer.crop((w // 2, 0, w // 2 + w, h)))
    draw.rectangle([0, h - 22, w, h], fill=(255, 255, 255, 235))
    draw.text((6, h - 20), f"RETIRED -- {note}"[:160], font=small, fill=(192, 0, 0, 255))
    out = Image.alpha_composite(im, overlay).convert("RGB")
    out.save(png_path)
    return True


_retired_stamped = []
for nm, note in RETIRE_NOW.items():
    gd = lib.group_dir(nm) if hasattr(lib, "group_dir") else f"{ROOT}/ablation_figures_20260625/group4"
    png_path = f"{gd}/{nm}.png"
    ok = _stamp_retired(png_path, note)
    lib.log_review("window_companion_retired", nm, "retired" if ok else "png not found", note)
    # mark it retired in PLOT_SETTINGS.json too, without touching its recorded data/statistics
    sp = f"{DATA.rsplit('/',1)[0]}/PLOT_SETTINGS.json"
    try:
        allset = json.load(open(sp))
        if nm in allset:
            allset[nm].setdefault("settings", {})["retired"] = True
            allset[nm]["settings"]["retired_reason"] = note
            allset[nm]["settings"]["retired_date"] = "2026-08-03"
            json.dump(allset, open(sp, "w"), indent=1)
    except Exception as e:
        print(f"  [retire WARNING] could not update PLOT_SETTINGS.json for {nm}: {e}")
    _retired_stamped.append((nm, ok))

if _retired_stamped:
    print("\nRETIRED (removed from PLAN, PNG stamped, settings flagged): %d" % len(_retired_stamped))
    for nm, ok in _retired_stamped:
        print("   %-52s %s" % (nm, "stamped" if ok else "PNG NOT FOUND -- could not stamp"))

lib.flush_review("/Volumes/4 MB/ablation_figures_20260625/_review/window_companions_review.csv")
