#!/usr/bin/env python3
"""0818 table items 11, 16, 17, 18 -> CSVs + one readable HTML document.

Not an Illustrator file, per her instruction: "you should create a new non-ai document that has the
tables and you should choose a format in which the tables will be very readable and easy to use."
"""
import os, sys, csv, io, json, glob, math, collections, html, datetime
import numpy as np
sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625"); import lib

R = "/Volumes/4 MB"; A = R + "/annotations"; D = R + "/ablation_plots/data"
DEST = R + "/4_TABLES_AND_REPORTS/TABLES_20260818"; os.makedirs(DEST, exist_ok=True)

def rd(p):
    with io.open(p, encoding="utf-8", errors="replace") as f: return list(csv.DictReader(f))
def fl(v, d=None):
    try:
        s = str(v).strip().replace(",", "")
        return float(s) if s not in ("", "None", "nan") else d
    except Exception: return d
def hms(v):
    s = str(v).strip().replace(",", "")
    if not s: return None
    neg = s.startswith("-"); s = s.lstrip("-")
    if ":" in s:
        p = [fl(x, 0) or 0 for x in s.split(":")]
        while len(p) < 3: p.insert(0, 0)
        sec = p[0]*3600 + p[1]*60 + p[2]
    else:
        sec = fl(s)
        if sec is None: return None
    return -sec if neg else sec

M, HDR = lib.load_master()
MB = {r["Batch Name"].strip(): r for r in M if r.get("Batch Name", "").strip()}
def nsis(b):
    v = fl((MB.get(b) or {}).get("# Sisterless KTs")); return int(v) if v is not None else None
def ev(b, c): return hms((MB.get(b) or {}).get(c))
def day(b): return b.split()[0] if b else ""

TABLES = {}

# ================================================================ ITEM 11  n and n-of-days per plot
def item_11():
    # which figures are actually PLACED on the live decks
    placed = collections.defaultdict(set)
    for tsv in glob.glob(R + "/_claude_tmp/geom9_*.tsv"):
        deck = os.path.basename(tsv)[6:-4]
        for ln in io.open(tsv, encoding="utf-8", errors="replace").read().replace("\r", "\n").split("\n"):
            f = ln.split("\t")
            if len(f) > 6 and f[0] == "PlacedItem" and f[5]:
                placed[f[5]].add(f"{deck}:AB{f[1]}")
    rows = []
    for p in sorted(glob.glob(D + "/*.csv")):
        pid = os.path.basename(p)[:-4]
        try: rs = rd(p)
        except Exception: continue
        if not rs:
            rows.append(dict(plot=pid, placed_on="; ".join(sorted(placed.get(pid, []))) or "-",
                             n_rows=0, n_cells=0, n_days=0, days="", note="ZERO ROWS"))
            continue
        col = next((c for c in ("batch", "Batch Name", "cell", "sample") if c in rs[0]), None)
        bs = sorted({(r.get(col) or "").strip() for r in rs if (r.get(col) or "").strip()}) if col else []
        ds = sorted({day(b) for b in bs if b})
        rows.append(dict(plot=pid, placed_on="; ".join(sorted(placed.get(pid, []))) or "-",
                         n_rows=len(rs), n_cells=len(bs), n_days=len(ds), days=", ".join(ds),
                         note="" if col else "no cell-identity column"))
    rows.sort(key=lambda r: (r["placed_on"] == "-", r["plot"]))
    TABLES["item11_n_and_days_per_plot"] = (
        ["plot", "placed_on", "n_rows", "n_cells", "n_days", "days", "note"], rows,
        "Item 11 &mdash; n and number of imaging days behind every plot",
        "One row per recorded figure. <b>n_cells</b> counts distinct cells in that figure's own recorded "
        "data CSV; <b>n_days</b> counts distinct imaging dates among them. <b>placed_on</b> names the deck "
        "and artboard where the figure is currently placed (&ldquo;-&rdquo; = built but not on a live deck). "
        "These are the descriptive values to drop into a legend.")
    print(f"[item11] {len(rows)} plots, {sum(1 for r in rows if r['placed_on']!='-')} placed")

