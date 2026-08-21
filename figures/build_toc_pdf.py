#!/usr/bin/env python3
"""Assemble the full kinetochore-analysis PDF organized into big sections, with a clickable
table-of-contents front page (internal GoTo links) + PDF outline bookmarks."""
import os, json, glob, fitz

PDF = "/Volumes/4 MB/ablation_figures_20260625/_ai_relink/pdf"
PS = json.load(open("/Volumes/4 MB/ablation_plots/PLOT_SETTINGS.json"))
OUT = "/Volumes/4 MB/ablation_plots/kinetochore_FULL_analysis_20260723.pdf"


def num(b):
    return PS.get(b, {}).get("plot_number", "")


def title(b):
    cap = (PS.get(b, {}).get("caption") or "").strip()
    if cap:
        return cap[:70]
    return b.replace("G5shape_", "").replace("G6trk_", "").replace("G6", "").replace("_", " ")


# ---- SECTIONS (big, understandable chunks). Each: (name, [figure basenames in order]) ----
SEC = [
    ("A · Kinetochore shape by state", ["G5shape_area", "G5shape_perimeter", "G5shape_circularity",
        "G5shape_solidity", "G5shape_aspect", "G5shape_elongation", "G5shape_major", "G5shape_aspect_ecdf",
        "G5shape_area_ecdf", "G5shape_area_vs_circularity", "G5shape_major_vs_minor", "G5shape_aspect_vs_solidity",
        "G5shape_maxaspect_by_class", "G5shape_fracstretched_by_class", "G5shape_polar_vs_paired_area",
        "G5shape_polar_vs_paired_aspect", "G5shape_lagging_stretch_time", "G5shape_cytosol_relax_accuracy"]),
    ("B · Shape / position / motion by state (tracked)", ["G6trk_perimeter", "G6trk_area", "G6trk_dist_to_plate",
        "G6trk_stretch_radial", "G6trk_anisotropy", "G6trk_vase", "G6trk_reflection_asym", "G6trk_speed_by_phase",
        "G6trk_postanaphase_speed", "G6trk_distance_total", "G6trk_distance_per20s", "G6trk_fractures",
        "G6trk_toward_vs_away"]),
    ("C · Distributions split by mitotic phase", sorted(os.path.basename(f)[:-4] for f in glob.glob(PDF + "/G6ph_*.pdf"))),
    ("D · Over time, aligned to metaphase onset", sorted(os.path.basename(f)[:-4] for f in glob.glob(PDF + "/G6time_*.pdf"))),
    ("E · Polar KT over time, coloured by phase (+ fits)", sorted(os.path.basename(f)[:-4] for f in glob.glob(PDF + "/G6ppt_*.pdf"))),
    ("F · Polar KT: time × distance-to-plate × area", sorted(os.path.basename(f)[:-4] for f in glob.glob(PDF + "/G6poly_*.pdf"))),
    ("G · Shape vs anaphase & chromosome length", ["G6trk_circ_vs_ttana", "G6trk_aspect_vs_ttana", "G6trk_area_vs_ttana",
        "G6trk_circ_vs_time", "G6trk_aspect_vs_time", "G6trk_area_vs_time", "G6trk_dist_vs_time", "G6trk_speed_vs_time",
        "G6trk_chromolen_vs_speed", "G6trk_chromolen_vs_circ", "G6trk_chromolen_vs_aspect"]),
    ("H · Chromosome geometry relative to the plate", ["G6trk_chromo_orient", "G6trk_chromo_farend",
        "G6trk_chromo_nearend", "G6trk_chromo_length"]),
    ("I · Sister kinetochores & k–k distance", sorted(os.path.basename(f)[:-4] for f in glob.glob(PDF + "/G6sis_*.pdf"))),
    # Force/tension: each full-mitosis figure is immediately followed by its METAPHASE-ONLY twin
    # (G6tenM_*), so the pair reads together (user 2026-07-27).
    ("J · Force / tension on the polar kinetochore (each followed by its metaphase-only twin)",
     [b for base in sorted(os.path.basename(f)[:-4] for f in glob.glob(PDF + "/G6ten_*.pdf")
                           if not os.path.basename(f).startswith("G6tenM_"))
        for b in (base, "G6tenM_" + base[len("G6ten_"):])]),
    ("K · Whole-cell outline relationships", sorted(os.path.basename(f)[:-4] for f in glob.glob(PDF + "/G6cell_*.pdf"))),
    ("L · Stretch oscillation & predictive-of-anaphase", sorted(os.path.basename(f)[:-4] for f in glob.glob(PDF + "/G6osc_*.pdf")) + sorted(os.path.basename(f)[:-4] for f in glob.glob(PDF + "/G6pred_*.pdf"))),
]

