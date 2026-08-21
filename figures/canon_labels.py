"""CANONICAL AXIS LABELS, UNITS AND GROUP NAMES — one wording per quantity, one name per cohort.

USER 2026-08-17: "make x and y-axis labels extremely standardized, as right now they can say the same
thing in many different ways like metaphase duration can be labeled as: metaphase delay, mitotic duration,
metaphase duration but with a bunch of words after it, and more. And the units for time should always be
listed on the axes in the same way (and other units as well). Groups should always be called the same
thing."

EVIDENCE, not memory: every string below was pulled out of the placed figures' own PDFs
(`_claude_tmp/extract_labels_20260817.py` -> `figure_text_20260817.json`), so the left-hand sides are
wordings that are actually on the decks today. Measured spread at the time of writing:
  * 318 distinct y-axis strings and 290 distinct x-axis strings across 540 placed figures;
  * metaphase duration alone appeared as "Metaphase duration (MM:SS)" (36x), "Metaphase duration (min)"
    (17x) and "metaphase duration (min)" (3x);
  * micrometres appeared as "um", "um^2", "µm" and "µm²" on different axes of the same board.

RULES THIS FILE ENCODES
  1. UNITS APPEAR IFF THE QUANTITY IS DIMENSIONAL. Ratios, fractions, probabilities, indices, normalised
     values and counts get NO unit — they get their basis instead ("normalised to metaphase onset").
  2. ONE GLYPH PER UNIT: µm, µm², µm/min, min, s, a.u., ° — never um, um^2, micron, sec, deg, AU.
  3. ONE TIME REPRESENTATION PER QUANTITY: decimal MINUTES on quantitative axes; mm:ss ONLY for the
     burned-in clock on a timestrip frame, where the reader is reading a movie, not doing arithmetic.
  4. Sentence case, unit in parentheses after a single space: "Metaphase duration (min)".
  5. NO explanatory clause inside an axis label. Inclusion criteria, binning notes and caveats belong in
     the figure legend; `PUB=1` strips them from the artwork.
"""

import re

# ── GROUPS: full name defined ONCE (cartoon/first mention), abbreviation everywhere after ────────────
# Kept <= 8 characters, no plural variants, same capitalisation everywhere. "on-target" is NOT repeated in
# the short form: every sisterless cohort is on-target by construction, so it is said once at definition.
GROUP_FULL = {
    "unmod":      "unmanipulated control",
    "1-sis":      "one sisterless kinetochore",
    "2-sis":      "two sisterless kinetochores",
    "3-sis":      "three sisterless kinetochores",
    "4-sis":      "four sisterless kinetochores",
    "off-target": "off-target ablation control",
    "dbl-KT":     "two ablations on one kinetochore",
    "dbl-chr":    "two kinetochores destroyed on one chromosome",
    "collagen":   "collagen-plated, sisterless",
    "meta-abl":   "ablation performed during metaphase",
}

# every wording seen on the decks -> the canonical short name
GROUP = {
    "unModified": "unmod", "unmodified": "unmod", "Unmodified": "unmod",
    "unmodified (from NEBD)": "unmod", "no manipulation": "unmod", "control": "unmod",
    "1-Sister": "1-sis", "1-Sisterless": "1-sis", "1-sisterless": "1-sis", "1 sisterless": "1-sis",
    "2-Sister": "2-sis", "2-Sisterless": "2-sis", "2-sisterless": "2-sis", "2 sisterless": "2-sis",
    "3-Sister": "3-sis", "3-Sisterless": "3-sis", "3-sisterless": "3-sis", "3 sisterless": "3-sis",
    "4-Sister": "4-sis", "4-Sisterless": "4-sis", "4-sisterless": "4-sis", "4 sisterless": "4-sis",
    "1-Sisterless\noff-target": "off-target", "2-Sisterless\noff-target": "off-target",
    "3-Sisterless\noff-target": "off-target", "1-Sister Controls": "off-target",
    "2-Sister Controls": "off-target", "3-Sister Controls": "off-target",
    "Off-Target/Control": "off-target", "All off-target": "off-target", "all off-target": "off-target",
    "off-target (1/3)": "off-target", "off-target": "off-target",
    # the tick-wrapper flattens "1-Sisterless\noff-target" to "1-Sisterless/off-target", which the
    # newline-keyed entries above cannot match -- the slashed form is what actually reaches the PDF
    "1-Sisterless/off-target": "off-target", "2-Sisterless/off-target": "off-target",
    "3-Sisterless/off-target": "off-target", "4-Sisterless/off-target": "off-target",
    "1-Sisterless off-target": "off-target", "2-Sisterless off-target": "off-target",
    "3-Sisterless off-target": "off-target", "4-Sisterless off-target": "off-target",
    "Double Chromosome": "dbl-chr",
    "Destruction of two\nkinetochores on\none chromosome": "dbl-chr",
    "double-chromosome": "dbl-chr", "double chromosome": "dbl-chr",
    "Collagen (2/3-sis on-target)": "collagen", "collagen (2/3-sis)": "collagen",
    "Collagen": "collagen", "collagen": "collagen",
    "metaphase-ablated": "meta-abl", "Metaphase ablation": "meta-abl",
}