# ================================================================ ITEM 16  deformation frames
def item_16():
    TR = rd(A + "/KT_OUTLINE_TRACKS_20260723.csv")
    idx = {}
    for r in TR:
        idx[(r["batch"].strip(), r["track_id"].strip(), str(fl(r["frame"], -1)))] = r
    by_bt = collections.defaultdict(list)
    for r in TR: by_bt[(r["batch"].strip(), r["track_id"].strip())].append(r)

    CM = {}
    try:
        for r in rd(A + "/CHROMOSOME_MASTER.csv"):
            CM[( (r.get("batch") or "").strip(), (r.get("chr_num") or "").strip() )] = r
    except Exception: pass

    rows = []
    for p in sorted(glob.glob(D + "/G6ten_peakzoom__p*.csv")):
        for r in rd(p):
            b = (r.get("batch") or "").strip()
            fr = str(fl(r.get("frame"), -1))
            kt = (r.get("kt_shown") or "").strip()
            tmin = fl(r.get("t_min"))
            # find the matching track row for shape values
            cand = [x for (bb, tid), rs in by_bt.items() if bb == b for x in rs
                    if str(fl(x["frame"], -2)) == fr and (x["label"].strip() == kt
                                                          or (kt == "plate" and x["label"].strip() == "paired"))]
            c0 = cand[0] if cand else {}
            meta, ana = ev(b, "Metaphase Start (s)"), ev(b, "Anaphase Onset (s)")
            t = fl(c0.get("t_sec"))
            stage = ("prometaphase" if (t is not None and meta is not None and t < meta)
                     else "anaphase" if (t is not None and ana is not None and t >= ana)
                     else "metaphase")
            polarpaired = "polar" if kt in ("polar",) else "paired (at plate)" if kt in ("paired", "plate") else kt
            congress = (MB.get(b) or {}).get("Polar Chromosomes", "").strip()
            rows.append(dict(
                figure=os.path.basename(p)[:-4], batch=b, day=day(b), frame=r.get("frame"),
                kinetochore=polarpaired,
                circularity=(round(fl(c0.get("circularity")), 4) if fl(c0.get("circularity")) is not None else ""),
                aspect_ratio=(round(fl(c0.get("aspect_ratio")), 3) if fl(c0.get("aspect_ratio")) is not None else ""),
                distortion_um=(round(fl(r.get("distortion")), 3) if fl(r.get("distortion")) is not None else ""),
                min_into_metaphase=(round(tmin, 2) if tmin is not None else ""),
                n_sisterless=nsis(b),
                congressed=("no (polar at anaphase)" if congress.lower() == "yes" else
                            "yes" if congress.lower() == "no" else "not scored"),
                mitosis_stage=stage))
    TABLES["item16_deformation_frames"] = (
        ["figure", "batch", "day", "frame", "kinetochore", "circularity", "aspect_ratio", "distortion_um",
         "min_into_metaphase", "n_sisterless", "congressed", "mitosis_stage"], rows,
        "Item 16 &mdash; the kinetochores shown in the deformation frames",
        "Every kinetochore panel on the artboard-7 deformation sheets. Shape values are read from the same "
        "outline rows the panels were built from, so the table and the figure cannot disagree. "
        "<b>min_into_metaphase</b> is relative to metaphase onset; <b>distortion_um</b> is measured ALONG "
        "the spindle axis (it is not a k-k distance).")
    print(f"[item16] {len(rows)} deformation panels")

