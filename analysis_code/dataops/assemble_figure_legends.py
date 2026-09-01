#!/usr/bin/env python3
"""Pair every panel that is ACTUALLY ON the publication deck with the legend sentence SHE wrote for it.

HER INSTRUCTION, 2026-08-21: *"the numbering of the figures has been changed, reordered, combined, etc,
while all those versions of the legends were being written ... you should know what everything on the figure
is actually for, and then it corresponds with some part of the legend drafts that i wrote, and you just have
to pair the two (and again, dont use any of your own sentences, only use sentences that ive written)"*

SO THE FIGURE NUMBER IS NOT THE KEY. Matching Figure 4 in a legend draft to Figure 4 on the deck is exactly
the mistake — her Figure 3 (Mad1) is now part of Figure 1, her Figure 7 is now part of Figure 3, and the
whole set renumbered 10 -> 9. The key is WHAT THE PANEL IS. Each entry below names a placed figure on the
deck and the panel description she wrote for that same thing, wherever in her drafts it lives.

SOURCES, all hers (mirrored in 4_TABLES_AND_REPORTS/WRITING_CORPUS_20260821/):
  P = legends_pasted_20260821.txt       the legend draft she pasted 2026-08-21
  D = paper_draft.txt                   `# Figure Legends` and `# Old Figure Legends` in "Paper draft"
  W = results_working_document.txt      "Results working document" — the figure-by-figure plan

Same guarantee as the Results/Discussion assembler: nothing is retyped. Each brick is an
(source, start anchor, end anchor) triple and the text is CUT OUT of her file at build time; a stale anchor
FAILS the build rather than emitting anything unverified. Mine, and only outside her prose: the artboard
headings and the panel keys (the deck's own figure filenames).

A panel with no legend text she has written anywhere is listed under NEEDS A LEGEND rather than given one.
"""
import collections, io, json, os, re, sys, unicodedata

ROOT = "/Volumes/4 MB"
CORP = f"{ROOT}/4_TABLES_AND_REPORTS/WRITING_CORPUS_20260821"
GEOM = f"{ROOT}/_claude_tmp/geom9_pub0814.tsv"
OUT  = f"{ROOT}/4_TABLES_AND_REPORTS/FIGURE_LEGENDS_20260821.md"

SRC = {"P": "legends_pasted_20260821.txt",
       "D": "paper_draft.txt",
       "W": "results_working_document.txt"}


def flat(s):
    s = unicodedata.normalize("NFC", s).replace("\u00ad", "")
    s = re.sub(r"\\([\[\]#*_])", r"\1", s)
    # Strip MARKDOWN BOLD only. A blanket \*\* strip also eats her significance markers -- "* (p<0.05),
    # ** (p<0.01), *** (p<0.001)" came out as "* (p<0.05), (p<0.01), * (p<0.001)", which changes what the
    # legend says. Bold delimiters hug their text; her markers have a space on both sides and *** is a
    # run of three, so require a run of exactly two that touches a non-space on one side.
    s = re.sub(r"(?<!\*)\*{2}(?!\*)(?=\S)|(?<=\S)(?<!\*)\*{2}(?!\*)", "", s)
    s = re.sub(r"\[BM\d+\]", "", s)
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"\s+([.,;:?!])", r"\1", s)
    return s.strip()


CORPUS = {k: flat(io.open(f"{CORP}/{v}", encoding="utf-8", errors="replace").read()) for k, v in SRC.items()}


class Missing(Exception):
    pass


def cut(src, start, end):
    hay = CORPUS[src]
    i = hay.find(flat(start))
    if i < 0:
        raise Missing(f"[{src}] start anchor not found: {start[:70]!r}")
    j = hay.find(flat(end), i)
    if j < 0:
        raise Missing(f"[{src}] end anchor not found after start: {end[:70]!r}")
    return hay[i:j + len(flat(end))]