# NEW 2026-07-27 (her request): the metaphase-onset -> anaphase re-cuts of section D, and the
# question-set figures, each get their own named section instead of falling into "Other".
SEC.append(("M · Metaphase-onset to anaphase only (no lagging, refit, outliers dropped)",
            sorted(os.path.basename(f)[:-4] for f in glob.glob(PDF + "/G6timeMA_*.pdf"))))
SEC.append(("N · Question set (2026-07-27)",
            sorted(os.path.basename(f)[:-4] for f in glob.glob(PDF + "/QNEW_*.pdf"))))

# de-dup: any figure PDF not placed in a section -> "Other"
placed = {b for _, figs in SEC for b in figs}
allpdf = {os.path.basename(f)[:-4] for f in glob.glob(PDF + "/G6*.pdf") if os.path.basename(f).startswith(("G6",))}
allpdf |= {os.path.basename(f)[:-4] for f in glob.glob(PDF + "/G5shape_*.pdf")}
misc = sorted(b for b in allpdf if b not in placed)
if misc:
    SEC.append(("Z · Other", misc))

# keep only figures whose PDF exists, in order
SEC = [(name, [b for b in figs if os.path.isfile(f"{PDF}/{b}.pdf")]) for name, figs in SEC]
SEC = [(n, f) for n, f in SEC if f]

# ---- layout the TOC (how many pages) ----
PW, PH = 792, 612           # US-letter landscape
MARGIN, COLW, COLS = 40, 360, 2
LINE = 15
top = 78                    # fitz y grows DOWNWARD: start near the top, increase y going down
usable_lines = int((PH - 40 - top) / LINE)

# flatten into entries with section markers
entries = []
for name, figs in SEC:
    entries.append(("SEC", name))
    for b in figs:
        entries.append(("FIG", b))
# split entries into columns/pages
per_col = usable_lines
per_page = per_col * COLS
n_toc = max(1, (len(entries) + per_page - 1) // per_page)

# ---- build the figures doc first to know page numbers ----
fig_pages = {}   # basename -> page index (0-based) in the FINAL doc (after toc pages)
doc = fitz.open()
for _ in range(n_toc):
    doc.new_page(width=PW, height=PH)
for name, figs in SEC:
    for b in figs:
        fig_pages[b] = doc.page_count
        doc.insert_pdf(fitz.open(f"{PDF}/{b}.pdf"))

# ---- draw the TOC pages + links ----
BLUE = (0.15, 0.35, 0.75)
DARK = (0.1, 0.1, 0.1)
idx = 0
toc_bookmarks = []   # [level, title, 1-indexed page]
for tp in range(n_toc):
    page = doc[tp]
    if tp == 0:
        page.insert_text((MARGIN, 40), "Kinetochore analysis — contents", fontsize=20, color=DARK, fontname="hebo")
        page.insert_text((MARGIN, 58), "2026-07-23 · click any line to jump to that plot", fontsize=9, color=(0.4, 0.4, 0.4))
    for col in range(COLS):
        x = MARGIN + col * (COLW + 20)
        y = top
        placed_here = 0
        while idx < len(entries) and placed_here < per_col:
            kind, val = entries[idx]
            if kind == "SEC":
                if placed_here > per_col - 3:   # don't strand a header at the bottom of a column
                    break
                y += 4
                page.insert_text((x, y), val, fontsize=11, color=DARK, fontname="hebo")
                toc_bookmarks.append([1, val, tp + 1])
                y += LINE + 4; placed_here += 2
            else:
                b = val; pg = fig_pages[b]
                label = f"   {num(b)}. {title(b)}" if num(b) != "" else f"   {title(b)}"
                page.insert_text((x, y), label, fontsize=8.5, color=BLUE)
                rect = fitz.Rect(x, y - LINE + 3, x + COLW, y + 3)
                page.insert_link({"kind": fitz.LINK_GOTO, "from": rect, "page": pg, "to": fitz.Point(0, 40)})
                toc_bookmarks.append([2, f"{num(b)}. {title(b)}"[:60], pg + 1])
                y += LINE; placed_here += 1
            idx += 1

# ---- outline bookmarks (sidebar) ----
doc.set_toc(toc_bookmarks)
doc.save(OUT, deflate=True, garbage=3)
print(f"wrote {OUT}: {doc.page_count} pages ({n_toc} TOC), {sum(len(f) for _,f in SEC)} figures, {len(SEC)} sections")
for n, f in SEC:
    print(f"  {n}: {len(f)}")
