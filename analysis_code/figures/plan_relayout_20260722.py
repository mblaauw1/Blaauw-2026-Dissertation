#!/usr/bin/env python3
"""Build a full re-layout plan for copy.ai.

Fixes, in one deterministic pass:
  #2  every figure caption gets its assigned plot number as a prefix
  #4  a caption is created from the figure, so there are no captions without a plot
  #5  each caption sits directly above its own figure (one caption per figure, no duplicates)
  #7  everything lands on an artboard
  #12 artboards are shelf-packed in group order, no overlaps

Reads  _scratch/copyai_after_edit1.json   (current state dump)
Writes _scratch/copyai_relayout.json      (the plan the JSX executes)
       ablation_plots/PLOT_NUMBERS_20260722.csv (the number assigned to each figure)
"""
import json, re, csv, os

SC = "/Volumes/4 MB/_scratch"
d = json.load(open(f"{SC}/copyai_after_edit1.json"))
items, texts, paths, abs_ = d['items'], d['texts'], d['paths'], d['artboards']

def norm(s): return re.sub(r'[^a-z0-9]', '', s.lower())

# ---------- source labels ([data: ...]) ----------
try:
    raw = json.load(open("/Volumes/4 MB/ablation_figures_20260625/_ai_relink/figure_source_labels.json"))
except Exception:
    raw = {}
SRC = {}
for k, v in raw.items():
    SRC[norm(os.path.basename(k).rsplit('.', 1)[0])] = v
# also harvest from the existing captions (they already carry a correct tag)
for t in texts:
    if '[data:' not in t['txt']:
        continue
    lbl, tag = t['txt'].split('[data:', 1)
    lbl = re.sub(r'^[A-Z]?\d+\.\s*', '', lbl.strip())
    tag = tag.split(']')[0].strip()
    SRC.setdefault(norm(lbl), tag)

# ---------- classify texts ----------
base_norm = {norm(i['base']) for i in items}
HEADERS, KEEP, DROP = [], [], []
for t in texts:
    s = t['txt'].strip()
    if t['layer'] == 'RETIRED_MARKS':
        KEEP.append(t); continue
    if not s:
        DROP.append(t); continue
    lbl = re.sub(r'^[A-Z]?\d+\.\s*', '', s.split('[data:')[0].strip())
    n = norm(lbl)
    if n in base_norm or any(n and k.startswith(n[:28]) for k in base_norm):
        DROP.append(t)                      # a figure caption -> rebuilt
    elif re.match(r'^(G\d+[:— ]|Custom analyses|Chromosome length)', s):
        HEADERS.append(t)                   # artboard title
    else:
        KEEP.append(t)                      # a real annotation

# ---------- per-artboard item order ----------
per = {}
for i in items:
    per.setdefault(i['ab'], []).append(i)
for a in per:
    per[a].sort(key=lambda i: (-round((i['b'][1] + i['b'][3]) / 2 / 120), i['b'][0]))

# ---------- layout constants ----------
MARGIN, GAPX, GAPY, CAPH = 30, 24, 34, 15
MAXW, MAXH = 900.0, 300.0
TARGETW = 3010.0

def fit(b):
    w, h = b[2] - b[0], b[1] - b[3]
    s = min(MAXW / w, MAXH / h, 1.0)
    if h * s < 150 and w * s < MAXW:        # don't shrink small plots further
        s = min(MAXW / w, 300.0 / h)
    return w * s, h * s

plan_items, plan_caps, plan_abs = [], [], []
numbers = {}
counter = 0
ORDER = sorted(per.keys())

for a in ORDER:
    its = per[a]
    # shelf-pack
    rows, cur, curw, rowh = [], [], 0.0, 0.0
    for i in its:
        w, h = fit(i['b'])
        if cur and curw + w + GAPX > TARGETW:
            rows.append((cur, rowh)); cur, curw, rowh = [], 0.0, 0.0
        cur.append((i, w, h)); curw += w + GAPX; rowh = max(rowh, h)
    if cur:
        rows.append((cur, rowh))
    width = MARGIN * 2 + (max((sum(w + GAPX for _, w, _ in r) - GAPX) for r, _ in rows) if rows else 400)
    width = max(width, 500)
    height = MARGIN * 2 + 46 + sum(rh + CAPH + GAPY for _, rh in rows)
    plan_abs.append({"i": a, "w": width, "h": height, "name": abs_[a]['name'] if a >= 0 else "Recovered"})

