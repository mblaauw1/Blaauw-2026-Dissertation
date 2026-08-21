#!/bin/bash
# One-command figure sync: rebuild deck + BOTH Illustrator files from the CURRENT plots.
# Run this AFTER making/regenerating plots. Requires Adobe Illustrator running + Automation permission.
#   - ablation_figures.ai (library): fully regenerated -> new plots auto-included
#   - ablation_figures_arranged_UPDATED_*.ai: figures re-placed (linked PDF) from your arranged layout
set -e
R="/Volumes/4 MB/ablation_figures_20260625"; cd "$R"
echo "[1/4] deck (pptx/pdf/html)…";        python3 deck.py >/dev/null && python3 deck_compact.py >/dev/null
# [2/4] NON-DESTRUCTIVE PDF-cache refresh. The plot builders already keep _ai_relink/pdf/*.pdf current
# (lib.py savefig writes each figure's editable PDF straight there), so a blanket `rm` is unnecessary AND
# dangerous: if step 3/4 fails under `set -e` the cache stays deleted and every linked-PDF .ai breaks
# (this bit us 2026-07-14 — 180 PDFs wiped). Move to a timestamped backup instead of deleting, so it's
# always recoverable. Only pdf-MODE builds repopulate from SVGs; native mode doesn't use this dir at all.
BK="_ai_relink/pdf_backup_$(date +%Y%m%d_%H%M%S)"
echo "[2/4] backing up PDF cache -> $BK (non-destructive)…"; mkdir -p "$BK" && (ls _ai_relink/pdf/*.pdf >/dev/null 2>&1 && cp -p _ai_relink/pdf/*.pdf "$BK"/ || true)
echo "[3/4] library ablation_figures.ai…"; python3 _ai_build/gen_library_ai.py >/dev/null
# gen_library_ai.py emits the JSX to $R/BUILD_AI_LIBRARY.jsx (+ a copy at _ai_build/ai_library.jsx),
# NOT /tmp/ai_library.jsx (the old path silently 404'd -> Error 1252). Point at the real file.
osascript -e 'with timeout of 1500 seconds' -e 'tell application "Adobe Illustrator" to do javascript (POSIX file "'"$R"'/BUILD_AI_LIBRARY.jsx")' -e 'end timeout'
echo "[4/4] arranged …_UPDATED.ai…"
cp "/Volumes/4 MB/ablation_plots/_superseded_decks/ablation_figures_arranged.ai" "/Volumes/4 MB/ablation_plots/_superseded_decks/ablation_figures_arranged_UPDATED_20260629.ai"
osascript -e 'with timeout of 1500 seconds' -e 'tell application "Adobe Illustrator" to do javascript (POSIX file "'"$R"'/_ai_relink/ai_swap_runner_oncopy_20260629.jsx")' -e 'end timeout'
echo "DONE — ablation_figures.ai (library) + arranged_UPDATED refreshed."
