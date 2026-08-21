#!/usr/bin/env python3
"""DEEP VERIFY — the second-level pass, for the failure modes the first-level checks cannot see.

Checks
  A  PLOT_SETTINGS integrity      entries whose data file is missing; bullets without a caption; ids that
                                  differ only by case; panels pointing at a parent that does not exist
  B  RENDER/RECORD CONSISTENCY    a figure whose PDF and data CSV were written at very different times
  C  BACKUPS                      every code file modified today has a backup somewhere
  D  DECK LINKS                   every linked file on a live deck exists on disk (from the geometry dump)
  E  DRAWN-vs-STORED BULLETS      the decks were saved after the last legend rebuild
  F  NOTHING SAVED LOCALLY        no project file written under ~ today (her standing rule)
"""
import csv, io, json, os, re, datetime, collections, subprocess
ROOT = "/Volumes/4 MB"
OUT = ROOT + "/4_TABLES_AND_REPORTS/DEEP_VERIFY_20260818.md"
today = datetime.date.today()
find = collections.defaultdict(list)
ps = json.load(open(ROOT + "/ablation_plots/PLOT_SETTINGS.json"))

# ---------- A PLOT_SETTINGS integrity
lower = collections.defaultdict(list)
for pid, e in ps.items():
    lower[pid.lower()].append(pid)
    if not isinstance(e, dict): continue
    if e.get("retired"): continue          # already retired on purpose; its data is meant to be gone
    d = e.get("data")
    if d and d not in ("", "None") and not os.path.exists(os.path.join(ROOT, "ablation_plots", d)):
        find["A: recorded data file missing"].append(f"{pid} -> {d}")
    if e.get("legend_bullets") and not (e.get("caption") or "").strip():
        find["A: bullets but no caption"].append(pid)
    par = e.get("panel_of")
    if par and par not in ps:
        find["A: panel points at a missing parent"].append(f"{pid} -> {par}")
for k, v in lower.items():
    if len(v) > 1:
        find["A: ids differing only by case"].append(" / ".join(v))

# ---------- B render vs record consistency (only for figures placed on live decks)
placed = {}
for f in os.listdir(ROOT + "/_claude_tmp"):
    if f.startswith("geom9_") and f.endswith(".tsv"):
        for r in csv.DictReader(io.open(f"{ROOT}/_claude_tmp/{f}", encoding="utf-8", errors="replace"), delimiter="\t"):
            if r.get("kind") == "PlacedItem" and (r.get("linked") or "").strip():
                placed[os.path.basename(r["linked"]).rsplit(".", 1)[0]] = r["linked"]
for pid, link in placed.items():
    d = os.path.join(ROOT, "ablation_plots/data", pid + ".csv")
    if ((ps.get(pid) or {}).get("n_rows") or 99) <= 1: continue   # provenance stub (timestrips), not plotted data
    if os.path.exists(link) and os.path.exists(d):
        dt = os.path.getmtime(link) - os.path.getmtime(d)
        if dt < -3600:                      # PDF is more than an hour OLDER than its data
            find["B: figure PDF older than its own data"].append(
                f"{pid}: pdf {datetime.datetime.fromtimestamp(os.path.getmtime(link)):%m-%d %H:%M} "
                f"vs data {datetime.datetime.fromtimestamp(os.path.getmtime(d)):%m-%d %H:%M}")

# ---------- C backups for everything changed today
CODE_DIRS = ["ablation_figures_20260625", "dataops", "kt_outline", "ablation_plots",
             "ablation_figures_20260625/figures"]
changed = []
for d in CODE_DIRS:
    p = os.path.join(ROOT, d)
    if not os.path.isdir(p): continue
    for fn in os.listdir(p):
        fp = os.path.join(p, fn)
        if not os.path.isfile(fp) or not fn.endswith((".py", ".jsx")): continue
        if ".bak" in fn: continue
        if datetime.date.fromtimestamp(os.path.getmtime(fp)) == today:
            changed.append(os.path.join(d, fn))
