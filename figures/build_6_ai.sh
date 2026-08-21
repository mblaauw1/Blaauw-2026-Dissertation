#!/bin/bash
# Rebuild the SIX .ai deck files (organized, letter, pdf, pdf_letter, grouped, grouped_letter) + topical PDF
# from the CURRENT plot pdf-cache. SAFE: each BUILD_AI_*.jsx opens/saves/closes ONLY the deck doc it creates;
# this script NEVER runs "close every document" — so an open copy.ai (or any user doc) is left untouched.
# Scheduled one-shot at 14:00 via launchd (com.mblaauw.build6ai); unloads itself when done.
R="/Volumes/4 MB/ablation_figures_20260625"; P="/Volumes/4 MB/ablation_plots"
LOG="$R/_build_6_ai_2pm.log"
exec >>"$LOG" 2>&1
echo "================ build_6_ai started $(date) ================"
if [ ! -d "$R" ]; then echo "ABORT: $R not mounted"; exit 1; fi
cd "$R" || { echo "ABORT: cd failed"; exit 1; }
# 1) regenerate topical PDF + the 6 JSX (manifest may have changed since last build)
python3 build_topical_pdf.py && echo "topical PDF ok"
cp _ai_relink/reordered_manifest_TOPICAL.json _ai_relink/reordered_manifest.json
KT_AI_MODE=pdf KT_AI_OUT="$P/ablation_figures_organized.ai"        KT_AI_JSX="$R/BUILD_AI_ORGANIZED.jsx"    python3 _ai_build/gen_library_ai.py
KT_AI_LETTER=1 KT_AI_MODE=pdf KT_AI_OUT="$P/ablation_figures_organized_letter.ai" KT_AI_JSX="$R/BUILD_AI_LETTER.jsx" python3 _ai_build/gen_library_ai.py
KT_AI_OUT="$P/ablation_figures_grouped.ai"         KT_AI_JSX="$R/BUILD_AI_GROUPED.jsx"        python3 _ai_build/gen_grouped_ai.py
KT_AI_LETTER=1 KT_AI_OUT="$P/ablation_figures_grouped_letter.ai" KT_AI_JSX="$R/BUILD_AI_GROUPED_LETTER.jsx" python3 _ai_build/gen_grouped_ai.py
cp _ai_relink/reordered_manifest_V1CURRENT.json _ai_relink/reordered_manifest.json
KT_AI_MODE=pdf KT_AI_OUT="$P/ablation_figures_pdf.ai"             KT_AI_JSX="$R/BUILD_AI_PDF.jsx"           python3 _ai_build/gen_library_ai.py
KT_AI_LETTER=1 KT_AI_MODE=pdf KT_AI_OUT="$P/ablation_figures_pdf_letter.ai" KT_AI_JSX="$R/BUILD_AI_PDF_LETTER.jsx" python3 _ai_build/gen_library_ai.py
cp _ai_relink/reordered_manifest_TOPICAL.json _ai_relink/reordered_manifest.json
echo "JSX regenerated $(date +%H:%M:%S)"
# 2) build each deck (JSX self-closes its doc; copy.ai untouched)
for j in BUILD_AI_ORGANIZED BUILD_AI_LETTER BUILD_AI_PDF BUILD_AI_PDF_LETTER BUILD_AI_GROUPED BUILD_AI_GROUPED_LETTER; do
  echo "--- building $j $(date +%H:%M:%S) ---"
  osascript -e 'with timeout of 1500 seconds' -e "tell application \"Adobe Illustrator\" to do javascript (POSIX file \"$R/$j.jsx\")" -e 'end timeout'
done
echo "================ build_6_ai DONE $(date) ================"
# one-shot: remove the scheduled agent so it does not repeat daily
launchctl unload "$HOME/Library/LaunchAgents/com.mblaauw.build6ai.plist" 2>/dev/null
rm -f "$HOME/Library/LaunchAgents/com.mblaauw.build6ai.plist"