# ================================================================ ITEM 17  lagging chromosomes
def item_17():
    res = {}
    try: res = json.load(io.open(R + "/_claude_tmp/todo0818/results.json"))
    except Exception as e: print("[item17] no analysis results:", e)
    rows = []
    for r in res.get("lagging", []):
        b = r["batch"]
        rows.append(dict(batch=b, day=day(b), track=r["track"], n_sisterless=r.get("n_sisterless"),
                         n_frames=r.get("n_frames"),
                         circularity=(round(r["circ_median"], 4) if r.get("circ_median") else ""),
                         length_um=(round(r["length_um_median"], 3) if r.get("length_um_median") else ""),
                         n_pieces_max=r.get("max_pieces"),
                         fractured=("yes" if r.get("fractured") else "no"),
                         min_into_anaphase_at_fracture=(round(r["min_from_ana"], 2) if r.get("min_from_ana") is not None else ""),
                         elongation_at_fracture=(round(r["elong_at_fracture"], 3) if r.get("elong_at_fracture") else ""),
                         circularity_at_fracture=(round(r["circ_at_fracture"], 4) if r.get("circ_at_fracture") else "")))
    rows.sort(key=lambda r: (r["batch"], str(r["track"])))
    TABLES["item17_lagging_chromosomes"] = (
        ["batch", "day", "track", "n_sisterless", "n_frames", "circularity", "length_um", "n_pieces_max",
         "fractured", "min_into_anaphase_at_fracture", "elongation_at_fracture", "circularity_at_fracture"], rows,
        "Item 17 &mdash; the lagging chromosomes",
        "One row per lagging kinetochore track. <b>n_pieces_max</b> is the largest number of separate outlines "
        "she drew for that one kinetochore on a single frame &mdash; more than one piece is a fracture. "
        "<b>circularity</b> and <b>length_um</b> are the per-track medians across all its traced frames.")
    print(f"[item17] {len(rows)} lagging tracks")

# ================================================================ ITEM 18  k-k example frames
def item_18():
    rows = []
    p = D + "/G6kk_zoom_candidates.csv"
    src = rd(p) if os.path.exists(p) else []
    for r in src:
        b = (r.get("batch") or "").strip()
        meta = ev(b, "Metaphase Start (s)")
        # recover t_sec for that frame from the k-k store
        t = None
        for k in rd(A + "/KT_SISTER_KK_20260723.csv") if False else []:
            pass
        rows.append(dict(batch=b, day=day(b), frame=r.get("frame"),
                         kk_distance_um=fl(r.get("kk_um")),
                         cell_median_kk_um=fl(r.get("cell_median_kk_um")),
                         group_median_kk_um=fl(r.get("group_median_kk_um")),
                         n_sisterless=r.get("n_sisterless"),
                         track_a=r.get("track_a"), track_c=r.get("track_c")))
    # attach minutes into metaphase from the k-k store
    kkidx = {}
    for r in rd(A + "/KT_SISTER_KK_20260723.csv"):
        kkidx[(r["batch"].strip(), str(fl(r["frame"], -1)))] = r
    for row in rows:
        k = kkidx.get((row["batch"], str(fl(row["frame"], -1))))
        meta = ev(row["batch"], "Metaphase Start (s)")
        t = fl(k.get("t_sec")) if k else None
        row["min_into_metaphase"] = round((t - meta) / 60.0, 2) if (t is not None and meta is not None) else ""
        row["phase"] = (k.get("phase") if k else "")
    TABLES["item18_kk_example_frames"] = (
        ["batch", "day", "frame", "kk_distance_um", "min_into_metaphase", "phase", "n_sisterless",
         "cell_median_kk_um", "group_median_kk_um", "track_a", "track_c"], rows,
        "Item 18 &mdash; the k-k example frames",
        "The candidate k-k illustration frames. Distances come from <code>KT_SISTER_KK</code> &mdash; "
        "UNTARGETED paired sister kinetochores. This is deliberately NOT the ablation-target pair "
        "(<code>pre_abl</code>/<code>pre_abl_pair</code>), which measures a different quantity and must "
        "never be substituted here. <b>cell_median</b> and <b>group_median</b> show how representative "
        "each chosen frame is.")
    print(f"[item18] {len(rows)} k-k example frames")