# ---------------------------------------------------------------------------------------------------
# THE PAIRING.  key = the figure's filename on the deck (pieces collapsed).  value = her text for it.
# `None` means she has not written a legend for that panel anywhere -- reported, never invented.
# ---------------------------------------------------------------------------------------------------
PAIR = {
 # ---- AB1, "Fig 1": ablation creates sisterless kinetochores, AND Mad1 retention (her old Fig 3 merged in)
 "nf9_unmanipulated-control__20250320_ptk_yfpcdc20__1_xy3":
   ("D", "Unmodified timestrip:", "align at the metaphase plate"),
 "nf10_1-sisterless-persistent-polar__20250402_ptk_yfpcdc20_2":
   ("P", "Single ablation timestrip:", "phase panels are the middle-most from that z-stack."),
 "nf9_3-sisterless__20260417_ptk2_eyfp_cdc20_ablation_18":
   ("P", "Triple ablation timestrip:", "Selected frames from a cell with two sisterless kinetochores."),
 "nf10_off-target__20250402_ptk_yfpcdc20_22":
   ("P", "Off-target timestrip:", "but still give the same energy."),
 "G4_prepost_intensity":
   ("P", "Before-after fluorescence timestrip:", "between 10-30s after laser destruction."),
 "G5_item4_hec1_timestrip_xy5":
   ("P", "Mad1 plus Hec1 frames:", "metaphase (middle), and anaphase (right)."),
 "G5_hec1_mad1_dot_quant":
   ("P", "Mad1 vs hec1 plot:", "the timestrip shown in (A)."),
 "G5_hec1_mad1_dot_quant_linear":
   ("P", "Mad1 fluorescence vs time:", "on another kinetochore was visible."),
 "G5_mad1_timestrip_20260310_ptk2_eyfp_mad1_14_aligned":
   ("P", "Mad1 at sisterless kinetochores:", "created in metaphase, prometaphase, or prophase."),

 # ---- AB2, "Fig 2": more than one sisterless kinetochore is needed to lengthen metaphase
 "G1_violin2_no_dc_offtarget_journal":
   ("P", "Main violin:", "*** (p<0.001)"),
 "G4_exhaustion_violin_journal":
   ("P", "Exhaustion violins, cartoon:", "only escapable by mitotic exhaustion."),
 "G3_slippage_timestrip_nocodazole_aligned":
   ("P", "Low dose noc timestrip:", "Timestrip of nocodazole-treated metaphase cell."),
 "G4_zm_full__p1":
   ("P", "Zm violins, cartoon:", "schematic of the ZM experiment."),
 "G9_drug_timestrip_zm18_aligned":
   ("P", "Zm timestrip:", "three sisterless kinetochores through mitosis."),

 # ---- AB5, "Fig 3": sisterless-kinetochore fate at anaphase onset (her old Fig 4 + Fig 7 merged)
 "AB5_EXCERPT_polar":
   ("P", "Timestrip of pole localization, congression, plate-localized, cartoons?:",
         "or move from the former to the latter."),
 "AB5_EXCERPT_hidden_in_plate": "SAME AS AB5_EXCERPT_polar",
 "AB5_EXCERPT_1sisterless_11":  "SAME AS AB5_EXCERPT_polar",
 "G3_kt_fate":
   ("P", "Combined columns:", "three possible types of movement patterns."),
 "nf10_lagging-stretch-rebound__20260303_Mad1_Ptk_Eyfpcdc2_ablation_1metaphase_52":
   ("P", "Timestrip of lagging, fractured lagging, cartoon:",
         "Lagging kinetochores are caused by merotelic connections."),
 "nf10_lagging-cand-single_ablation_15__20260416_single_ablation_15":
   "SAME AS nf10_lagging-stretch-rebound__20260303_Mad1_Ptk_Eyfpcdc2_ablation_1metaphase_52",
 "G4_lagging_bar":
   ("P", "Lagging bar plot:", "binned by sisterless kinetochore condition."),
 "G4_sisbehav_swimmer":
   ("P", "Sideways bar plot showing congression behavior within each batch over time.",
         "(0.82 vs 0.67, p=0.92)"),
 "G2_trend_single_vs_triple":
   ("P", "Plots of likelihood of chromosome behavior based on length in single vs triple:",
         "then congress to the metaphase plate."),
 "G3_length_vs_congression_time__p1":
   ("P", "Congression of longer chromosomes takes more time than congression of short chromosomes",
         "longer chromosomes need increased time to lose lateral attachments."),
 "G5_lagging_stretch_reference": None,

 # ---- AB7, "Fig 4": polar sisterless kinetochores deform like paired ones (her old Fig 5)
 "G6tenM_equivalent_kk":
   ("P", "Kinetochore shape deformation is caused by force application",
         "Left: Violin plot of force on polar vs force on paired."),
 "G6tenM_polar_tension_timelines":
   ("P", "Right: line plot of force on polar normalized to force on paired over time.",
         "Right: line plot of force on polar normalized to force on paired over time."),
 "G6ten_withincell_over_time":
   ("P", "Timestrip close-up of paired over time and polar over time:",
         "over the course of metaphase."),
 "G6_polar_distortion_vs_chromolen_1v3": None,
 "G6_polar_equivalent_kk_single_vs_triple": None,
 "G7kymo": None,

 # ---- AB8, "Fig 5": paired-kinetochore movement is not preserved (her old Fig 6)
 "G6tenM_equivalent_kk_over_time":
   ("P", "Difference in k-k distance between 1,3 box plot; k-k over time:",
         "k-k for pairs over the course of metaphase."),
 "G7_prometa_single_vs_meta_triple":
   ("P", "Amplitude difference; period difference; Model oscillation curves:",
         "Model oscillation curves illustrate movement differences (right)."),
 "kk_osc_model": "SAME AS G7_prometa_single_vs_meta_triple",
 "G2_dur_ana_to_cyto_journal":
   ("P", "Difference in movement to pole after anaphase between 1,3:",
         "(Left) Triple sisterless cells require more time to move from anaphase onset to cytokinesis."),
 "G6_anaphase_kt_speed_single_vs_triple":
   ("P", "(Right) At anaphase onset, the kinetochores in triple sisterless cells",
         "than in single sisterless or control cell types."),
 "kk_osc_about_plate": None,
 "G8kymo_kk": None,

 # ---- AB4, "Fig 6": cell-scale movement patterns are preserved (her old Fig 8)
 "G1_area_combined_meta_trendscaled_delta":
   ("P", "Whole-cell movement patterns in cells from different manipulation groups:",
         "these cells show more dramatic metamorphoses than other groups."),
 "G1_roundness_combined_meta_trendscaled_delta":   "SAME AS G1_area_combined_meta_trendscaled_delta",
 "G1_plate_rotation_combined_meta_trendscaled_delta": "SAME AS G1_area_combined_meta_trendscaled_delta",
 "G1_centroid_movement_combined_meta_trendscaled_delta": "SAME AS G1_area_combined_meta_trendscaled_delta",
 "G1_measure":
   ("P", "Frames from near the start and of metaphase for single and triple sisterless group",
         "and centroid movement (right)."),
 "G2_dur_align_to_meta_journal":
   ("P", "Violin plot showing that cells from different populations move through prometaphase",
         "do not affect mitotic processes before metaphase onset."),
 "G1_collagen_duration_dist": None,
 "G6_polepole_approx_absolute_time": None,

 # ---- AB9, "Fig 9": creating them before spindle formation shortens metaphase
 "nf9_1-sisterless__20250930_four_ablation_59":
   ("P", "Timestrip of creation of sisterless kinetochore in prophase before NEBD",
         "division of cytosol background fluorescence from nuclear background fluorescence."),
 "G7_prophase_vs_prometaphase_triple":
   ("P", "Violin plots of metaphase duration difference:",
         "if the sisterless kinetochores are present before NEBD."),
 "G2_kk_distance_by_phase":
   ("P", "Difference in k-k distances at ablation:",
         "as the spindle forms and pairs achieve spindle attachments."),
 "G3_lagging_by_creation_phase":
   ("P", "Kinetochore outcome location split by phase of sisterless creation:",
         "the time it had to achieve the end state before delaying metaphase did increase."),
 "G2_noc_washout_vs_prophase":
   ("P", "Schematic showing nocodazole washout in which cells previously in mitosis",
         "the sisterless kinetochore experience is that of creation before NEBD."),
 "G8_kt_speed_paired_vs_sisterless": None,
}

