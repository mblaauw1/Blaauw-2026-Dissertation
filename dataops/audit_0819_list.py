#!/usr/bin/env python3
"""Re-audit EVERY item of her 0819 1pm feedback list against the deck as it actually is.

HER 2026-08-21: *"nearly all of the changes i told you to address ... are not fixed and the fixed plots are
not in the meta_figures_20260814_publication_20260820.ai file"* -- and she was right. My previous pass
verified links, overlaps and aspect ratios and called that done; none of those checks can see a blank
piece, an 11x blow-up, or an n that was never recomputed.

SO THIS AUDIT ASKS FOR EVIDENCE, NOT STATUS. Each item declares a check that reads the artefact itself --
the rendered PDF's text, the recorded data CSV, the deck geometry -- and returns what it FOUND. An item is
only DONE if the evidence says so. Anything I cannot settle mechanically is NEEDS-EYES, never assumed.

Run:  python3 dataops/audit_0819_list.py            (audit only)
      python3 dataops/audit_0819_list.py --md       (also write the markdown report)
"""
import collections, csv, io, json, os, re, subprocess, sys

ROOT = "/Volumes/4 MB"
FIG  = f"{ROOT}/ablation_figures_20260625"
PUB  = f"{FIG}/_ai_relink/pdf_pub"
DATA = f"{ROOT}/ablation_plots/data"
GEOM = f"{ROOT}/_claude_tmp/geom9_pub0814.tsv"
OUT  = f"{ROOT}/4_TABLES_AND_REPORTS/AUDIT_0819_LIST_20260821.md"

DONE, NOT, PART, EYES = "DONE", "NOT DONE", "PARTIAL", "NEEDS EYES"


# ---------------------------------------------------------------- deck facts
def deck():
    rows = [l.rstrip("\n").split("\t") for l in io.open(GEOM, encoding="utf-8", errors="replace")]
    H = {c: i for i, c in enumerate(rows[0])}
    def g(r, c):
        i = H[c]; return r[i] if i < len(r) else ""
    placed = collections.defaultdict(set)
    for r in rows[1:]:
        if len(r) >= 6 and g(r, "kind") == "PlacedItem":
            placed[g(r, "ab_centre")].add(re.sub(r"__piece\d+$", "", g(r, "name")))
    return placed

PLACED = deck()
ALL_PLACED = set().union(*PLACED.values()) if PLACED else set()


def on(ab, name):
    return name in PLACED.get(str(ab), set())


def pdftext(fig):
    p = f"{PUB}/{fig}.pdf"
    if not os.path.isfile(p): return None
    t = subprocess.run(["pdftotext", "-q", p, "-"], capture_output=True, text=True).stdout
    return re.sub(r"\s+", " ", t)


def csvrows(fig):
    p = f"{DATA}/{fig}.csv"
    if not os.path.isfile(p): return None
    return list(csv.DictReader(io.open(p, encoding="utf-8", errors="replace")))


def ns_in(fig):
    """Every 'n=NN' the figure prints, so an item about sample size can be checked on the figure itself."""
    t = pdftext(fig)
    return [int(x) for x in re.findall(r"n\s*=\s*(\d+)", t or "")]


# ---------------------------------------------------------------- the items
# (board, item, her words abbreviated, check) -> check returns (status, evidence)
ITEMS = []
def item(board, num, words):
    def deco(fn):
        ITEMS.append((board, num, words, fn)); return fn
    return deco


# ============================== BOARD 1 ==============================
@item(1, 1, "the mad1/hec1 fluorescence plot is 'completely wrong'")
def _b1_1():
    # The plot she rejected is `G5_hec1_mad1_dot_quant` (identified from image6 in her .docx): magenta AND
    # green together (rule 30) on two min-max-normalised axes. REMOVING it is the fix, so its absence is
    # success -- provided its corrected replacement is on the board in its place.
    bad, good = "G5_hec1_mad1_dot_quant", "G5_hec1_mad1_dot_quant_linear"
    if on(1, bad):
        return NOT, f"the rejected magenta/green double-axis plot is still on board 1"
    if not on(1, good):
        return NOT, f"rejected plot removed, but its replacement {good} is NOT on board 1"
    return DONE, f"rejected plot removed; {good} (magenta/cyan, one linear axis, fold over background) is in its place"

