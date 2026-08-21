#!/usr/bin/env python3
"""Does the assembled Results text still cover what is actually ON the main publication deck?

HER ASK, 2026-08-21: *"go over this 'compiled' results and discussion sections and make sure that, with the
updates to the main figure publication version over the past few hrs, its structure still covers everything"*

Two directions, because only checking one of them is how a section quietly goes stale:
  FIGURE -> TEXT   a figure is placed but no sentence in its section talks about it   (an orphan panel)
  TEXT   -> FIGURE a section exists but its artboard carries no artwork               (a promise with no figure)

Coverage is keyword-based and deliberately generous: a HIT means the section plausibly covers the panel, so
only the MISSES are worth her time. Reads the read-only geometry dump, never the .ai (deck halt).
"""
import collections, io, json, os, re, sys

ROOT = "/Volumes/4 MB"
GEOM = f"{ROOT}/_claude_tmp/geom9_pub0814.tsv"
TEXT = f"{ROOT}/4_TABLES_AND_REPORTS/RESULTS_AND_DISCUSSION_20260821.md"
OUT  = f"{ROOT}/4_TABLES_AND_REPORTS/TEXT_VS_DECK_COVERAGE_20260821.md"

# artboard -> the figure number SHE has typed on it (topmost title wins; both numbers are reported below)
AB_FIG = {"1": "Fig 1", "2": "Fig 2", "5": "Fig 3", "7": "Fig 4",
          "8": "Fig 5", "4": "Fig 6", "6": "Fig 7", "3": "Fig 8", "9": "Fig 9"}

# what each figure-name stem is ABOUT, in words her prose would plausibly use
TOPIC = [
 (r"mad1|hec1",             ["mad1", "hec1", "sac signal", "silence its sac"]),
 (r"prepost_intensity",     ["cdc20 signal", "disappearance", "photobleach"]),
 (r"violin2|exhaustion|zm", ["metaphase duration", "delay", "off-target", "zm"]),
 (r"slippage|nocodazole|noc", ["slippage", "nocodazole", "colclemid", "8+ hours"]),
 (r"kt_fate|sisbehav|swimmer", ["fate", "localize", "polar", "metaphase plate"]),
 (r"lagging",               ["lagging", "chromatid", "midzone"]),
 (r"length_vs_congression|chromolen", ["length", "longer chromosomes", "chromosome size"]),
 (r"distortion|tension|G6ten", ["tension", "stretch", "deformation", "oscillat"]),
 (r"kymo|osc|amplitude|period", ["oscillat", "movement pattern"]),
 (r"kk|k-k",                ["k-k", "kinetochore to both poles", "merotelic"]),
 (r"area|roundness|centroid|rotation|solidity|shape", ["round", "cross-sectional area", "plate rotation", "shape"]),
 (r"collagen",              ["collagen"]),
 (r"washout",               ["washout", "nocodazole"]),
 (r"speed",                 ["speed", "movement"]),
 (r"phase|prometa|prophase", ["prophase", "prometaphase", "creation phase"]),
 (r"polepole|duration|dur_", ["metaphase duration", "spindle"]),
 (r"measure|traces|excerpt|timestrip|piece|nf9|nf10", []),   # illustrative panels: no prose term expected
]


def sections(md):
    out, cur, buf = {}, None, []
    for line in io.open(md, encoding="utf-8"):
        m = re.match(r"### (Fig \d+) · AB(\d+)", line)
        if m:
            if cur: out[cur] = " ".join(buf)
            cur, buf = m.group(1), []
        elif line.startswith(("## ", "---")):
            if cur: out[cur] = " ".join(buf)      # Results ends here; do not swallow the Discussion
            cur, buf = None, []
        elif cur:
            buf.append(line.strip())
    if cur: out[cur] = " ".join(buf)
    return {k: v.lower() for k, v in out.items()}


