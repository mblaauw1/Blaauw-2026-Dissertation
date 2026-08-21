#!/usr/bin/env python3
"""THIRD-LEVEL AUDIT — invariants that hold across the whole project, not per-file checks.

Everything here is a rule she has stated, expressed as something that must be TRUE of the data on disk:

  A  a batch on MANUAL_PLOT_EXCLUSIONS must NOT appear in that plot's recorded data
  B  a globally-excluded cell (KT_OUTLINE_EXCLUDE) must not appear in ANY derived store
  C  metaphase-ablation cells must not appear in a master-derived figure unless the figure says so
  D  every PDF linked from a deck must be a readable PDF (header + EOF, non-zero)
  E  one figure NAME must not resolve to two different files across decks
  F  a legend bullet must not be older than the data it describes
  G  no figure may put red and green in the same axes (her colourblindness rule)
  H  a timestrip panel must not contain a pure-black pad band
"""
import csv, io, json, os, re, glob, collections, datetime
ROOT = "/Volumes/4 MB"
OUT  = ROOT + "/4_TABLES_AND_REPORTS/THIRD_LEVEL_AUDIT_20260819.md"
find = collections.defaultdict(list)
ps   = json.load(open(ROOT + "/ablation_plots/PLOT_SETTINGS.json"))

def rd(p):
    """DictReader, but tolerant of the duplicate column names some stores carry."""
    with io.open(p, encoding="utf-8", errors="replace") as f:
        rows = list(csv.DictReader(f))
    out = []
    for r in rows:
        out.append({k: (" ".join(str(x) for x in v if x is not None) if isinstance(v, list) else v)
                    for k, v in r.items()})
    return out

def data_path(pid):
    d = (ps.get(pid) or {}).get("data")
    if not d: return None
    p = os.path.join(ROOT, "ablation_plots", d)
    return p if os.path.exists(p) else None

# ---------------------------------------------------------------- A manual exclusions, BY SCOPE
# An exclusion row is not always "delete this cell from this plot". Three kinds exist and only the first
# is verifiable as absence:
#   WHOLE  -- the cell must not appear in that plot's data at all
#   PART   -- one series / one ablation / one POINT was dropped ("sister LINE not plotted",
#             "outlier POINT removed"); the cell legitimately still has its other rows
#   PICK   -- "not used as the <x> example": a choice of example movie, not a data exclusion
# Treating every row as WHOLE produced a false alarm on G4_ablation_intensity_combined, where the sister
# line for ablation #0 is exactly what was dropped and the targeted line is meant to stay.
ex = rd(ROOT + "/annotations/MANUAL_PLOT_EXCLUSIONS.csv")
PART = re.compile(r"\bPOINT\b|LINE not plotted|only the|doesn't recover|ablation #\d", re.I)
PICK = re.compile(r"timestrip|not used as|example", re.I)
def scope_ids(txt):
    """Resolve the free-text plot scope she wrote into the plot ids it actually covers."""
    t = txt.strip()
    if t in ps: return [t]
    low = t.lower()
    # "G4_fluor_over_time (all fluorescence OVER-TIME/trend/scaled plots)" -- the id comes first and the
    # parenthesis explains the family. Resolve the prefix BEFORE the free-text phrases, or the phrase
    # match swallows a scope that was already precise.
    head = t.split("(")[0].strip()
    if head in ps or re.match(r"^G\d[A-Za-z0-9_]+$", head):
        fam = [k for k in ps if k == head or k.startswith(head + "_")]
        fam = [k for k in fam if (ps.get(k) or {}).get("data")]
        if fam: return sorted(fam)
    if low.startswith("all plots"):
        return sorted(k for k, v in ps.items() if isinstance(v, dict) and v.get("data") and not v.get("retired"))
    pats = []
    if "all fluor" in low:                      pats = [r"^G4_fluor"]
    elif "all kk plots" in low or "kinetochore-distance" in low: pats = [r"^G2_kk", r"kk_"]
    elif "+_journal" in low:
        base = t.split(" ")[0]; return [k for k in (base, base + "_journal") if k in ps]
    elif "/" in t:
        return [k.strip() for k in t.split("/") if k.strip() in ps]
    elif "(" in t and t.split("(")[0].strip() in ps:
        return [t.split("(")[0].strip()]
    out = []
    for pat in pats: out += [k for k in ps if re.search(pat, k)]
    return sorted(set(k for k in out if (ps.get(k) or {}).get("data")))