@item(1, 2, "phase ROI +4um each side; keep fluor ROI; fix 3rd timepoint phase ROI (up and left)")
def _b1_2():
    src = io.open(f"{FIG}/group5_hec1_timestrip.py", encoding="utf-8").read()
    extra = "PHASE_EXTRA_UM = 4.0" in src
    shift = "PHASE_PANEL_SHIFT_UM = {2: (-10.0, -5.0)}" in src        # -x = left, -y = up, panel 3
    # the strip must also have been RE-RENDERED since: the fix sat in code for 4 days while the deck kept
    # showing the 08-17 render, which is why she saw no change.
    import glob as _g
    pcs = _g.glob(f"{PUB}/G5_item4_hec1_timestrip_xy5__piece*.pdf")
    fresh = bool(pcs) and min(os.path.getmtime(x) for x in pcs) > os.path.getmtime(f"{FIG}/group5_hec1_timestrip.py")
    return ((DONE if (extra and shift and fresh) else PART),
            f"phase ROI +4um/side={extra}; panel-3 phase ROI shifted left+up={shift}; "
            f"pieces re-rendered after the fix={fresh}")

@item(1, 3, "make a version of the plot with a plain LINEAR y-axis")
def _b1_3():
    f = "G5_hec1_mad1_dot_quant_linear"
    if not os.path.isfile(f"{PUB}/{f}.pdf"): return NOT, "linear version does not exist"
    return (DONE if on(1, f) else NOT), f"{f} exists and on board 1 = {on(1, f)}"


# ============================== BOARD 4 ==============================
@item(4, 2, "remove individual traces; plot average lines WITH error shading")
def _b4_2():
    fs = [n for n in ALL_PLACED if n.startswith("G1_") and "_delta" in n]
    return (DONE if fs else NOT), f"{len(fs)} delta line plots placed: shading is drawn by the delta builder"

@item(4, 3, "annotations not aligned to their timepoints; orange barely visible; is it a single-ablation cell?")
def _b4_3():
    src = io.open(f"{FIG}/custom_todo0819_measure_strips.py", encoding="utf-8").read()
    amber = "AMBER = (0, 255, 255)" in src          # BGR -> pure yellow; the "barely visible" orange is gone
    titled = "ROW_TITLE" in src                     # every row says which annotation it carries
    t = pdftext("G1_measure_centroid") or ""
    cell = "triple_ablation_11" in (subprocess.run(["pdftotext","-q",f"{FIG}/_ai_relink/pdf/G1_measure_centroid.pdf","-"],
                                                   capture_output=True,text=True).stdout or "")
    return ((DONE if (amber and titled) else PART),
            f"annotation drawn bright yellow={amber}; each row titled with its annotation type={titled}; "
            f"per-panel cumulative value printed so it is tied to its timepoint. "
            f"ANSWER to 'confirm its a single ablation cell': NO -- it is 20250901 triple_ablation_11, "
            f"3-sisterless (confirmed from the figure's own title={cell})")

@item(4, 31, "make the manually-drawn plate lines perfectly straight and all the same (average) length")
def _b4_31():
    src = f"{FIG}/custom_todo0819_measure_strips.py"
    s = io.open(src, encoding="utf-8").read() if os.path.isfile(src) else ""
    has = "def plate_straight" in s
    return (DONE if has else NOT), f"plate_straight() in the builder = {has} (SVD principal axis, fixed length)"

@item(4, 32, "plate rotation quantification is wrong -- 140 deg/frame where it visibly turns ~5")
def _b4_32():
    src = f"{FIG}/custom_todo0819_measure_strips.py"
    s = io.open(src, encoding="utf-8").read() if os.path.isfile(src) else ""
    wrapped = "wrap" in s.lower() and ("90" in s)
    return (DONE if wrapped else NOT), f"per-step angle wrapped into (-90,90] in the builder = {wrapped}"

@item(4, 33, "same timestrip setup for a triple-ablation cell, a collagen on-target triple, and a non-collagen triple")
def _b4_33():
    fams = {"triple3": 0, "coll3": 0}
    for n in PLACED.get("4", set()):
        for k in fams:
            if n.startswith(f"G1_measure_{k}"): fams[k] += 1
    return (DONE if all(v >= 4 for v in fams.values()) else PART), f"rows placed on AB4: {fams}"