# ── AXES: exact wordings seen on the decks -> the one canonical label ────────────────────────────────
AXIS = {
    # time / duration ------------------------------------------------------------------------------
    "Metaphase duration (MM:SS)": "Metaphase duration (min)",
    "Metaphase duration (min)": "Metaphase duration (min)",
    "metaphase duration (min)": "Metaphase duration (min)",
    "Metaphase delay (min)": "Metaphase duration (min)",
    "Mitotic duration (min)": "Mitotic duration (min)",
    "Metaphase to Anaphase": "Metaphase duration (min)",
    "Metaphase to Anaphase (min)": "Metaphase duration (min)",
    "Anaphase to Cytokinesis (min)": "Anaphase to cytokinesis (min)",
    "First Alignment to Metaphase (min)": "First alignment to metaphase (min)",
    "NEBD to Metaphase (min)": "NEBD to metaphase (min)",
    "Meta→Ana (MM:SS)": "Metaphase duration (min)",
    "NEBD to Metaphase (MM:SS)": "NEBD to metaphase (min)",
    "First Alignment to Metaphase (MM:SS)": "First alignment to metaphase (min)",
    "Anaphase to Cytokinesis (MM:SS)": "Anaphase to cytokinesis (min)",
    # time AXES (x) --------------------------------------------------------------------------------
    "Time from first ablation (min); unmodified referenced to NEBD": "Time from ablation (min)",
    "Time from first ablation (min)": "Time from ablation (min)",
    "Time from ablation (s)": "Time from ablation (min)",
    "Time from ablation to metaphase start (min)": "Ablation to metaphase onset (min)",
    "Time from ablation to metaphase (min)": "Ablation to metaphase onset (min)",
    "first ablation to metaphase onset (min)": "Ablation to metaphase onset (min)",
    "Time from metaphase onset (min)": "Time from metaphase onset (min)",
    "Time from metaphase start (min)": "Time from metaphase onset (min)",
    "time from metaphase start (min)": "Time from metaphase onset (min)",
    "Time from metaphase (min)": "Time from metaphase onset (min)",
    "min from metaphase": "Time from metaphase onset (min)",
    "from metaphase onset (min)": "Time from metaphase onset (min)",
    "minutes from metaphase onset (each cell cut at its own anaphase onset)": "Time from metaphase onset (min)",
    "minutes from metaphase onset (metaphase window only)": "Time from metaphase onset (min)",
    "Time since anaphase onset (min)": "Time from anaphase onset (min)",
    "since anaphase onset (min, post)": "Time from anaphase onset (min)",
    "Minutes relative to anaphase onset (0 = anaphase)": "Time from anaphase onset (min)",
    "Time from movie start (min)": "Time from imaging start (min)",
    "timepoint (mm:ss)": "Time from imaging start (min)",
    "Timepoint (mm:ss)": "Time from imaging start (min)",
    "Minutes relative to a congression event": "Time from congression (min)",
    # dimensionless: NO unit, basis instead ---------------------------------------------------------
    "Fraction of metaphase elapsed": "Fraction of metaphase elapsed",
    "(fraction of metaphase elapsed: 0=onset, 1=anaphase)": "Fraction of metaphase elapsed",
    "Roundness (4piA/P^2)": "Cell roundness",
    "Cell roundness  (4πA / P²)": "Cell roundness",
    "circularity": "Cell roundness",
    "aspect": "Aspect ratio",
    "aspect ratio": "Aspect ratio",
    "near / far area ratio": "Near/far area ratio",
    "(extent across the plate / extent along it)": "Kinetochore aspect ratio",
    # length / distance ------------------------------------------------------------------------------
    "Cross-sectional area (um^2)": "Cell cross-sectional area (µm²)",
    "area (µm²)": "Cell cross-sectional area (µm²)",
    "Cumulative centroid movement (um)": "Cumulative centroid movement (µm)",
    "Cumulative plate rotation (deg)": "Cumulative plate rotation (°)",
    "distance to plate (µm)": "Distance to metaphase plate (µm)",
    "Distance to metaphase plate (µm)": "Distance to metaphase plate (µm)",
    "KT distance to metaphase plate (µm)": "Distance to metaphase plate (µm)",
    "k-k distance (um)": "k–k distance (µm)",
    "k-k distance (µm)": "k–k distance (µm)",
    "Chromosome length (µm)": "Chromosome length (µm)",
    "chromosome length (µm)": "Chromosome length (µm)",
    "sisterless chromosome length (µm)": "Chromosome length (µm)",
    "Sisterless chromosome length (µm)": "Chromosome length (µm)",
    "length of the sisterless chromosome (µm)": "Chromosome length (µm)",
    "assigned chromosome length (um)": "Chromosome length (µm)",
    "mean chromosome length per cell (µm)": "Mean chromosome length per cell (µm)",
    "Summed sisterless chromosome length (µm)": "Summed chromosome length (µm)",
    "Kinetochore length, major axis (µm)": "Kinetochore length (µm)",
    "Lagging KT length (µm, major axis at half-max)": "Kinetochore length (µm)",
    "total path length (µm)": "Total path length (µm)",
    "Displacement per 20s interval (µm)": "Displacement per 20 s (µm)",
    "oscillation amplitude (µm)": "Oscillation amplitude (µm)",
    "amplitude (um)": "Oscillation amplitude (µm)",
    "ablation-to-cell-edge distance (µm)": "Ablation-to-cell-edge distance (µm)",
    "y from cell origin (µm)": "Position from cell origin (µm)",
    "R_toward µm": "Reach toward the plate (µm)",
    # speed ---------------------------------------------------------------------------------------
    "speed (µm/s)": "Kinetochore speed (µm/min)",
    "paired KT speed (um/s)": "Kinetochore speed (µm/min)",
    "polar KT speed (um/s)": "Kinetochore speed (µm/min)",
    "Velocity relative to plate (µm/min)": "Velocity relative to the plate (µm/min)",
    # period ---------------------------------------------------------------------------------------
    "period (min)": "Oscillation period (min)",
    "oscillation period (s)": "Oscillation period (min)",
    # intensity ------------------------------------------------------------------------------------
    "Kinetochore eYFP-Cdc20 (a.u.)": "Kinetochore eYFP–Cdc20 (a.u.)",
    # dimensionless with its basis stated, per rule 1 -- no unit, but say what it is a fold OVER
    "fold over her cytosol background": "Fluorescence (fold over cytosol background)",
    "fold over cytosol background": "Fluorescence (fold over cytosol background)",
    # distortion -----------------------------------------------------------------------------------
    # 🔴 HER 2026-08-20 (board 7 item 4): *"the y-axes should just say 'kinetochore distortion' where
    # applicable - all except the relative distortion one which should just say relative distortion. I'll
    # note in methods and in the results that its along the spindle axis."* So the axis carries the
    # QUANTITY and the prose carries the axis convention; the "along the spindle axis" wording is removed
    # from every plot at once by changing it here rather than in each builder.
    "spindle-axis distortion": "Kinetochore distortion",
    "kinetochore distortion along the spindle axis": "Kinetochore distortion",
    "Kinetochore distortion along the spindle axis": "Kinetochore distortion",
    "Polar-KT distortion along the spindle axis": "Kinetochore distortion",
    "polar-KT distortion along the spindle axis": "Kinetochore distortion",
    "polar-KT distortion": "Kinetochore distortion",
    "kinetochore distortion": "Kinetochore distortion",
    "relative distortion": "Relative distortion",
    "Relative kinetochore distortion": "Relative distortion",
    "relative kinetochore distortion": "Relative distortion",
    "distortion relative to paired": "Relative distortion",
    "distortion relative to paired kinetochores": "Relative distortion",
    # counts ---------------------------------------------------------------------------------------
    "# ablation targets placed": "Ablation targets per cell",
    "sisterless group": "Group",
    "ablation phase": "Cell-cycle phase at ablation",
}

