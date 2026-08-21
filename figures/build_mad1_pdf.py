#!/usr/bin/env python3
"""Assemble the SEPARATE Mad1 kinetochore-outline PDF (user 2026-07-27: Mad1 cells are their own
experiment and must not appear in the Cdc20 deck)."""
import os, fitz
PDF = "/Volumes/4 MB/ablation_figures_20260625/_ai_relink/pdf"
OUT = "/Volumes/4 MB/ablation_plots/kinetochore_MAD1_analysis_20260727.pdf"
ORDER = ["MAD1kt_cohort_composition", "MAD1kt_area_um2", "MAD1kt_perimeter_um", "MAD1kt_circularity",
         "MAD1kt_aspect_ratio", "MAD1kt_major_um", "MAD1kt_solidity",
         "MAD1kt_area_um2_time", "MAD1kt_aspect_ratio_time"]
doc = fitz.open()
page = doc.new_page(width=612, height=792)
page.insert_text((56, 90), "Mad1 kinetochore-outline analysis", fontsize=20, fontname="hebo")
page.insert_text((56, 118), "eYFP-Mad1 cells only - plotted separately from the eYFP-Cdc20 deck", fontsize=11)
page.insert_text((56, 140), "source: annotations/MAD1_KT_OUTLINE_TRACKS_20260727.csv   built by kt_mad1_plots.py", fontsize=8)
y = 180
n = 0
for i, b in enumerate(ORDER):
    p = f"{PDF}/{b}.pdf"
    if not os.path.exists(p):
        continue
    n += 1
    page.insert_text((70, y), f"{n}.  {b}", fontsize=10); y += 18
for b in ORDER:
    p = f"{PDF}/{b}.pdf"
    if not os.path.exists(p):
        print("  MISSING", b); continue
    src = fitz.open(p)
    doc.insert_pdf(src); src.close()
doc.save(OUT); doc.close()
print(f"wrote {OUT}: {n} figures")