bk = set(os.listdir(ROOT + "/_master_backups"))
# The 2026-08-18 drive reorganisation re-COPIED whole directories, which resets mtime without touching
# content. Those copies arrive in tight bursts; a real edit is a lone timestamp. Counting the bursts as
# "modified" produced 214 phantom findings, so the bursts are identified and skipped.
stamps = collections.Counter(datetime.datetime.fromtimestamp(os.path.getmtime(os.path.join(ROOT, r))).strftime("%H:%M")
                             for r in changed)
BURST = {k for k, v in stamps.items() if v >= 5}
bakdir = {}
for d in CODE_DIRS:
    p = os.path.join(ROOT, d)
    if os.path.isdir(p):
        for fn in os.listdir(p):
            if ".bak" in fn: bakdir.setdefault(d, set()).add(fn)
for rel in changed:
    base, d = os.path.basename(rel), os.path.dirname(rel)
    if datetime.datetime.fromtimestamp(os.path.getmtime(os.path.join(ROOT, rel))).strftime("%H:%M") in BURST:
        continue                                            # reorg copy, not an edit
    has = (any(b.startswith(base + ".bak") for b in bk)                      # _master_backups
           or any(b.startswith(base + ".bak") for b in bakdir.get(d, ())))   # in-place .bak_* beside it
    created_today = "_20260818" in base or "_0818" in base   # written today; there is no earlier version
    if not has and not created_today:
        find["C: edited today with no backup of the pre-edit version"].append(rel)

# ---------- D deck links exist
for pid, link in placed.items():
    if not os.path.exists(link):
        find["D: deck links a file that does not exist"].append(f"{pid} -> {link}")

# ---------- E drawn vs stored bullets
built = max((v.get("legend_bullets_built") or "") for v in ps.values() if isinstance(v, dict))
for d in ("META_FIGURES_20260814.ai", "META_FIGURES_20260813_supplemental.ai", "NEW_FIGURES_20260804.ai",
          "supplemental.ai", "NEW_TIMESTRIPS_20260804.ai"):
    p = f"{ROOT}/1_DECKS/{d}"
    if not os.path.exists(p): continue
    saved = datetime.datetime.fromtimestamp(os.path.getmtime(p)).strftime("%Y-%m-%d %H:%M")
    if built and saved < built:
        find["E: deck saved before the last legend rebuild"].append(f"{d}: saved {saved}, bullets built {built}")

# ---------- F nothing saved locally
home = os.path.expanduser("~")
for sub in ("", "Downloads", "Documents", "Desktop"):
    p = os.path.join(home, sub)
    try: names = os.listdir(p)
    except OSError: continue
    for fn in names:
        fp = os.path.join(p, fn)
        try:
            if not os.path.isfile(fp): continue
            if datetime.date.fromtimestamp(os.path.getmtime(fp)) != today: continue
        except OSError: continue
        # Her own downloads live here too. Only PROJECT-shaped names are a rule violation
        # ("never save locally"); flagging her to-do PDF every run just trains the eye to skip the check.
        if not fn.endswith((".csv", ".png", ".pdf", ".md")) or fn.startswith("."): continue
        if re.search(r"2026\d{4}|ablation|kt_|meta_|^G\d[_a-z]|sisterless|congress|timestrip|PLOT_SETTINGS",
                     fn, re.I):
            find["F: PROJECT file written under ~ today (must live on 4 MB)"].append(os.path.join(sub, fn))

with io.open(OUT, "w", encoding="utf-8") as f:
    total = sum(len(v) for v in find.values())
    f.write(f"# Deep verify — {datetime.date.today()}\n\n**{total} finding(s).**\n\n")
    for k in sorted(find):
        f.write(f"## {k} — {len(find[k])}\n")
        for x in find[k][:40]: f.write(f"* {x}\n")
        f.write("\n")
    if not total: f.write("Nothing found in any category.\n")
print(f"code files modified today: {len(changed)}   placed figures checked: {len(placed)}")
print(f"findings: {sum(len(v) for v in find.values())}")
for k, v in sorted(find.items()):
    print(f"  {k}: {len(v)}")
    for x in v[:8]: print("      ", x)
print("->", OUT)