# glyph-level normalisation applied to ANY label that has no explicit entry above, so a new figure cannot
# reintroduce "um" or "deg" just by being written after this file.
UNIT_FIX = [
    (re.compile(r"\bum\^?2\b"), "µm²"),
    (re.compile(r"\bum\b"), "µm"),
    (re.compile(r"\bmicrons?\b", re.I), "µm"),
    (re.compile(r"\(deg\)"), "(°)"),
    (re.compile(r"\bA\.?U\.?\b"), "a.u."),
    (re.compile(r"\bsec\b"), "s"),
    (re.compile(r"\bmins\b"), "min"),
    (re.compile(r"\bminutes\b"), "min"),
    (re.compile(r"\bMM:SS\b"), "min"),
    (re.compile(r"\bk-k\b"), "k–k"),
]

def canon_axis(s):
    """Canonical axis label for `s`. Unknown labels still get unit-glyph normalisation."""
    if not s: return s
    t = s.strip()
    if t in AXIS: return AXIS[t]
    for rx, rep in UNIT_FIX:
        t = rx.sub(rep, t)
    return t

_NSUF = re.compile(r"\s*\((?:N|n)\s*=\s*\d+\)\s*$")
_TRAIL = re.compile(r"\s*\((?:from NEBD|1/3|2/3-sis on-target|2/3-sis)\)\s*$", re.I)

