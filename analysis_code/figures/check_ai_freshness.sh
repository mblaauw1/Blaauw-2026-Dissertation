#!/bin/zsh
# check_ai_freshness.sh — verify every figure linked in the .ai (BOTH .pdf and .png links) is current.
# HABIT (2026-07-10, user): the .ai links figures as BOTH _ai_relink/pdf/*.pdf AND direct group*/*.png.
# A PDF-only sweep misses the PNG-linked timestrips/examples. Always check both.
#
# Usage: zsh check_ai_freshness.sh [/path/to/file.ai]
# Prints: (1) missing links, (2) links older than the master/annotations (= CANDIDATE stale, needs content check).
# A figure "older than master" is only a CANDIDATE — confirm by either:
#   - cross-referencing the batch it shows against the changed-batch set (pinned examples to unchanged batches = clear), or
#   - rebuild-and-diff its builder (md5 before/after).
set -e
AI="${1:-/Volumes/4 MB/ablation_plots/_superseded_decks/ablation_figures_pdf.ai}"
MASTER="/Volumes/4 MB/ABLATION_MASTER.csv"
ANN="/Volumes/4 MB/annotations/kt_points.csv"
me=$(stat -c '%Y' "$MASTER"); ae=$(stat -c '%Y' "$ANN")
cut=$(( me>ae ? me : ae ))   # newest input
echo "AI: $AI"
echo "newest input (master/annotations): $(date -d @$cut '+%Y-%m-%d %H:%M')"
strings "$AI" | grep -oE 'stRef:filePath="[^"]+\.(pdf|png)"' | sed 's/stRef:filePath="//;s/"$//' | sort -u > /tmp/ai_all_links.txt
npdf=$(grep -c '\.pdf"\?$' /tmp/ai_all_links.txt || true); npng=$(grep -c '\.png"\?$' /tmp/ai_all_links.txt || true)
echo "linked figures: $(wc -l < /tmp/ai_all_links.txt) total  (pdf $npdf / png $npng)"
echo "--- MISSING on disk ---"; miss=0
while IFS= read -r p; do [ -f "$p" ] || { echo "  MISSING: $p"; miss=$((miss+1)); }; done < /tmp/ai_all_links.txt
echo "missing: $miss"
echo "--- OLDER THAN NEWEST INPUT (candidate stale — verify content) ---"; old=0
while IFS= read -r p; do
  [ -f "$p" ] || continue
  pe=$(stat -c '%Y' "$p")
  if [ "$pe" -lt "$cut" ]; then echo "  $(date -d @$pe '+%m-%d %H:%M')  $(basename "$p")"; old=$((old+1)); fi
done < /tmp/ai_all_links.txt
echo "candidate-stale (older than input): $old  — confirm via pinned/changed-batch cross-ref or rebuild-diff"