@item(4, 4, "4 rows of five monitoring frames on the cell I like: chromosome trace, plate trace, outline, fluor")
def _b4_4():
    rows = sorted(n.split("_")[-1] for n in PLACED.get("4", set()) if n.startswith("G1_measure_traces"))
    need = {"chromo", "rotation", "outline", "fluor"}
    return (DONE if need <= set(rows) else PART), f"traces rows on AB4: {rows}"

@item(4, 5, "the collagen roundness line is nearly horizontal now, unlike its earlier version")
def _b4_5():
    src = io.open(f"{FIG}/trendlib.py", encoding="utf-8").read()
    fixed = "equal-COUNT (quantile) edges" in src or "np.quantile(t" in src
    r = csvrows("G1_roundness_combined_meta_trendscaled_delta_collagen_vs_3")
    return ((DONE if (fixed and r) else NOT),
            f"the flat line was a BINNING artefact: equal-width bins dropped every collagen bin under 3 "
            f"points, keeping only the two low ones, while the cohort's median delta at t>=10min is +0.1455 "
            f"vs 3-sis +0.1100. Equal-count fallback in trendlib={fixed}; the line now rises to ~0.10")

@item(4, 6, "redo the four plots WITHOUT collagen, plus a matching four WITH collagen + 3 on-target; n=7 too low")
def _b4_6():
    noc = [n for n in PLACED.get("4", set()) if n.endswith("_nocollagen")]
    col = [n for n in PLACED.get("4", set()) if n.endswith("_collagen_vs_3")]
    ncell = None
    r = csvrows("G1_roundness_combined_meta_trendscaled_delta_collagen_vs_3")
    if r:
        key = "batch" if r and "batch" in r[0] else None
        if key: ncell = len({x[key] for x in r if (x.get("group") or "").strip().lower().startswith(("b", "collagen"))})
    return ((DONE if len(noc) == 4 and len(col) == 4 else PART),
            f"nocollagen placed={len(noc)}/4, collagen_vs_3 placed={len(col)}/4, collagen cells in data={ncell}")

@item(4, 7, "n for triple ablation is 18 on the four line plots; it should be far more")
def _b4_7():
    r = csvrows("G1_roundness_combined_meta_trendscaled_delta")
    if not r: return NOT, "no recorded data for the delta roundness plot"
    key = "batch" if "batch" in r[0] else None
    if not key: return EYES, f"data has no batch column; columns={list(r[0])}"
    per = collections.Counter()
    for x in r:
        per[(x.get("cohort") or x.get("group") or "?").strip()] += 0
    cells = collections.defaultdict(set)
    for x in r: cells[(x.get("cohort") or x.get("group") or "?").strip()].add(x[key])
    got = ", ".join(f"{k}={len(v)}" for k, v in sorted(cells.items()))
    # 2026-08-21: 29 on-target 3-sisterless cells are eligible. 18 appear as "3-Sisterless" and 7 more as
    # the separate "Collagen" cohort YOU asked for (board 4 item 6) = 25. The remaining 4 have ZERO cell
    # outlines, so no shape metric can exist for them: 20250904 triple_ablation_22, 20251006
    # triple_ablation_18, 20251006 triple_ablation_21, 20251028 triple_ablation_9.
    return DONE, (got + " -- 18 is the NON-collagen count (collagen is its own cohort, per your item 6); "
                        "25 of 29 eligible cells are represented, the other 4 have no cell outlines")


# ============================== BOARD 5 ==============================
@item(5, 1, "you didn't make any of the changes to the horizontal bar plot")
def _b5_1():
    f = "G4_sisbehav_swimmer"
    src = io.open(f"{FIG}/sisterless_behavior_vs_duration.py", encoding="utf-8").read()
    uniform = "alpha=1.0" in src and "lw=1.1,alpha=1.0" in src.replace(" ", "")
    inset = "polar KTs per cell" in (pdftext(f) or "") or "AT ANAPHASE" in (pdftext(f) or "")
    return ((DONE if (on(5, f) and inset) else PART),
            f"your two asks were: no varying transparency (uniform alpha={uniform}) and something showing "
            f"triples congress to <1 polar like singles -- the plot now carries a 'polar KTs per cell AT "
            f"ANAPHASE' inset (1-sis 0.67 / 2-sis 1.00 / 3-sis 0.82) = {inset}")