def canon_group(s):
    """Canonical short cohort name for `s` (tick labels, legend entries). Unknown names pass through.

    Legend entries carry their N ("1-Sisterless (N=28)") and sometimes a parenthetical qualifier
    ("unmodified (from NEBD)", "Collagen (2/3-sis on-target)"). An exact-match table alone therefore missed
    every legend on the deck while getting the tick labels right -- caught by LOOKING at the first PUB
    render. The count is stripped, the name canonicalised, and the count put back, so no information is
    lost and the cohort is still named the same way everywhere."""
    if not s: return s
    t = s.strip()
    if t in GROUP: return GROUP[t]
    flat = t.replace("\n", " ").strip()
    if flat in GROUP: return GROUP[flat]
    m = _NSUF.search(flat)
    n = m.group(0).strip() if m else ""
    core = _NSUF.sub("", flat).strip()
    if core in GROUP: return (GROUP[core] + " " + n).strip()
    core2 = _TRAIL.sub("", core).strip()
    if core2 in GROUP: return (GROUP[core2] + " " + n).strip()
    # MULTI-LINE TICK LABELS. A phase-split violin labels its columns "1-Sisterless\nProphase"; matching the
    # flattened string finds nothing, so each LINE is canonicalised on its own and the layout is preserved.
    # Caught by looking at the publication render, not by the text scan.
    if "\n" in t:
        parts = [canon_group(p) for p in t.split("\n")]
        if parts != t.split("\n"): return "\n".join(parts)
    # last resort: any "<N>-Sisterless" + off-target composite, however it was joined
    m = re.match(r"^\d-Sisterless\s*[/·|-]?\s*off-target$", t, re.I)
    if m: return "off-target"
    # PREFIX MATCH. Legend entries append all sorts of things to the cohort name -- "(n=4 KTs)",
    # " — 18 cells, 529 points", " trend". Replace the leading cohort name and keep the rest, longest
    # key first so "1-Sisterless off-target" is not eaten by "1-Sisterless".
    for k in sorted(GROUP, key=len, reverse=True):
        if "\n" in k: continue
        if flat.startswith(k) and (len(flat) == len(k) or not flat[len(k)].isalnum()):
            return GROUP[k] + flat[len(k):]
    return s

