#!/usr/bin/env python3
"""Build a descriptive, glanceable title for every figure placed in the two .ai decks.

USER 2026-07-29: the existing titles are "quite undescriptive and some of them are quite long with
just a jumble of info that isnt useful ... at a glance". A title must say what RELATIONSHIP is
plotted, what DATA TYPE it came from (manual outlines / snapped circles / TrackMate), the TIME RANGE
of the datapoints, the FILTERS in force, when it was last updated, and which artboard it is on.

It also carries the KT-CLASS labelling that handoff-7 section 12 lists as never started: "many plots
do not say whether they show control/paired, polar, congressed or lagging KTs".

FORMAT (one line, pipe-separated so it stays scannable):
  <relationship> | <data source> | <KT classes> | <time window> | <filters> | n=… | AB## | upd YYYY-MM-DD

Every field is DERIVED and, where it cannot be derived, it is OMITTED rather than guessed - a wrong
filter or window in a title is worse than a missing one.

Writes `deck_title` into PLOT_SETTINGS (and `deck_title_fields` so each part can be traced).
A companion JSX draws them under the figures.
"""
import csv, json, os, re, subprocess, collections, datetime

ROOT = "/Volumes/4 MB"
PS = os.path.join(ROOT, "ablation_plots/PLOT_SETTINGS.json")
DATA = os.path.join(ROOT, "ablation_plots/data")
PDF = os.path.join(ROOT, "ablation_figures_20260625/_ai_relink/pdf")
csv.field_size_limit(10 ** 9)
ps = json.load(open(PS))

# ---- which figures are placed, and on which artboard (from the JSX dump if present) ----
ab = {}
dump = "/Volumes/4 MB/_working/_deck_jsx_inputs/artboards.json"
if os.path.exists(dump):
    ab = json.load(open(dump))
placed = set()
for d in ["ablation_plots/_superseded_decks/ablation_figures_grouped copy.ai",
          "ablation_plots/_superseded_decks/ablation_figures_kinetochore_overflow.ai"]:
    out = subprocess.run(["strings", os.path.join(ROOT, d)], capture_output=True, text=True).stdout
    for m in re.findall(r"([A-Za-z0-9_.\-]+)\.(?:pdf|png)", out):
        placed.add(m)

# ---- data source, inferred from the generating script's inputs ----
SRC_RULES = [
    ("kt_outlines",            "manual outlines"),
    ("KT_OUTLINE_TRACKS",      "manual outlines"),
    ("kt_shape_metrics",       "manual outlines"),
    ("KT_FLUOR_CYTOSOLNORM",   "manual outlines + per-frame cytosol"),
    ("KT_TENSION",             "manual outlines"),
    ("KT_SISTERS",             "manual outlines"),
    ("kt_points",              "snapped circles"),
    ("KT_TRACKING_MASTER",     "TrackMate"),
    ("trackmate",              "TrackMate"),
    ("meta_plates",            "manual plate marks"),
    ("chromo_lines",           "manual chromosome lines"),
    ("CYTOSOL_BACKGROUND",     "cytosol background"),
]
KT_CLASS = [("paired", "paired/plate"), ("polar", "polar"), ("sisterless", "sisterless"),
            ("lagging", "lagging"), ("congress", "congressed"), ("plate_kt", "plate")]
WINDOW = [
    ("meta_to_ana",   "metaphase→anaphase"),
    ("_metaphase",    "metaphase only"),
    ("premeta",       "before metaphase"),
    ("prometa",       "prometaphase"),
    ("neb_to_meta",   "NEBD→metaphase"),
    ("ana_to_cyto",   "anaphase→cytokinesis"),
    ("postanaphase",  "after anaphase"),
    ("chronological", "whole movie, chronological"),
    ("time_to_anaphase", "aligned to anaphase"),
    ("frap",          "from ablation (t=0 at laser)"),
    ("prepost",       "pre vs post ablation"),
    ("ablation_intensity", "from ablation (t=0 at laser)"),
]


def script_of(pid):
    """Resolve the `code` field to a real path. It appears in three forms: an absolute path, a
    root-relative one (ablation_figures_20260625/x.py), and a PLOT_SETTINGS-relative one
    (code/<fig>__<script>.py, which lives under ablation_plots/). Trying only the root form left the
    data-source field underivable for 463 of 522 figures (2026-07-29)."""
    c = str((ps.get(pid) or {}).get("code") or "").strip()
    if not c:
        return ""
    if c.startswith("/"):
        return c
    for base in (ROOT, os.path.join(ROOT, "ablation_plots"),
                 os.path.join(ROOT, "ablation_figures_20260625")):
        q = os.path.join(base, c)
        if os.path.isfile(q):
            return q
    return os.path.join(ROOT, c)


def read_script(pid):
    p = script_of(pid)
    if p and os.path.isfile(p):
        try:
            return open(p, encoding="utf-8", errors="ignore").read()
        except Exception:
            return ""
    return ""