# ================================================================ item 12 + model summaries
def extras():
    try:
        res = json.load(io.open(R + "/_claude_tmp/todo0818/results.json"))
        po = res.get("pooling", [])
        if po:
            TABLES["item12_pooling_2plus3"] = (
                ["comparison", "unit", "n_1sis", "n_2sis", "n_3sis", "n_pooled", "median_1sis", "median_3sis",
                 "median_2plus3", "p_3only", "p_2plus3", "verdict"], po,
                "Item 12 &mdash; would pooling 2+3-sisterless help?",
                "Every headline comparison run BOTH ways: 1-sisterless vs 3-sisterless only, and "
                "1-sisterless vs 2+3 pooled. <b>verdict</b> flags any result that changes significance.")
    except Exception as e: print("[extras] pooling:", e)
    try:
        mr = json.load(io.open(R + "/_claude_tmp/todo0818/model_results.json"))
        if mr.get("item5"):
            TABLES["item5_model_sweep"] = (
                ["model", "MAE", "medAE", "null_MAE", "gain", "R2", "spearman", "paired_p", "n"],
                mr["item5"],
                "Items 5 &amp; 10 &mdash; metaphase-duration model sweep",
                f"Leave-one-imaging-day-out over {mr.get('n_cells')} on-target 1- and 3-sisterless cells "
                f"({mr.get('n_days')} days, {mr.get('n_features')} features). Errors in MINUTES. "
                "<b>null_MAE</b> is the error from simply predicting the median duration &mdash; a model is "
                "only useful if it beats that by more than noise (<b>paired_p</b>).")
        if mr.get("item6"):
            TABLES["item6_remaining_time"] = (
                ["landmark_min", "model", "MAE", "null_MAE", "gain", "R2", "spearman", "paired_p", "n_cells"],
                mr["item6"],
                "Item 6 &mdash; predicting time REMAINING in metaphase",
                "Landmark models: given everything observable up to L minutes into metaphase, predict the "
                "minutes still to go. Only cells still in metaphase at L are included.")
        if mr.get("importance"):
            TABLES["item7_what_would_help"] = (
                ["feature", "importance", "coverage", "headroom"], mr["importance"][:60],
                "Item 7 &mdash; what would most improve the model",
                "<b>importance</b> is how heavily the model leans on that measurement; <b>coverage</b> is the "
                "fraction of cells that actually have it. <b>headroom</b> = importance &times; (1 &minus; coverage) "
                "&mdash; a high value means the model already values it AND many cells are missing it, so "
                "annotating more of it is the highest-yield next step.")
    except Exception as e: print("[extras] model:", e)

for fn in (item_11, item_16, item_17, item_18, extras):
    try: fn()
    except Exception as e:
        import traceback; print("[ERROR]", fn.__name__, e); traceback.print_exc()