def abbreviation_table():
    """Rows for the 'defined once' key: (abbreviation, full name)."""
    return sorted(GROUP_FULL.items())


# ==================================================================================================
# CANONICAL COHORT ORDER
# ==================================================================================================
# USER 2026-08-20 (board 5 item 7): *"for the bar plot below, and (for other applicable places like this in
# other applicable plots, mainly where off-target is combined into one group), plot the bars in the order of
# unmovified, off-target, 1 sisterless, and 3 sisterless from left to right"*.
#
# The order is LEAST to MOST manipulated, which is also the order the reader needs to compare against: the
# two controls first, then the two ablation cohorts. Kept here beside the name map so a figure cannot get
# canonical NAMES and a different ORDER; `order_key` sorts any mix of raw or canonical labels.
GROUP_ORDER = ["unmod", "off-target", "1-sis", "2-sis", "3-sis", "4-sis",
               "dbl-KT", "dbl-chr", "collagen", "meta-abl"]


def order_key(label):
    """Sort key putting cohorts in her order. Unknown labels sort last, alphabetically, so a new cohort is
    visible at the end rather than silently jumping to the front."""
    g = canon_group(label)
    return (GROUP_ORDER.index(g), "") if g in GROUP_ORDER else (len(GROUP_ORDER), str(label))


def sort_groups(labels):
    """-> the same labels, in her canonical order."""
    return sorted(labels, key=order_key)


# ── ONE colour for "single" vs "triple" ablation, everywhere ────────────────────────────────────────
# USER 2026-08-20 (artboard 8, item 7): "the colors used in the k-k plot over time we discussed above are
# unique among the other plots on artboard 8, so coordinate them with the common scheme used in the other
# plots."
#
# Artboard 8's bar plots and the oscillation panels already agreed on blue/orange-red for 1- vs
# 3-sisterless (`custom_prometa_vs_meta_20260810.COL`, `kk_osc_refined.COL`). `kt_tension_metaphase.ABL_COL`
# was the odd one out at green/purple, so the same cell type changed colour between neighbouring plots on
# the same board. Defining it once here means the answer cannot drift again -- and it retires a green from
# a palette that elsewhere carries a red for "lagging" (NOTES rule 30).
SIS_COLOR = {"1": "#2a7fff", "3": "#ff5a3c"}
SIS_COLOR.update({"single": SIS_COLOR["1"], "1-sis": SIS_COLOR["1"], "1-Sister": SIS_COLOR["1"],
                  "1-Sisterless": SIS_COLOR["1"], "triple": SIS_COLOR["3"], "3-sis": SIS_COLOR["3"],
                  "3-Sister": SIS_COLOR["3"], "3-Sisterless": SIS_COLOR["3"]})


def sis_color(key, default="#888888"):
    """Canonical colour for a 1- vs 3-sisterless series, by any of its spellings."""
    return SIS_COLOR.get(str(key).strip(), default)


# USER 2026-08-20 (artboard 8, item 6): "The x-axis is far too long; it should be no more than 4 words and
# then units." Same rule applied to the sibling y-axes on that board, which still carried ad-hoc wording.
AXIS.update({
    "amplitude (um, SD)":              "Oscillation amplitude (µm)",
    "oscillation amplitude (um, SD)":  "Oscillation amplitude (µm)",
    "amplitude (µm, SD)":              "Oscillation amplitude (µm)",
    "model pos (um)":                  "Kinetochore position (µm)",
    "model pos (µm)":                  "Kinetochore position (µm)",
    "time (min)":                      "Time (min)",
})