def data_source(pid, src, e):
    """Prefer what the script actually reads; fall back to the recorded source-file list, which
    record_plot stamps for every figure it registers."""
    hits = []
    for key, label in SRC_RULES:
        if key in src and label not in hits:
            hits.append(label)
    if not hits:
        files = " ".join((e.get("source") or {}).get("files", []) if isinstance(e.get("source"), dict) else [])
        for key, label in SRC_RULES:
            if key in files and label not in hits:
                hits.append(label)
        if not hits and "ABLATION_MASTER" in files:
            hits.append("master table")
    if hits:
        return " + ".join(hits[:2])
    return "source not recorded"


def kt_classes(pid, hdr, rows):  # hdr is used for the explicit no-KT-class fallbacks
    """what KT classes actually appear in the plotted data (not what the name implies)."""
    found = []
    for i, c in enumerate(hdr):
        # widened 2026-07-29: an audit found 29 figures whose KT class sits in a column this list did
        # not scan - group_a (statgrid pairwise labels), fate, behavior, outcome, location, event, kt,
        # task. The batch/cell NAME column is deliberately never scanned: batch names contain words like
        # "sisterless" (two_sisterless_kinetochores_5) which is a cell identifier, not a KT class.
        if c.lower() in ("batch", "cell", "track", "id", "ann_id", "chromosome"):
            continue
        if c.lower() not in ("label", "kt_type", "state", "class", "role", "series", "group", "cohort",
                             "group_a", "group_b", "fate", "behavior", "behaviour", "outcome",
                             "location", "event", "kt", "task", "panel", "marker"):
            continue
        vals = {(r[i] if i < len(r) else "").strip().lower() for r in rows}
        for key, label in KT_CLASS:
            if any(key in v for v in vals if v) and label not in found:
                found.append(label)
    if not found:                       # fall back to the plot id
        for key, label in KT_CLASS:
            if key in pid.lower() and label not in found:
                found.append(label)
    if found:
        return ", ".join(found[:4])
    # NEVER leave this blank (user 2026-07-29: "resolve the remaining blanks"). A blank field reads as
    # "unknown", when in fact most of these figures legitimately have no KT class - they measure whole
    # cells or whole chromosomes. Say which, so a glance distinguishes "not a KT plot" from "unlabelled".
    if not hdr:
        return "image panel (no KT class)"
    low = [c.lower() for c in hdr]
    if any(c in low for c in ("cohort", "group", "group_a", "n_sisterless")):
        return "by ablation cohort (cell-level, no KT class)"
    if any("chrom" in c for c in low):
        return "chromosome-level (no KT class)"
    return "cell-level (no KT class)"


def window(pid, src, hdr):
    for key, label in WINDOW:
        if key in pid.lower():
            return label
    if "frac_meta_to_ana" in hdr:
        return "metaphase→anaphase (normalised)"
    if any(c in hdr for c in ("t_since_ana_min", "t_since_anaphase_min")):
        return "aligned to anaphase"
    if "time_from_ablation_s" in hdr or "rel_time_s" in hdr:
        return "from ablation (t=0 at laser)"
    # TIME-AXIS column names actually present in the recorded data CSVs (enumerated 2026-07-29).
    # Missing these made real time-series plots report "no time axis" - e.g. kk_vs_time (t_min_from_meta)
    # and G4_kt_intensity_time (t_min_since_first_abl).
    TIMEAX = ("t_min", "t_sec", "time_s", "t_min_from_meta", "time_from_metaphase_min",
              "t_from_metaphase_min", "time_from_meta_min", "t_min_since_first_abl",
              "t_to_anaphase_min", "t_since_anaphase_min", "rel_time_s", "time_from_ablation_s",
              "frame_idx", "frame", "x_min")
    ANCHOR = {"t_min_from_meta": "from metaphase onset",
              "time_from_metaphase_min": "from metaphase onset",
              "t_from_metaphase_min": "from metaphase onset",
              "time_from_meta_min": "from metaphase onset",
              "t_min_since_first_abl": "from the first ablation",
              "t_to_anaphase_min": "to anaphase onset",
              "t_since_anaphase_min": "since anaphase onset",
              "rel_time_s": "from the ablation flash",
              "time_from_ablation_s": "from the ablation flash"}
    for c in TIMEAX:
        if c in hdr:
            a = ANCHOR.get(c)
            return ("whole traced range, %s" % a) if a else "whole traced range"
    # NEVER blank. Distinguish a figure with no time axis from one whose window was not worked out.
    if not hdr:
        return "image panel (no time axis)"
    low = [c.lower() for c in hdr]
    if any("duration" in c or c in ("minutes", "meta_min", "meta_duration_min") for c in low):
        return "one duration per cell (not a time series)"
    return "no time axis (one value per cell)"