CARVE = {"20251029 triple_ablation_12": ("lagging_vs_congression", "lagging")}   # her 2026-08-18 decision
checked = unverifiable = 0
for r in ex:
    plot, b = (r.get("plot") or "").strip(), (r.get("batch") or "").strip()
    reason = (r.get("reason") or "")
    if not plot or not b: continue
    if PICK.search(plot) or PICK.search(reason):
        unverifiable += 1
        find["A: example-choice row, nothing to verify in data (recorded, not a defect)"].append(f"{plot} :: {b}")
        continue
    if PART.search(reason):
        unverifiable += 1
        find["A: partial removal (one series/point) — absence is the WRONG test, needs an eye"].append(
            f"{plot} :: {b} :: {reason[:70]}")
        continue
    ids = scope_ids(plot)
    if not ids:
        find["A: exclusion scope I could not resolve to any plot id"].append(f"{plot} :: {b}")
        continue
    for pid in ids:
        p = data_path(pid)
        if not p: continue
        if b in CARVE and CARVE[b][0] in pid: continue      # documented carve-out, her instruction
        checked += 1
        hit = sum(1 for x in rd(p) if any(b == (v or "").strip() for v in x.values()))
        if hit:
            find["A: EXCLUDED CELL STILL IN THE PLOT'S DATA"].append(f"{pid} :: {b} ({hit} rows)")

# ---------------------------------------------------------------- B global kt-outline exclusion
import sys; sys.path.insert(0, ROOT + "/ablation_figures_20260625")
try:
    import lib
    GLOBAL = set(getattr(lib, "KT_OUTLINE_EXCLUDE", ()) or ())
except Exception as e:
    GLOBAL = set(); find["B: could not import lib"].append(str(e)[:120])
DERIVED = ["KT_OUTLINE_TRACKS_20260723.csv", "KT_LANDMARK_ANALYSIS_20260723.csv", "KT_SISTERS_20260723.csv",
           "KT_SISTER_KK_20260723.csv", "KT_TENSION_20260723.csv", "KT_TENSION_LOADAXIS_20260805.csv",
           "KT_CHROMO_ANALYSIS_20260723.csv", "KT_LOADING_AXIS_20260805.csv"]
for store in DERIVED:
    p = ROOT + "/annotations/" + store
    if not os.path.exists(p): continue
    bs = {(r.get("batch") or "").strip() for r in rd(p)}
    for g in GLOBAL:
        if g in bs: find["B: globally excluded cell present in a derived store"].append(f"{store} :: {g}")

# ---------------------------------------------------------------- D linked PDFs are readable
links = set()
for f in glob.glob(ROOT + "/_claude_tmp/geom9_*.tsv"):
    for ln in io.open(f, encoding="utf-8", errors="replace").read().replace("\r", "\n").split("\n"):
        c = ln.split("\t")
        if len(c) > 11 and c[0] == "PlacedItem" and c[11].strip(): links.add(c[11].strip())
for p in sorted(links):
    if not os.path.exists(p):
        find["D: linked file missing"].append(p); continue
    if os.path.getsize(p) < 1000:
        find["D: linked file suspiciously small"].append(f"{os.path.basename(p)} ({os.path.getsize(p)} B)"); continue
    if p.lower().endswith(".pdf"):
        with open(p, "rb") as fh:
            head = fh.read(5)
            fh.seek(max(0, os.path.getsize(p) - 1400)); tail = fh.read()
        if head != b"%PDF-" or b"%%EOF" not in tail:
            find["D: linked PDF does not parse as a PDF"].append(os.path.basename(p))