# Panels she wrote a legend for that are NOT placed on the publication deck at all.
ORPHAN_LEGENDS = [
 ("P", "Double ablation timestrip:", "Selected frames from a cell with two sisterless kinetochores."),
 ("P", "Two kinetochores on one chromosome timestrip:", "not leave any kinetochores with unresolved SAC signals."),
 ("P", "Frap timestrip:", "Laser photobleaching and recovery of a kinetochore."),
 ("P", "Frap fluorescence traces:", "over the seconds following attempted laser destruction."),
]

AB_TITLE_KEY = {"1": "Fig 1", "2": "Fig 2", "5": "Fig 3", "7": "Fig 4",
                "8": "Fig 5", "4": "Fig 6", "6": "Fig 7", "3": "Fig 8", "9": "Fig 9"}


def deck():
    rows = [l.rstrip("\n").split("\t") for l in io.open(GEOM, encoding="utf-8", errors="replace")]
    H = {c: i for i, c in enumerate(rows[0])}
    def g(r, c):
        i = H[c]; return r[i] if i < len(r) else ""
    placed, titles = collections.defaultdict(set), collections.defaultdict(list)
    for r in rows[1:]:
        if len(r) < 6: continue
        if g(r, "kind") == "PlacedItem":
            placed[g(r, "ab_centre")].add(re.sub(r"__piece\d+$", "", g(r, "name")))
        if g(r, "kind") == "TextFrame" and len(g(r, "name")) > 55:
            try: T = float(g(r, "T"))
            except Exception: T = -1e9
            titles[g(r, "ab_centre")].append((T, flat(g(r, "name"))))
    return placed, {k: sorted(v, reverse=True) for k, v in titles.items()}