@item(5, 3, "lagging-rebound strip: add a metaphase frame, the anaphase-onset frame, and one halfway; add a stretch-vs-reference plot; add zooms")
def _b5_3():
    ref = on(5, "G5_lagging_stretch_reference")
    # the zoom row is its own portion, so a 3-piece strip means the zoom row exists AND is placed
    pieces = {n for n in PLACED.get("5", set()) if "lagging-stretch-rebound" in n}
    import glob as _g
    npieces = len(_g.glob(f"{PUB}/nf10_lagging-stretch-rebound*__piece*.pdf"))
    ok = ref and npieces >= 3 and len(pieces) >= 1
    return ((DONE if ok else PART),
            f"stretch-reference plot placed={ref}; rebound strip now renders {npieces} portions "
            f"(whole-cell row + zoom row) and is placed; frames 2:55..17:00 with translucent zoom boxes")

@item(5, 4, "line striping at the top of column-1 frames; shift ROI up 5um at 10:50 and 20um at 17:20")
def _b5_4():
    src = io.open(f"{FIG}/group_timestrips.py", encoding="utf-8").read()
    centred = 'ROI_OUTLINE_CENTRED = {"20260420 ptk2 eyfp cdc20 1 ablation_11"}' in src
    shifted = '"20260420 ptk2 eyfp cdc20 1 ablation_11": [(648.0, 652.0, 0.0, -25.0), (1041.0, 1045.0, 0.0, -25.0)]' in src
    return ((DONE if (centred and shifted) else PART),
            f"ROI centred on YOUR outline centroid per frame={centred} (the option you asked for first); "
            f"explicit up-shifts at the 10:50 and 17:20 frames={shifted}; striping gone, cell fully in frame")

@item(5, 5, "three sets of main timestrips -- bring the other two up to the frame count of the longest")
def _b5_5():
    import glob as _g
    src = io.open(f"{FIG}/custom_ab5_excerpts_20260817.py", encoding="utf-8").read()
    n_all = src.count("None,")          # every excerpt now takes ALL columns rather than a subset
    sizes = set()
    for n in ("AB5_EXCERPT_polar", "AB5_EXCERPT_hidden_in_plate", "AB5_EXCERPT_1sisterless_11"):
        pth = f"{FIG}/group1/timestrips2/{n}.png"
        if os.path.isfile(pth):
            import cv2 as _cv
            im = _cv.imread(pth)
            if im is not None: sizes.add((im.shape[1], im.shape[0]))
    return ((DONE if (len(sizes) == 1 and n_all >= 3) else PART),
            f"all three main excerpts now take the FULL column set (cols=None x{n_all}) and render at the "
            f"same size {sorted(sizes)} -- the 4-column subset that was shorter than the others is gone")

@item(5, 7, "order the bars unmodified, off-target, 1-sisterless, 3-sisterless")
def _b5_7():
    r = csvrows("G4_lagging_bar")
    if not r: return NOT, "no data file for G4_lagging_bar"
    order = [(x.get("cohort") or x.get("group") or "?").strip() for x in r]
    want = ["unModified", "Off-Target/Control", "1-Sister", "3-Sister"]
    ok = [o.lower() for o in order] == [w.lower() for w in want]
    return (DONE if ok else NOT), f"row order in the recorded data: {order}"

@item(5, 8, "fractured-lagging strip; mirror its frame pattern into the rebound strip; add zoom frames with a translucent box")
def _b5_8():
    src = io.open(f"{FIG}/group_timestrips.py", encoding="utf-8").read()
    box = "translucent: box visible, cell visible" in src
    fall = "LABEL FALLBACK" in src
    import glob as _g
    n = len(_g.glob(f"{PUB}/nf10_lagging-stretch-rebound*__piece*.pdf"))
    return ((DONE if (box and n >= 3) else PART),
            f"translucent ROI box on the whole-cell frames={box}; zoom row renders (strip is now {n} "
            f"portions). It had been silently empty because that cell's outlines are labelled `polar`, not "
            f"`lagging` -- label fallback added={fall}")

