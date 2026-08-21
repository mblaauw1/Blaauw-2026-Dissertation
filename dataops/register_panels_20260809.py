#!/usr/bin/env python3
"""Register every split panel as its own plot, with its own caption and legend bullets.

Follows `split_panels_20260809.py`. Each `<parent>__pN.pdf` becomes a first-class plot_id in
PLOT_SETTINGS so it can be placed on a deck and carry its own legend, exactly like any other figure.

DATA PROVENANCE. A panel is one view of its parent's dataset, so it inherits the parent's data CSV and
source lineage rather than getting a fabricated one — the parent's `record_plot` row already holds the rows
those panels were drawn from. The panel entry records `panel_of` and `panel_index` so the relationship is
explicit and a later audit can always get back to the parent.

CAPTIONS. A panel's caption is the parent's caption plus which panel it is. Where the parent's caption
carried per-metric statistics (they are pipe-separated by the builders here), the matching clause is
promoted to the front of that panel's caption so the numbers under a panel describe THAT panel.
"""
import csv, json, os, re, glob, datetime

FIG = "/Volumes/4 MB/ablation_figures_20260625"
PANELS = os.path.join(FIG, "panels")
RELINK = os.path.join(FIG, "_ai_relink", "pdf")
PS_PATH = "/Volumes/4 MB/ablation_plots/PLOT_SETTINGS.json"

ps = json.load(open(PS_PATH))
pngs = sorted(glob.glob(os.path.join(PANELS, "*__p*.png")))
print(f"panel images found: {len(pngs)}")

by_parent = {}
for p in pngs:
    stem = os.path.splitext(os.path.basename(p))[0]
    m = re.match(r"^(.*)__p(\d+)$", stem)
    if not m:
        continue
    by_parent.setdefault(m.group(1), []).append((int(m.group(2)), stem))
for k in by_parent:
    by_parent[k].sort()
print(f"parents represented: {len(by_parent)}")

made, skipped = 0, 0
for parent, items in sorted(by_parent.items()):
    pe = ps.get(parent)
    if not isinstance(pe, dict):
        skipped += len(items)
        continue
    cap = (pe.get("caption") or "").strip()
    # builders here separate per-metric findings with " | " -- give each panel its own clause when the
    # counts line up, so a panel's legend is about that panel and not the whole grid
    clauses = [c.strip() for c in cap.split(" | ") if c.strip()]
    head = clauses[0] if clauses else cap
    tail = clauses[1:] if len(clauses) > 1 else []
    for idx, stem in items:
        if not os.path.exists(os.path.join(RELINK, stem + ".pdf")):
            skipped += 1
            continue
        mine = ""
        if tail and len(tail) == len(items):
            mine = tail[idx - 1] + ". "
        ps[stem] = {
            "caption": f"{mine}Panel {idx} of {len(items)} from {parent}. {head}".strip(),
            "settings": dict(pe.get("settings") or {}, panel_of=parent, panel_index=idx,
                             n_panels=len(items)),
            "data": pe.get("data"),
            "code": pe.get("code"),
            "source": pe.get("source"),
            "n_rows": pe.get("n_rows"),
            "panel_of": parent,
            "panel_index": idx,
            "split_from_multipanel": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        }
        if isinstance(pe.get("plot_number"), int):
            pass          # deliberately NOT inherited: a panel is a new figure and needs its own number
        made += 1

tmp = PS_PATH + ".tmp"
json.dump(ps, open(tmp, "w"), indent=1)
os.replace(tmp, PS_PATH)
print(f"registered {made} panels   skipped {skipped}")
json.dump({k: [s for _, s in v] for k, v in by_parent.items()},
          open("/Volumes/4 MB/_claude_tmp/panel_map.json", "w"), indent=1)
print("panel map -> /Volumes/4 MB/_claude_tmp/panel_map.json")