def filters(pid, src, e):
    f = []
    if "plot_excluded" in src or "lib.excluded" in src:
        f.append("Exclude/drug/metaphase-abl removed")
    if "kt_outline_excluded" in src:
        f.append("cdc20 cohort")
    if "focus_excluded" in src:
        f.append("out-of-focus dropped")
    if "is_misplaced_id" in src:
        f.append("misplaced clicks dropped")
    if pid.endswith("_zoom"):
        f.append("outliers trimmed")
    if "_journal" in pid:
        f.append("journal style")
    if "robust_keep" in src:
        f.append("robust outlier gate")
    if str(e.get("retired")) == "True":
        f.insert(0, "RETIRED")
    if f:
        return "; ".join(f[:3])
    return "no exclusions applied"


def relationship(pid, e):
    cap = str(e.get("caption") or "").strip()
    if cap:
        cap = re.split(r"[.;(]", cap)[0].strip()
        cap = re.sub(r"\s+", " ", cap)
        if 12 <= len(cap) <= 96:
            return cap
    s = pid
    s = re.sub(r"^(G\d[a-z]*|QNEW|RNEW|DEMO|MAD1kt|collagenON|collagen)_+", "", s)
    s = s.replace("_", " ")
    s = re.sub(r"\bvs\b", "vs", s)
    return s[:96]


out = {}
for pid in sorted(placed):
    e = ps.get(pid)
    if e is None:
        continue
    src = read_script(pid)
    hdr, rows = [], []
    p = os.path.join(DATA, pid + ".csv")
    if os.path.isfile(p):
        try:
            rr = list(csv.reader(open(p)))
            if rr:
                hdr, rows = rr[0], rr[1:]
        except Exception:
            pass
    pdfp = os.path.join(PDF, pid + ".pdf")
    upd = ""
    if os.path.exists(pdfp):
        upd = datetime.datetime.fromtimestamp(os.stat(pdfp).st_mtime).strftime("%Y-%m-%d")
    else:
        # no _ai_relink pdf (image panels / timestrips are placed as PNG) - use the PNG itself
        for g in ("group1", "group2", "group3", "group4", "group5_shape", "group5_mad1_kt",
                  "group6_tracks", "group7_questions", "custom_collagen_vs_triple",
                  "group1/timestrips2", "group1/frap_timestrips", ""):
            q = os.path.join(ROOT, "ablation_figures_20260625", g, pid + ".png")
            if os.path.exists(q):
                upd = datetime.datetime.fromtimestamp(os.stat(q).st_mtime).strftime("%Y-%m-%d")
                break
        if not upd:
            # a few figures live outside the figure tree: the two kk_* overflow plots are written to
            # _scratch by their analysis scripts, and one retired figure only survives under
            # _retired/fabricated_plots_20260722. Search those too rather than leave the date blank.
            for q in (os.path.join(ROOT, "_scratch", pid + ".png"),
                      os.path.join(ROOT, "_retired/fabricated_plots_20260722", pid + ".png")):
                if os.path.exists(q):
                    upd = datetime.datetime.fromtimestamp(os.stat(q).st_mtime).strftime("%Y-%m-%d")
                    break
    # 2026-08-19: COUNT THE FILE, never trust the stored n_rows. 275 entries had a stale n_rows (a zoom
    # companion or panel that re-wrote its CSV without re-recording), and 46 deck titles were therefore
    # quoting an n that the figure's own data no longer supports.
    n = len(rows) if rows else e.get("n_rows")
    fields = {
        "relationship": relationship(pid, e),
        "source": data_source(pid, src, e),
        "kt_class": kt_classes(pid, hdr, rows),
        "window": window(pid, src, hdr),
        "filters": filters(pid, src, e),
        "n": ("n=%s" % n) if n else "n/a (image panel)",
        "artboard": ab.get(pid, "artboard unknown"),
        "updated": ("upd %s" % upd) if upd else "",
    }
    title = " | ".join(v for v in [fields["relationship"], fields["source"], fields["kt_class"],
                                   fields["window"], fields["filters"], fields["n"],
                                   fields["artboard"], fields["updated"]] if v)
    e["deck_title"] = title
    e["deck_title_fields"] = fields
    out[pid] = title

bak = "%s.%s_pre_titles.bak" % (PS, datetime.datetime.now().strftime("%Y%m%d_%H%M%S"))
import shutil
shutil.copy2(PS, bak)
json.dump(ps, open(PS + ".tmp", "w"), indent=1)
os.replace(PS + ".tmp", PS)
json.dump(out, open("/Volumes/4 MB/_working/_deck_jsx_inputs/deck_titles.json", "w"), indent=1)

print("titles built for %d placed figures" % len(out))
miss = collections.Counter()
for pid, t in out.items():
    f = ps[pid]["deck_title_fields"]
    for k, v in f.items():
        if not v:
            miss[k] += 1
print("fields that could not be derived (omitted rather than guessed):", dict(miss))
print()
for pid in list(sorted(out))[:6]:
    print("  %s\n     %s" % (pid, out[pid]))
print("\nbackup %s" % os.path.basename(bak))
