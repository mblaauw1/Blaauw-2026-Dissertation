#!/usr/bin/env python3
"""verify_deck_complete.py -- answer "is anything missing from copy.ai?" with a check, not a memory.

Her standing worry (2026-07-22): "plots are being dropped (generated during one edit cycle but not the next
because they were forgotten), accidentally stacked on top of one another, or I tell you to generate a plot and
it never actually lands in the file."  This makes that checkable in one command.

It reads the LAST full dump of copy.ai (`_scratch/copyai_after_relayout.json`, refreshed by
`ablation_figures_20260625/DUMP_FULL_20260722b.jsx`) and reports:

  1. registered but NOT placed      -- a figure exists in PLOT_SETTINGS but is on no artboard
  2. placed but NOT registered      -- a figure on the deck with no provenance entry
  3. broken links                   -- a placement whose linked file is gone
  4. exact stacks                   -- two placements of the same figure at the same coordinates
  5. off-artboard items             -- placed art sitting outside every artboard
  6. figures with a rendered file but no placement at all -- built and then forgotten
  7. captions without a figure / figures without a caption

Usage:  python3 verify_deck_complete.py [path/to/dump.json]
Refresh the dump first if the deck has changed since:
  osascript -e 'with timeout of 1800 seconds
  tell application "Adobe Illustrator" to do javascript (POSIX file
  "/Volumes/4 MB/ablation_figures_20260625/DUMP_FULL_20260722b.jsx")
  end timeout'
"""
import json, os, re, sys, glob
from collections import Counter, defaultdict

ROOT = "/Volumes/4 MB"
DUMP = sys.argv[1] if len(sys.argv) > 1 else f"{ROOT}/_scratch/copyai_after_relayout.json"
S = json.load(open(f"{ROOT}/ablation_plots/PLOT_SETTINGS.json"))
d = json.load(open(DUMP))
items, texts = d["items"], d["texts"]
placed = [i["base"] for i in items]
pset = set(placed)
bad = 0


def head(n, msg):
    global bad
    print(f"\n{'OK   ' if n == 0 else 'CHECK'} [{msg}] {n}")
    if n:
        bad += 1


# 1 / 2
notplaced = sorted(k for k, v in S.items()
                   if k not in pset and not v.get("retired") and not v.get("data_record_only"))
head(len(notplaced), "registered but not placed")
for k in notplaced:
    print("      ", k)
notreg = sorted(b for b in pset if b not in S and b != "(nofile)")
head(len(notreg), "placed but not registered")
for k in notreg:
    print("      ", k)

# 3
broken = [i for i in items if i.get("missing")]
head(len(broken), "broken links")
for i in broken:
    print("      ", i["base"] or "(no file)", i["b"])

# 4
pos = defaultdict(list)
for i in items:
    pos[(i["base"], tuple(round(x, 1) for x in i["b"]))].append(i)
stacks = [k for k, v in pos.items() if len(v) > 1]
head(len(stacks), "exact stacked duplicates")
for k in stacks:
    print("      ", k[0], k[1])

# 5
off = [i for i in items if i["ab"] == -1]
head(len(off), "items off every artboard")
for i in off:
    print("      ", i["base"], i["b"])

# 6 -- rendered but never placed anywhere
pdfs = {os.path.basename(p)[:-4] for p in glob.glob(f"{ROOT}/ablation_figures_20260625/_ai_relink/pdf/*.pdf")
        if not os.path.basename(p).startswith("._")}
# per-batch timestrips / example panels carry a yyyymmdd in the name and are deliberately not deck
# figures -- only an unplaced render that looks like a FIGURE is worth flagging.
forgotten = sorted(p for p in pdfs
                   if p not in pset and not (S.get(p) or {}).get("retired")
                   and not re.search(r"20\d{6}", p))
head(len(forgotten), "figure-shaped renders never placed (per-batch strips excluded)")
for k in forgotten[:40]:
    print("      ", k)

# 7 -- caption <-> figure pairing
caps = [t for t in texts if re.match(r"^\d+\.\s", t["txt"])]
def norm(s): return re.sub(r"[^a-z0-9]", "", s.lower())
byname = {norm(i["base"]): i for i in items}
orphan_caps = [t for t in caps
               if norm(re.sub(r"^\d+\.\s*", "", t["txt"].split("[data:")[0]).strip()) not in byname]
head(len(orphan_caps), "numbered captions with no matching figure")
for t in orphan_caps[:20]:
    print("      ", t["txt"][:70])
capnames = {norm(re.sub(r"^\d+\.\s*", "", t["txt"].split("[data:")[0]).strip()) for t in caps}
nocap = sorted({i["base"] for i in items if norm(i["base"]) not in capnames})
head(len(nocap), "figures with no numbered caption")
for k in nocap[:20]:
    print("      ", k)

print(f"\n{'-'*70}\ndeck: {len(items)} placements · {len(pset)} distinct figures · "
      f"{len(d['artboards'])} artboards · {len(caps)} numbered captions")
print(f"dump: {DUMP}")
print("RESULT:", "clean" if bad == 0 else f"{bad} check(s) need attention")
sys.exit(0)
