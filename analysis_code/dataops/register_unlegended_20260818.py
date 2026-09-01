#!/usr/bin/env python3
"""Give the last placed-but-unregistered figures a provenance entry, so every figure on the five live
decks can carry a legend.

HER INSTRUCTION (2026-08-18): "resolve all legend items still on the five decks."
After the bullets pass, 19 placements had no legend because they had no PLOT_SETTINGS entry at all —
a placed figure with no entry is a defect (her standing rule), not a formatting problem.

Handled here (the two builders that OWN their panels were patched instead, which is the durable fix):
  * the 7 `__pieceN` files of the split nf9 timestrip  -> panels of that timestrip
  * the 3 AB5 excerpt crops                            -> registered with what they are
  * the FRAP timestrip placed on 0813supp              -> registered as an image panel
"""
import json, os, re, sys
sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625"); import lib

PS = "/Volumes/4 MB/ablation_plots/PLOT_SETTINGS.json"
reg = json.load(open(PS))
done = []

# ---- 1. the seven pieces of the split nf9 timestrip -------------------------------------------
parent = "nf9_3-sisterless__20260417_ptk2_eyfp_cdc20_ablation_18"
for i in range(1, 8):
    pid = f"{parent}__piece{i}"
    if reg.get(pid, {}).get("panel_of"): continue
    lib.register_panel(pid, parent,
                       caption=(f"Piece {i} of the 3-sisterless timestrip "
                                f"(20260417 ptk2 eyfp cdc20 ablation_18), split so the strip fits the board."),
                       settings={"panel_index": i, "split_reason": "long timestrip split into pieces"},
                       script=__file__)
    done.append(pid)

# ---- 2. the AB5 excerpt crops -------------------------------------------------------------------
EXCERPTS = {
 "AB5_EXCERPT_polar": "Excerpt from the artboard-5 timestrip: the kinetochore that stays polar.",
 "AB5_EXCERPT_hidden_in_plate": "Excerpt from the artboard-5 timestrip: the kinetochore hidden inside the plate.",
 "AB5_EXCERPT_1sisterless_11": "Excerpt from the artboard-5 timestrip: 1-sisterless cell, ablation_11.",
}
for pid, cap in EXCERPTS.items():
    if reg.get(pid, {}).get("caption"): continue
    lib.register_panel(pid, "", caption=cap,
                       settings={"kind": "image excerpt", "built_by": "custom_ab5_excerpts_20260817.py",
                                 "note": "a crop of an existing timestrip panel, not a separate measurement"},
                       script="custom_ab5_excerpts_20260817.py")
    done.append(pid)

# ---- 3. the FRAP timestrip on 0813supp ----------------------------------------------------------
pid = "20250711_double_ablation_18_frap0_aligned"
if not reg.get(pid, {}).get("caption"):
    lib.register_panel(pid, "", caption="FRAP timestrip — 20250711 double ablation_18, first FRAP event, aligned crop.",
                       settings={"kind": "image_panel", "batch": "20250711 double ablation_18",
                                 "built_by": "group_frap_timestrips.py",
                                 "note": "one FRAP sequence; the bleach marker is drawn on the bleached frame"},
                       script="group_frap_timestrips.py")
    done.append(pid)

print(f"registered {len(done)} figures:")
for d in done: print("   ", d)