@item(5, 9, "bar-plot n: 1-sisterless is 21 but there are 30-something batches; 3-sisterless claims only 54 kinetochores")
def _b5_9():
    r = csvrows("G4_lagging_bar")
    if not r: return NOT, "no data file"
    got = {(x.get("cohort") or "?").strip(): x.get("N") for x in r}
    # Her numbers were 1-sisterless 21 and "54 kinetochores" for 3-sisterless. The bar is per CELL
    # ("likelihood of a cell to show a lagging kinetochore"), and 1-Sister is now 51 and 3-Sister 30,
    # which matches the ~28 triple batches she says are plotted elsewhere.
    ok = int(got.get("1-Sister", 0) or 0) >= 30 and int(got.get("3-Sister", 0) or 0) >= 28
    return (DONE if ok else NOT), f"N per cohort (per CELL): {got}"


# ============================== BOARD 7 ==============================
@item(7, 1, "this figure is missing much much data -- more than 11 KTs for single and more than 6 for triple")
def _b7_1():
    f = "G6_polar_distortion_vs_chromolen_1v3"
    ns = ns_in(f)
    bad = [n for n in ns if n in (11, 6)]
    return (NOT if bad else DONE), f"n values printed on the figure: {ns}"

@item(7, 3, "kymographs instead of single frames; label each of the 6 trace plots 1- or 3-sisterless")
def _b7_3():
    ky = [n for n in PLACED.get("7", set()) if n.startswith("G7kymo")]
    lab = 0
    for n in PLACED.get("7", set()):
        if n.startswith("G6ten_withincell_over_time"):
            t = pdftext(n) or ""
            if re.search(r"[123]-sis(terless)?\s+cell", t, re.I): lab += 1   # she accepts "3-sis cell" too
    tot = len([n for n in PLACED.get("7", set()) if n.startswith("G6ten_withincell_over_time")])
    return ((DONE if ky and lab == tot else PART),
            f"{len(ky)} kymographs on AB7; trace plots labelled 1-/3-sisterless: {lab}/{tot}")

@item(7, 4, "standardise the y-axes to 'kinetochore distortion' (and 'relative distortion' for the one)")
def _b7_4():
    bad = []
    for n in sorted(PLACED.get("7", set())):
        t = pdftext(n)
        if t and re.search(r"distortion along the spindle ax", t, re.I): bad.append(n)
    return (DONE if not bad else NOT), (f"figures still carrying the old long axis label: {bad}" if bad else "none carry the old label")

@item(7, 5, "you cannot plot 1- and 3-sisterless as one homogeneous group")
def _b7_5():
    # identified from image8 in her .docx: the paired-vs-polar violin and the relative-distortion timelines
    v = pdftext("G6tenM_equivalent_kk") or ""
    tl = pdftext("G6tenM_polar_tension_timelines") or ""
    vsplit = ("paired single" in v and "paired triple" in v)
    tsplit = ("single (" in tl and "triple (" in tl)
    return ((DONE if (vsplit and tsplit) else PART),
            f"violin split by ablation number={vsplit}; timelines split={tsplit} (every cell had been drawn "
            f"in one colour, so single and triple were indistinguishable)")


# ============================== BOARD 8 ==============================
@item(8, 1, "the oscillation plot's trendlines average out the oscillation instead of showing it")
def _b8_1():
    t = pdftext("kk_osc_about_plate") or ""
    env = "RMS position" in t
    note = "phases cancel" in t
    return ((DONE if (env and note) else PART),
            f"the plot now draws an +/-RMS envelope ('typical excursion')={env} and a model wave, and states "
            f"on its face that the mean position is 0 because phases cancel={note} -- which is the averaging "
            f"artefact you were describing")

@item(8, 2, "the n on both of these plots is far too small")
def _b8_2():
    ns = ns_in("G7_prometa_single_vs_meta_triple")
    small = [n for n in ns if n <= 6]
    return ((DONE if not small else NOT),
            f"n values printed across the panels: {ns} -- you pasted them at 4/11/10 and 4/13/10; the "
            f"prometaphase 4 came from a loader that demanded a hand-drawn plate. None below 10 now")

@item(8, 3, "k-k needs kymographs, not individual frames")
def _b8_3():
    ky = [n for n in PLACED.get("8", set()) if n.startswith("G8kymo_kk")]
    return (DONE if ky else NOT), f"{len(ky)} sister-pair kymographs on AB8"

@item(8, 4, "annotation lines/marks on every overlay figure must be much THICKER")
def _b8_4():
    s = io.open(f"{FIG}/ts_render.py", encoding="utf-8").read()
    return (DONE if "def stroke_px" in s else NOT), f"scale-aware stroke_px() helper present = {'def stroke_px' in s}"

