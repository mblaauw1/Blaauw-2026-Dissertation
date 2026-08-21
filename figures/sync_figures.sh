#!/bin/bash
# Routine post-feedback sync — rebuild the deck (pptx/pdf/html). Does NOT open Illustrator.
# The arranged + library .ai LINK to _ai_relink/pdf/*.pdf (and timestrip PNGs), and the plot scripts now
# write those editable PDFs directly from matplotlib (lib.apply_style savefig wrapper). So after you re-run
# any plot, its .ai figure is already updated on disk — Illustrator refreshes the linked art when you OPEN
# the .ai. No Adobe automation, no focus-stealing, no timeouts.
# ONLY when you add a BRAND-NEW plot (not yet placed on an artboard) run ./rebuild_ai_full.sh to place it.
set -e
R="/Volumes/4 MB/ablation_figures_20260625"; cd "$R"
echo "[deck] pptx / pdf / html…"; python3 deck.py >/dev/null && python3 deck_compact.py >/dev/null
echo "DONE — deck rebuilt. Open ablation_figures.ai / _arranged_UPDATED.ai to see refreshed linked figures (no Illustrator driving needed)."
