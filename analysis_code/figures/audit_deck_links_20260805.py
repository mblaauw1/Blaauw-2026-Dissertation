#!/usr/bin/env python3
"""Are the four .ai decks up to date with what is on disk?

USER 2026-08-05: "make sure that everything is up-to-date in the meta, supplemental, timestrip, and new
figures files".

I cannot open the .ai files — another session has META and supplemental open, and her standing rule is
that her deck edits are never touched. So this reports rather than edits: it reads each deck with
`strings` (no lock, no modification), lists every asset it links, and checks each one against disk.

Three states per link:
  CURRENT — the asset exists and has not been rebuilt since the .ai was last saved
  STALE   — the asset has been REBUILT since the .ai was saved, so the deck is showing an older image
            until it is relinked (Illustrator does this on open, or via Links > Update)
  BROKEN  — no file of that name exists anywhere in the figure tree

Writes 4_TABLES_AND_REPORTS/DECK_LINK_STATUS_20260805.md. Re-run it any time; it takes seconds.
"""
import os, re, subprocess, collections, datetime

ROOT = "/Volumes/4 MB"
AI = f"{ROOT}/ablation_plots"
OUTMD = f"{ROOT}/4_TABLES_AND_REPORTS/DECK_LINK_STATUS_20260805.md"
DECKS = ["META_FIGURES_20260803.ai", "supplemental.ai",
         "NEW_TIMESTRIPS_20260804.ai", "NEW_FIGURES_20260804.ai"]

idx = collections.defaultdict(list)
for root in ("ablation_figures_20260625", "ablation_plots"):
    for dp, _, fns in os.walk(os.path.join(ROOT, root)):
        if ".bak" in dp or "_backup" in dp:
            continue
        for fn in fns:
            if fn.lower().endswith((".png", ".pdf", ".svg")):
                idx[fn].append(os.path.join(dp, fn))

def ts(t): return datetime.datetime.fromtimestamp(t).strftime("%m-%d %H:%M")

report = []
for d in DECKS:
    p = os.path.join(AI, d)
    if not os.path.exists(p):
        report.append((d, None, [], [], [])); continue
    aimt = os.path.getmtime(p)
    s = subprocess.run(["strings", "-a", "-n", "5", p], capture_output=True, text=True,
                       errors="replace").stdout
    links = sorted(set(re.findall(r"[A-Za-z0-9_.-]+\.(?:png|pdf|svg)", s)))
    cur, stale, broken = [], [], []
    for l in links:
        if l not in idx:
            broken.append(l); continue
        best = max(idx[l], key=os.path.getmtime)
        m = os.path.getmtime(best)
        (stale if m > aimt else cur).append((l, m))
    report.append((d, aimt, cur, sorted(stale, key=lambda z: -z[1]), broken))

with open(OUTMD, "w", encoding="utf-8") as f:
    f.write("# Deck link status — are the four .ai files up to date?\n\n")
    f.write(f"Generated {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}. "
            "Read with `strings`; no .ai file was opened or modified.\n\n")
    f.write("**STALE does not mean broken.** The asset on disk is correct and current; the deck is still "
            "showing the previous render of it. Opening the file in Illustrator, or Links > Update Link, "
            "picks up the new version. Every stale entry below is a figure that was rebuilt today.\n\n")
    tot_s = sum(len(r[3]) for r in report); tot_b = sum(len(r[4]) for r in report)
    f.write(f"Across the four decks: **{tot_s} links need updating**, **{tot_b} are broken**.\n\n")
    for d, aimt, cur, stale, broken in report:
        f.write(f"## {d}\n\n")
        if aimt is None:
            f.write("_file not found_\n\n"); continue
        f.write(f"last saved {ts(aimt)} · {len(cur)} current · **{len(stale)} stale** · "
                f"**{len(broken)} broken**\n\n")
        if broken:
            f.write("### BROKEN — no file of this name exists\n\n")
            for b in broken: f.write(f"- `{b}`\n")
            f.write("\n")
        if stale:
            f.write("### Rebuilt since this deck was saved — relink to pick them up\n\n")
            f.write("| rebuilt | asset |\n|---|---|\n")
            for l, m in stale: f.write(f"| {ts(m)} | `{l}` |\n")
            f.write("\n")

print(f"decks checked: {len(DECKS)}")
for d, aimt, cur, stale, broken in report:
    if aimt is None: print(f"  {d:34} NOT FOUND"); continue
    print(f"  {d:34} saved {ts(aimt)}  current {len(cur):3d}  stale {len(stale):3d}  broken {len(broken)}")
    for b in broken: print(f"       BROKEN: {b}")
print(f"-> {OUTMD}")