def lookup(name):
    """Her entry for this panel: exact key, else the longest key that prefixes it (panel families)."""
    if name in PAIR: return PAIR[name], name
    cands = [k for k in PAIR if name.startswith(k)]
    if cands:
        k = max(cands, key=len); return PAIR[k], k
    return "UNKNOWN", None


def main():
    placed, titles = deck()
    L = ["# Figure legends, paired to what is actually on the deck — 2026-08-21", "",
         "**Every sentence is yours**, cut verbatim from `legends_pasted_20260821.txt`, the `Figure Legends`",
         "section of *Paper draft*, or `Results working document` by `dataops/assemble_figure_legends.py`;",
         "the build fails rather than emit anything it cannot find in one of them.",
         "",
         "**Paired by what the panel IS, not by figure number** — your numbering changed while the drafts were",
         "being written (Mad1 moved into Figure 1, the polar-join-plate figure moved into Figure 3, and the set",
         "renumbered 10 → 9), so a legend's old figure number is not evidence of where it belongs now.",
         "",
         "**Mine, and only outside your prose:** the artboard headings, the panel keys (the deck's own",
         "filenames), and this note.", "", "---", ""]

    unmatched, used = [], 0
    for ab in sorted(AB_TITLE_KEY, key=int):
        figs = sorted(placed.get(ab, []))
        tt = titles.get(ab, [])
        L.append(f"## {AB_TITLE_KEY[ab]} — artboard {ab}")
        if tt: L.append(f"\n*{tt[0][1]}*\n")
        if not figs:
            L.append("**No artwork placed on this board.**\n"); continue
        seen = set()
        for n in figs:
            ent, key = lookup(n)
            if isinstance(ent, str) and ent.startswith("SAME AS"):
                ent, key = PAIR[ent[len("SAME AS "):]], ent[len("SAME AS "):]
            if ent == "UNKNOWN":
                unmatched.append((ab, n)); L.append(f"- `{n}` — 🔴 **not in the pairing table**"); continue
            if ent is None:
                unmatched.append((ab, n)); L.append(f"- `{n}` — 🔴 **you have not written a legend for this**"); continue
            if key in seen:
                L.append(f"- `{n}` — *(same legend as above)*"); continue
            seen.add(key); used += 1
            L.append(f"- `{n}`\n\n  {cut(*ent)}\n")
        L.append("")

    L += ["---", "", "## Legends you wrote for panels that are NOT on the deck", "",
          "These have written legends but no placed figure, so either the panel still has to go on, or the",
          "legend should come out:", ""]
    for e in ORPHAN_LEGENDS:
        L.append(f"- **{e[1].rstrip(':')}** — {cut(*e)}")
    L += ["", "## Panels on the deck with no legend written yet", ""]
    if unmatched:
        for ab, n in unmatched:
            L.append(f"- artboard {ab} — `{n}`")
    else:
        L.append("- none")
    io.open(OUT, "w", encoding="utf-8").write("\n".join(L) + "\n")
    print(f"panels paired to your text : {used}")
    print(f"panels needing a legend    : {len(unmatched)}")
    print(f"legends with no panel      : {len(ORPHAN_LEGENDS)}")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    try:
        main()
    except Missing as e:
        sys.exit(f"REFUSING TO WRITE — a brick no longer matches her text verbatim:\n  {e}")