def main():
    rows = [l.rstrip("\n").split("\t") for l in io.open(GEOM, encoding="utf-8", errors="replace")]
    H = {c: i for i, c in enumerate(rows[0])}
    def g(r, c):
        i = H[c]; return r[i] if i < len(r) else ""
    placed, titles = collections.defaultdict(list), collections.defaultdict(list)
    for r in rows[1:]:
        if len(r) < 6: continue
        if g(r, "kind") == "PlacedItem":
            placed[g(r, "ab_centre")].append(g(r, "name"))
        if g(r, "kind") == "TextFrame" and len(g(r, "name")) > 55:
            try: T = float(g(r, "T"))
            except Exception: T = -1e9
            titles[g(r, "ab_centre")].append((T, g(r, "name")))

    S = sections(TEXT)
    L = ["# Does the Results text still cover the publication deck? — 2026-08-21", "",
         "Built by `dataops/coverage_text_vs_deck.py` from the read-only geometry dump of",
         "`META_FIGURES_20260814_PUBLICATION_20260820.ai` (deck untouched — halt is on).", "",
         "A **HIT** means the section plausibly covers that panel. Only the misses below need your attention.", ""]

    blockers, orphans = [], []
    for ab in sorted(AB_FIG, key=int):
        fig = AB_FIG[ab]
        figs = sorted(placed.get(ab, []))
        txt  = S.get(fig, "")
        tt   = sorted(titles.get(ab, []), reverse=True)
        L.append(f"## {fig} · artboard {ab} — {len(figs)} figures placed, {len(txt.split())} words of text")
        for T, n in tt[:2]:
            L.append(f"  - title on board: *{n.strip()}*")
        if not figs:
            L.append(f"  - 🔴 **the section has text but the artboard carries NO artwork.**")
            blockers.append((fig, ab, tt[0][1].strip() if tt else ""))
        if not txt:
            L.append(f"  - 🔴 **no text section for this figure.**")
        miss = []
        for n in figs:
            terms = []
            for pat, tl in TOPIC:
                if re.search(pat, n, re.I): terms = tl; break
            else:
                terms = []
            if terms and not any(t in txt for t in terms):
                miss.append(n)
        if miss:
            L.append(f"  - ⚠ placed but nothing in this section refers to it ({len(miss)}):")
            for n in sorted(set(miss)): L.append(f"      · {n}")
            orphans += [(fig, n) for n in miss]
        L.append("")

    stray = placed.get("0", []) + placed.get("", [])
    if stray:
        L += ["## Off-board", "",
              "Placed on the pasteboard, so it prints on no figure:", ""]
        for n in sorted(stray): L.append(f"  - 🔴 `{n}`")
        L.append("")

    dup = collections.defaultdict(list)
    for ab, tl in titles.items():
        for _, n in tl:
            m = re.match(r"\s*(Fig(?:ure)? \d+)", n)
            if m: dup[m.group(1).replace("Figure", "Fig")].append(ab)
    clash = {k: sorted(set(v)) for k, v in dup.items() if len(set(v)) > 1}
    if clash:
        L += ["## Figure numbers that appear on more than one artboard", "",
              "Each artboard carries an old title and a new one; these numbers are claimed twice, so the",
              "callouts in the text cannot be resolved until the stale title is deleted.", ""]
        for k, v in sorted(clash.items()): L.append(f"  - **{k}** → artboards {', '.join(v)}")
        L.append("")

    # An artboard can be empty for two very different reasons: she PLANNED a figure and has not built it,
    # or she MERGED its content into another board and the title is a leftover. Those need opposite actions,
    # so decide it from evidence: does another board's title now contain this board's sentence?
    if blockers:
        L += ["## Why are those two artboards empty? (tested, not assumed)", "",
              "For each empty board, the longest run of its title's words that also appears in ANOTHER",
              "board's title. A long run means its content was folded into that board and the title is stale;",
              "a short run means it is a figure you planned and have not built yet.", ""]
        for fig, ab, t in blockers:
            w = re.sub(r"^\s*Fig(ure)? \d+:\s*", "", t).lower().split()
            best = (0, None, "")
            for ab2, tl2 in titles.items():
                if ab2 == ab: continue
                for _, n2 in tl2:
                    h = re.sub(r"\s+", " ", n2.lower())
                    for i in range(len(w)):
                        for j in range(len(w), i + 3, -1):
                            if " ".join(w[i:j]) in h:
                                if j - i > best[0]: best = (j - i, ab2, " ".join(w[i:j]))
                                break
            L.append(f"- **{fig} (AB{ab})** — longest shared run: **{best[0]} words** with artboard {best[1]}")
            if best[0] >= 8:
                L.append(f"    - matched text: *\u201c{best[2]}\u201d*")
                L.append(f"    - reads as **MERGED into AB{best[1]}** — the empty board is a leftover; delete its title.")
            else:
                L.append(f"    - no substantial overlap, so this reads as a figure you **planned and have not built**.")
        L.append("")

    L += ["## Summary", "",
          f"- artboards with text but no artwork: **{len(blockers)}**"]
    for f, ab, t in blockers: L.append(f"    - {f} (AB{ab}) — {t}")
    L.append(f"- placed figures no sentence refers to: **{len(orphans)}**")
    L.append(f"- figures on the pasteboard: **{len(stray)}**")
    io.open(OUT, "w", encoding="utf-8").write("\n".join(L) + "\n")
    print("\n".join(L[-14:]))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    sys.exit(main())