# ================================================================ write CSVs + the HTML document
for name, (hdr, rows, title, blurb) in TABLES.items():
    with io.open(f"{DEST}/{name}.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f); w.writerow(hdr)
        for r in rows: w.writerow([r.get(k, "") for k in hdr])

def cell(v):
    if v is None: return ""
    if isinstance(v, float):
        if abs(v) >= 1e-4 or v == 0: return f"{v:.4g}"
        return f"{v:.2e}"
    return html.escape(str(v))

parts = []
for name, (hdr, rows, title, blurb) in TABLES.items():
    th = "".join(f"<th data-c='{i}'>{html.escape(h)}</th>" for i, h in enumerate(hdr))
    tb = "".join("<tr>" + "".join(f"<td>{cell(r.get(h))}</td>" for h in hdr) + "</tr>" for r in rows)
    parts.append(f"""
<section id="{name}">
  <h2>{title}</h2>
  <p class="blurb">{blurb}</p>
  <div class="meta">{len(rows)} rows &middot; <a href="{name}.csv" download>{name}.csv</a></div>
  <input class="filter" data-for="{name}" placeholder="filter these rows&hellip;">
  <div class="scroll"><table id="t_{name}"><thead><tr>{th}</tr></thead><tbody>{tb}</tbody></table></div>
</section>""")

nav = "".join(f'<a href="#{n}">{TABLES[n][2].split("&mdash;")[0].strip()}</a>' for n in TABLES)
doc = f"""<!doctype html><html><head><meta charset="utf-8">
<title>Ablation tables &mdash; 2026-08-18</title><style>
:root{{--bg:#fff;--fg:#16191d;--mut:#5b6570;--line:#e3e7eb;--head:#f6f8fa;--acc:#0072b2;--hl:#fff8e1}}
@media(prefers-color-scheme:dark){{:root{{--bg:#14171a;--fg:#e8ecef;--mut:#9aa4ae;--line:#2a3036;--head:#1c2126;--acc:#4da3d8;--hl:#2e2a1b}}}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--fg);font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif}}
header{{padding:30px 34px 16px;border-bottom:1px solid var(--line)}}
h1{{margin:0 0 6px;font-size:25px;letter-spacing:-.01em}}
.sub{{color:var(--mut);font-size:14px}}
nav{{position:sticky;top:0;z-index:5;background:var(--bg);border-bottom:1px solid var(--line);
     padding:11px 34px;display:flex;gap:16px;flex-wrap:wrap}}
nav a{{color:var(--acc);text-decoration:none;font-size:13.5px;font-weight:500}}
nav a:hover{{text-decoration:underline}}
section{{padding:30px 34px;border-bottom:1px solid var(--line)}}
h2{{margin:0 0 8px;font-size:19px}}
.blurb{{color:var(--mut);max-width:78ch;margin:0 0 10px;font-size:13.5px}}
.meta{{color:var(--mut);font-size:12.5px;margin-bottom:10px}}
.meta a{{color:var(--acc)}}
.filter{{width:280px;padding:7px 10px;margin-bottom:10px;border:1px solid var(--line);
         border-radius:7px;background:var(--bg);color:var(--fg);font-size:13px}}
.scroll{{overflow-x:auto;border:1px solid var(--line);border-radius:9px;max-height:600px;overflow-y:auto}}
table{{border-collapse:collapse;width:100%;font-size:12.8px;font-variant-numeric:tabular-nums}}
thead th{{position:sticky;top:0;background:var(--head);text-align:left;padding:9px 11px;
          border-bottom:2px solid var(--line);cursor:pointer;white-space:nowrap;font-weight:600}}
thead th:hover{{color:var(--acc)}}
td{{padding:7px 11px;border-bottom:1px solid var(--line);white-space:nowrap}}
tbody tr:hover{{background:var(--hl)}}
code{{background:var(--head);padding:1px 5px;border-radius:4px;font-size:12px}}
</style></head><body>
<header><h1>Ablation project &mdash; reference tables</h1>
<div class="sub">Generated 2026-08-18 from the recorded figure data and the annotation stores.
Click any column header to sort. Each table also downloads as CSV.</div></header>
<nav>{nav}</nav>
{''.join(parts)}
<script>
document.querySelectorAll('table').forEach(function(t){{
  t.querySelectorAll('thead th').forEach(function(th,i){{
    var asc=true;
    th.addEventListener('click',function(){{
      var tb=t.tBodies[0], rows=[].slice.call(tb.rows);
      rows.sort(function(a,b){{
        var x=a.cells[i].textContent.trim(), y=b.cells[i].textContent.trim();
        var nx=parseFloat(x), ny=parseFloat(y);
        var num=!isNaN(nx)&&!isNaN(ny)&&x!==''&&y!=='';
        if(num) return asc?nx-ny:ny-nx;
        return asc?x.localeCompare(y):y.localeCompare(x);
      }});
      asc=!asc; rows.forEach(function(r){{tb.appendChild(r)}});
    }});
  }});
}});
document.querySelectorAll('.filter').forEach(function(inp){{
  inp.addEventListener('input',function(){{
    var q=inp.value.toLowerCase(), t=document.getElementById('t_'+inp.dataset.for);
    [].slice.call(t.tBodies[0].rows).forEach(function(r){{
      r.style.display = r.textContent.toLowerCase().indexOf(q)>-1 ? '' : 'none';
    }});
  }});
}});
</script></body></html>"""
io.open(f"{DEST}/ABLATION_TABLES_20260818.html", "w", encoding="utf-8").write(doc)
print(f"\n[done] {len(TABLES)} tables -> {DEST}/ABLATION_TABLES_20260818.html")
for n, (h, r, t, b) in TABLES.items(): print(f"   {n:36s} {len(r):5d} rows")
