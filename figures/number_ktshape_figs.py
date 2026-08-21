#!/usr/bin/env python3
"""Assign deck plot numbers 388-404 to the 17 kinetochore-shape figures, mirror into PLOT_SETTINGS +
PLOT_NUMBERS, and emit a caption-replacement map (prose -> the deck-standard '<#>. <base>   [data: ...]')."""
import json, csv, os

PS = "/Volumes/4 MB/ablation_plots/PLOT_SETTINGS.json"
PN = "/Volumes/4 MB/ablation_plots/PLOT_NUMBERS_20260722.csv"
PLACE = "/Volumes/4 MB/_scratch/place_ktshape.json"

place = json.load(open(PLACE))
bases = [it["base"] for it in place["items"]]          # 17, in placement order
old_caps = [c["txt"] for c in place["caps"]]           # the prose captions currently on the deck

S = json.load(open(PS))
start = max((v.get("plot_number", 0) for v in S.values() if isinstance(v.get("plot_number"), int)), default=387)
assert start == 387, f"unexpected max plot_number {start}"

numbering = {}
for i, base in enumerate(bases):
    num = 388 + i
    numbering[base] = num
    if base in S:
        S[base]["plot_number"] = num

tmp = PS + ".tmp"
json.dump(S, open(tmp, "w"), indent=1); os.replace(tmp, PS)

# append to PLOT_NUMBERS csv (dedupe if rerun)
existing = list(csv.DictReader(open(PN)))
have = {r["figure"] for r in existing}
with open(PN, "a", newline="") as f:
    w = csv.writer(f)
    for base, num in numbering.items():
        if base not in have:
            w.writerow([num, base])

# caption replacement map: old prose -> deck-standard caption
repl = {}
for base, old in zip(bases, old_caps):
    repl[old] = f"{numbering[base]}. {base}   [data: manual annotations]"
json.dump({"repl": repl}, open("/Volumes/4 MB/_scratch/ktshape_caption_fix.json", "w"), indent=1)

print("assigned:", numbering)
print(f"PLOT_SETTINGS + PLOT_NUMBERS updated; {len(repl)} caption replacements staged")