# global shelf-pack of artboards
X0, Y0, ABGAP, MAXROWW = 100.0, 8508.0, 260.0, 15200.0
x, y, rowh = X0, Y0, 0.0
for pa in plan_abs:
    if x > X0 and x + pa['w'] > X0 + MAXROWW:
        x = X0; y -= rowh + ABGAP; rowh = 0.0
    pa['rect'] = [x, y, x + pa['w'], y - pa['h']]
    x += pa['w'] + ABGAP
    rowh = max(rowh, pa['h'])

# place content inside each artboard
for pa in plan_abs:
    a = pa['i']; r = pa['rect']
    its = per[a]
    rows, cur, curw, rowh = [], [], 0.0, 0.0
    for i in its:
        w, h = fit(i['b'])
        if cur and curw + w + GAPX > TARGETW:
            rows.append((cur, rowh)); cur, curw, rowh = [], 0.0, 0.0
        cur.append((i, w, h)); curw += w + GAPX; rowh = max(rowh, h)
    if cur:
        rows.append((cur, rowh))
    cy = r[1] - MARGIN - 46
    for row, rh in rows:
        cx = r[0] + MARGIN
        for i, w, h in row:
            counter += 1
            numbers[i['base']] = counter
            tag = SRC.get(norm(i['base']), '')
            cap = f"{counter}. {i['base']}" + (f"   [data: {tag}]" if tag else "")
            plan_caps.append({"txt": cap, "pos": [cx, cy]})
            plan_items.append({"file": i['file'], "ob": i['b'],
                               "nb": [cx, cy - CAPH, cx + w, cy - CAPH - h], "base": i['base']})
            cx += w + GAPX
        cy -= rh + CAPH + GAPY

# artboard headers move to their artboard's top-left
plan_head = []
for pa in plan_abs:
    hs = [t for t in HEADERS if t['ab'] == pa['i']]
    for k, t in enumerate(hs):
        plan_head.append({"ob": t['b'], "pos": [pa['rect'][0] + MARGIN, pa['rect'][1] - MARGIN + 4 - k * 18]})

# other kept annotations: shift with their artboard
plan_keep = []
old = {a['i']: a['rect'] for a in abs_}
for t in KEEP:
    if t['ab'] not in old:
        continue
    pa = next((p for p in plan_abs if p['i'] == t['ab']), None)
    if not pa:
        continue
    o = old[t['ab']]
    plan_keep.append({"ob": t['b'],
                      "pos": [pa['rect'][0] + (t['b'][0] - o[0]), pa['rect'][1] + (t['b'][1] - o[1])]})

# SIGHILITE + REVIVED boxes -> re-anchored to the figure's new bounds
newb = {p['base']: p['nb'] for p in plan_items}
plan_box = []
for p in paths:
    m = re.match(r'^(SIGHILITE|REVIVED)\s+(.*)$', p['name'] or '')
    if not m:
        continue
    nb = newb.get(m.group(2))
    plan_box.append({"name": p['name'], "ob": p['b'],
                     "nb": ([nb[0] - 6, nb[1] + 6, nb[2] + 6, nb[3] - 6] if nb else None)})

json.dump({"artboards": plan_abs, "items": plan_items, "caps": plan_caps,
           "drop_texts": [{"ob": t['b'], "txt": t['txt'][:40]} for t in DROP],
           "head": plan_head, "keep": plan_keep, "boxes": plan_box},
          open(f"{SC}/copyai_relayout.json", "w"), indent=0)

with open("/Volumes/4 MB/ablation_plots/PLOT_NUMBERS_20260722.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["plot_number", "figure"])
    for k, v in sorted(numbers.items(), key=lambda kv: kv[1]):
        w.writerow([v, k])

print("artboards", len(plan_abs), "items", len(plan_items), "caps", len(plan_caps),
      "drop_texts", len(DROP), "headers", len(plan_head), "keep", len(plan_keep),
      "boxes", len(plan_box), "unanchored_boxes", sum(1 for b in plan_box if not b['nb']))
ext = [c for pa in plan_abs for c in pa['rect']]
print("extent x", min(ext[0::4] + ext[2::4]), max(ext[0::4] + ext[2::4]),
      "y", min(ext[1::4] + ext[3::4]), max(ext[1::4] + ext[3::4]))
print("captions missing a [data:] tag:", sum(1 for c in plan_caps if '[data:' not in c['txt']))