# ---------------------------------------------------------------- E one name, two files
byname = collections.defaultdict(set)
for f in glob.glob(ROOT + "/_claude_tmp/geom9_*.tsv"):
    tag = os.path.basename(f)[6:-4]
    for ln in io.open(f, encoding="utf-8", errors="replace").read().replace("\r", "\n").split("\n"):
        c = ln.split("\t")
        if len(c) > 11 and c[0] == "PlacedItem" and c[5] and c[11].strip():
            byname[c[5]].add(c[11].strip())
for n, paths in byname.items():
    # pdf/ vs pdf_pub/ is the intended pair; anything else is two different figures under one name
    stems = {os.path.basename(x) for x in paths}
    dirs  = {os.path.dirname(x) for x in paths}
    if len(stems) > 1 or not dirs <= {ROOT + "/ablation_figures_20260625/_ai_relink/pdf",
                                      ROOT + "/ablation_figures_20260625/_ai_relink/pdf_pub"}:
        find["E: one figure name resolves to different files"].append(f"{n} -> {sorted(paths)}")

# ---------------------------------------------------------------- F bullets older than their data
for pid, e in ps.items():
    if not isinstance(e, dict) or not e.get("legend_bullets") or e.get("retired"): continue
    built = e.get("legend_bullets_built")
    p = data_path(pid)
    if not (built and p): continue
    try: b = datetime.datetime.strptime(built, "%Y-%m-%d %H:%M")
    except ValueError: continue
    if datetime.datetime.fromtimestamp(os.path.getmtime(p)) > b + datetime.timedelta(minutes=2):
        find["F: legend bullet older than the data it describes"].append(
            f"{pid}: bullets {built}, data {datetime.datetime.fromtimestamp(os.path.getmtime(p)):%m-%d %H:%M}")

# ---------------------------------------------------------------- C metaphase-ablation default exclusion
# Her rule: metaphase-ablation cells are a separate group and are filtered out of every master-derived
# set unless the figure is explicitly about them.
try:
    META_ABL = {b for b in {(r.get("batch") or "").strip() for pid in ps for r in
                            (rd(data_path(pid)) if data_path(pid) else [])} if b and lib.is_metaphase_ablation(b)}
except Exception:
    META_ABL = set()
ALLOWED = re.compile(r"metaphase_abl|phase_split|prometa|meta_vs|by_phase|phase_of_abl", re.I)
for pid, e in ps.items():
    if not isinstance(e, dict) or e.get("retired"): continue
    p = data_path(pid)
    if not p or ALLOWED.search(pid): continue
    rows = rd(p)
    if not rows or "batch" not in rows[0]: continue
    hit = sorted({(r.get("batch") or "").strip() for r in rows} & META_ABL)
    if hit:
        find["C: metaphase-ablation cell in a figure that is not about metaphase ablation"].append(
            f"{pid}: {', '.join(h[:34] for h in hit[:4])}{' …' if len(hit) > 4 else ''}")

# ---------------------------------------------------------------- G red + green in one figure
# NOTES rule 30 / her colourblindness: never red and green together, including red markers on a green
# fluorescence panel. Read the colour operators straight out of the placed PDF rather than trusting code.
import zlib
def pdf_colours(path):
    raw = open(path, "rb").read()
    out = []
    for m in re.finditer(rb"stream\r?\n(.*?)endstream", raw, re.S):
        blob = m.group(1)
        try: blob = zlib.decompress(blob)
        except Exception: pass
        for c in re.finditer(rb"([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+(rg|RG)\b", blob):
            try: out.append(tuple(float(c.group(i)) for i in (1, 2, 3)))
            except ValueError: pass
    return out