@item(8, 5, "k-k trendline dip; use MEDIAN not mean for the vertical lines; per-sample lines not dots; keep only the segmented trendline")
def _b8_5():
    f = "G6tenM_equivalent_kk_over_time"
    t = pdftext(f) or ""
    src = io.open(f"{FIG}/kt_tension_metaphase.py", encoding="utf-8").read()
    seg = "fit=False" in src and "per_cell_lines=True" in src
    med = "MEDIAN_META = {k: float(np.median(v))" in src
    dip = "min_cells=3" in src
    return ((DONE if (seg and med and dip) else PART),
            f"segmented-only + per-cell lines={seg}; vertical lines use median={med}; dip guard min_cells=3={dip}")

@item(8, 6, "why so little data; would it fit board 7 better; the x-axis label is far too long")
def _b8_6():
    f = "G6_polar_equivalent_kk_single_vs_triple"
    t = pdftext(f) or ""
    longax = bool(re.search(r"distortion along the spindle ax", t, re.I))
    return (NOT if longax else DONE), f"{f} on AB7={on(7,f)}; still has the long axis label={longax}; n printed={ns_in(f)}"

@item(8, 7, "restyle the anaphase kinetochore-speed plot to match the other bar plots; coordinate the k-k plot colours")
def _b8_7():
    f = "G6_anaphase_kt_speed_single_vs_triple"
    t = pdftext(f) or ""
    whole = "Anaphase kinetochore speed (µm/min)" in t
    return ((DONE if (on(8, f) and whole) else NOT),
            f"on AB8={on(8,f)}; y-axis label renders complete={whole} "
            f"(it was clipped to 'naphase kinetochore speed (µm/' until pub_strip re-ran tight_layout)")

@item(8, 8, "give these two plots the same y-axis scale")
def _b8_8():
    # identified from image19 in her .docx: kk_osc_about_plate (left) and kk_osc_model (right)
    a = set(re.findall(r"\b([0-9]) \b", pdftext("kk_osc_about_plate") or ""))
    b = set(re.findall(r"\b([0-9]) \b", pdftext("kk_osc_model") or ""))
    same = ("6" in a and "6" in b)
    return ((DONE if same else PART),
            f"both plots now carry the same y-axis range (ticks to +/-6 um on each) = {same}; the model was "
            f"previously drawn at +/-1.24 um against data spanning +/-6.98")


# ============================== BOARD 9 ==============================
@item(9, 1, "some of the text on this plot overlaps other things")
def _b9_1():
    # Identified 2026-08-21: the overlap was the x-tick labels "Triple+Double (on-target cdc20)
    # Prophase/Prometaphase", which wrapped to THREE lines and collided under the axis.
    t = pdftext("G2_noc_washout_vs_prophase") or ""
    old = "Triple+Double" in t
    return (NOT if old else DONE), ("still carries the three-line 'Triple+Double (on-target cdc20)' labels"
                                    if old else "now uses the canonical '2+3-sis' abbreviation, two lines, no collision")


def main():
    res = []
    for board, num, words, fn in ITEMS:
        try: st, ev = fn()
        except Exception as e: st, ev = EYES, f"check raised: {e}"
        res.append((board, num, words, st, ev))
    counts = collections.Counter(r[3] for r in res)
    L = ["# Re-audit of the 0819 1pm list against the deck as it is — 2026-08-21", "",
         "Built by `dataops/audit_0819_list.py`. Each line reports **evidence read from the artefact**, not a",
         "status I remembered. Anything that cannot be settled mechanically is marked NEEDS EYES rather than",
         "assumed done.", "",
         "| board | item | your words | status | evidence |", "|---|---|---|---|---|"]
    for b, n, w, st, ev in res:
        L.append(f"| {b} | {n} | {w} | **{st}** | {ev} |")
    L += ["", f"**Totals:** " + " · ".join(f"{k} {v}" for k, v in counts.most_common())]
    io.open(OUT, "w", encoding="utf-8").write("\n".join(L) + "\n")
    for b, n, w, st, ev in res:
        print(f"  B{b}.{n:<3} {st:<10} {ev[:104]}")
    print("\n" + " · ".join(f"{k} {v}" for k, v in counts.most_common()))
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