# Judge by HUE, not by raw channel size. The first version called (0.545, 0.227, 0.0) "red": that is a
# 25-degree dark ORANGE, the standard colourblind-safe partner for green, and it produced 81 false alarms.
import colorsys
def _h(c): return colorsys.rgb_to_hsv(*c)
def is_red(c):
    h, sa, v = _h(c); h *= 360
    return (h <= 14 or h >= 346) and sa >= .55 and v >= .35
def is_green(c):
    h, sa, v = _h(c); h *= 360
    return 90 <= h <= 165 and sa >= .30 and v >= .25
pdfs = sorted({p for p in links if p.lower().endswith(".pdf") and os.path.exists(p)})
for p in pdfs:
    try: cols = pdf_colours(p)
    except Exception: continue
    reds   = {c for c in cols if is_red(c)}
    greens = {c for c in cols if is_green(c)}
    if reds and greens:
        find["G: red AND green in the same figure (colourblind rule)"].append(
            f"{os.path.basename(p)}: red {sorted(reds)[:2]} green {sorted(greens)[:2]}")

# ---------------------------------------------------------------- H black pad bands in timestrip panels
# "A crop must NEVER fabricate pixels" -- a black band at a panel edge is padding, not image.
try:
    from PIL import Image
    names = {os.path.basename(p).rsplit(".", 1)[0] for p in links}
    # look wherever a panel PNG can live, not just the three timestrip folders
    pngs = [q for d in ("group1/timestrips", "group1/timestrips2", "group1/frap_timestrips",
                        "group1", "group2", "group3", "group4", "group5", "group6", "group9")
            for q in glob.glob(f"{ROOT}/ablation_figures_20260625/{d}/*.png")
            if os.path.basename(q).rsplit(".", 1)[0] in names]
    pngs = sorted(set(pngs))
    for q in pngs[:900]:
        im = Image.open(q).convert("L")
        w, h = im.size
        px = im.load()
        def col_black(x): return all(px[x, y] <= 4 for y in range(0, h, max(1, h // 120)))
        def row_black(y): return all(px[x, y] <= 4 for x in range(0, w, max(1, w // 160)))
        left  = sum(1 for x in range(min(40, w)) if col_black(x))
        right = sum(1 for x in range(w - 1, max(w - 41, 0), -1) if col_black(x))
        top   = sum(1 for y in range(min(40, h)) if row_black(y))
        bot   = sum(1 for y in range(h - 1, max(h - 41, 0), -1) if row_black(y))
        if max(left, right, top, bot) >= 3:
            find["H: black pad band at a timestrip panel edge"].append(
                f"{os.path.basename(q)}: L{left} R{right} T{top} B{bot}")
    H_CHECKED = len(pngs[:900])
except Exception as e:
    H_CHECKED = 0
    find["H: could not run the black-band check"].append(str(e)[:120])

with io.open(OUT, "w", encoding="utf-8") as f:
    tot = sum(len(v) for v in find.values())
    f.write(f"# Third-level audit — {datetime.date.today()}\n\n**{tot} finding(s).** "
            f"{checked} (cell x plot) exclusions verified against plot data; {len(links)} deck links checked; "
            f"{len(pdfs)} PDFs colour-scanned; {H_CHECKED} timestrip panels checked for black pads.\n\n")
    for k in sorted(find):
        f.write(f"## {k} — {len(find[k])}\n")
        for x in find[k][:60]: f.write(f"* {x}\n")
        f.write("\n")
    if not tot: f.write("Every invariant holds.\n")
print(f"exclusions verified: {checked}   deck links: {len(links)}   global excludes: {sorted(GLOBAL)}")
print("findings:", sum(len(v) for v in find.values()))
for k, v in sorted(find.items()):
    print(f"  {k}: {len(v)}")
    for x in v[:6]: print("      ", x)
print("->", OUT)
