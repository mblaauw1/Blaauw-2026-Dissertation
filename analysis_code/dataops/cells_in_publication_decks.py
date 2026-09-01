#!/usr/bin/env python3
"""Which CELLS appear as imagery (timestrips / frame captures) on the two PUBLICATION decks.

HER 2026-08-21: *"can you make a list of all of the cells that appear in either frame captures or timestrips
in (1) the main figure and (2) the supplemental (publish versions of each)?"*

IMAGERY ONLY. A violin plot draws on 80 cells but shows none of them; what she is asking for is the cells a
reader actually SEES. So a figure counts here only if it is a rendered frame or strip, decided by the
figure's own provenance rather than by its name: `PLOT_SETTINGS.json` records a `type`/`kind` for most, and
the timestrip builders all record a `batch`. Name parsing is the last resort and is reported as such, so a
guessed identification can never be mistaken for a recorded one.

Output: one table per deck, per ARTBOARD, with the batch, how it was identified, and the figure it came from.
"""
import collections, io, json, os, re, sys

ROOT = "/Volumes/4 MB"
GEOM = {"main (META_FIGURES_20260814_PUBLICATION_20260820.ai)": f"{ROOT}/_claude_tmp/geom9_pub0814.tsv",
        "supplemental (META_FIGURES_20260813_supplemental_PUBLICATION_20260820.ai)": f"{ROOT}/_claude_tmp/geom9_pub0813.tsv"}
OUT  = f"{ROOT}/4_TABLES_AND_REPORTS/CELLS_SHOWN_ON_PUBLICATION_DECKS_20260821.md"

PS = json.load(io.open(f"{ROOT}/ablation_plots/PLOT_SETTINGS.json", encoding="utf-8"))

# a figure is IMAGERY if its recorded type says so, or its name is one of the strip families
# NOT "panel of": every split PLOT panel carries "Panel 3 of 8 from ..." in its caption, and a panel
# of a violin is still a violin. Imagery is decided by what the figure SHOWS.
IMAGERY_TYPE = re.compile(r"timestrip|excerpt|kymograph|montage|raster|frame capture", re.I)
IMAGERY_NAME = re.compile(r"^(nf9_|nf10_|G5_mad1_timestrip|G5_item4_hec1_timestrip|G9_drug_timestrip|"
                          r"G3_slippage_timestrip|G4_polar_timestrip|AB5_EXCERPT|G1_measure|G7kymo|G8kymo|"
                          r"traced_cell)", re.I)

# batches, longest first, so "…ablation_18" never matches inside "…ablation_180"
MASTER = []
raw = io.open(f"{ROOT}/ABLATION_MASTER.csv", encoding="utf-8-sig", errors="replace").read().splitlines()
hi = next(i for i, l in enumerate(raw) if l.startswith("Batch Name,"))
import csv as _csv
MROWS = {r["Batch Name"].strip(): r for r in _csv.DictReader(raw[hi:]) if (r.get("Batch Name") or "").strip()}
MASTER = sorted(MROWS, key=len, reverse=True)


def batch_of(fig):
    """(batch, how). Recorded provenance first; the figure's name only as a labelled fallback."""
    e = PS.get(fig) or {}
    for src in (e.get("settings") or {}, e):
        if isinstance(src, dict):
            b = src.get("batch")
            if isinstance(b, str) and b.strip():
                return b.strip(), "recorded"
    cap = (e.get("caption") or "")
    for b in MASTER:
        if b in cap:
            return b, "caption"
    # THE BUILDER BURNS THE BATCH INTO THE TITLE, and the PUBLICATION render strips titles -- so the working
    # PDF still carries it when the publication twin does not. `G1_measure_*` has no recorded batch at all
    # (its builder takes MEAS_BATCH from the environment), and this is the only place the four variants'
    # cells are written down: traces = 20250401 ptk_yfpcdc20_28, coll3 = 20250923 triple_ablation_collagen_25,
    # triple3 = 20251029 triple_ablation_23, plain = 20250901 triple_ablation_11.
    wp = f"{ROOT}/ablation_figures_20260625/_ai_relink/pdf/{fig}.pdf"
    if os.path.isfile(wp):
        import subprocess as _sp
        try:
            t = _sp.run(["pdftotext", "-q", wp, "-"], capture_output=True, text=True, timeout=25).stdout
            t = re.sub(r"\s+", " ", t)
            for b in MASTER:
                if b in t:
                    return b, "figure title"
        except Exception:
            pass
    # AB5 excerpts are CROPS of a named source strip; the map lives in the excerpt builder, so read it there
    # rather than restating it (one source of truth).
    if fig.startswith("AB5_EXCERPT"):
        try:
            src = io.open(f"{ROOT}/ablation_figures_20260625/custom_ab5_excerpts_20260817.py",
                          encoding="utf-8").read()
            m = re.search(r'"' + re.escape(fig) + r'":\s*\("([^"]+)"', src)
            if m:
                stem = m.group(1)
                for b in MASTER:
                    if b in stem or b.replace(" ", "_") in stem:
                        return b, "excerpt source strip"
        except Exception:
            pass
    # The Hec1/Mad1 strips are named by an `xy` TAG (`..._xy5`), not by batch, and their builder is the only
    # place the tag is tied to a cell. Read it from the docstring where that mapping is written down.
    m = re.match(r"G5_item4_hec1_timestrip_(xy\d+)$", fig)
    if m:
        # the builder's docstring writes the cell with a leading ellipsis ("...Hec1halo_640_4_xy5"), so the
        # full batch string never appears in the source. Resolve the tag against master instead, and only
        # accept it when exactly ONE Hec1 batch carries that tag -- an ambiguous tag stays unidentified.
        # The tag alone is not unique -- 4 Hec1 batches end in `_xy5`. The builder's docstring lists each
        # strip as "...Hec1halo_640_4_xy5", i.e. the ellipsis hides only the date prefix, so the fragment
        # after it IS distinctive. Match on that, and still require a unique hit.
        try:
            src = io.open(f"{ROOT}/ablation_figures_20260625/group5_hec1_timestrip.py",
                          encoding="utf-8").read()
            frags = re.findall(r"\.\.\.\s*([A-Za-z0-9_]*" + re.escape(m.group(1)) + r")\b", src)
            for fr in frags:
                cand = [b for b in MASTER if b.lower().endswith(fr.lower())]
                if len(cand) == 1:
                    return cand[0], "builder docstring fragment"
        except Exception:
            pass
    # A SPLIT PANEL of a per-cell example figure shows ONE cell: panel N is row N of the parent's data.
    m = re.match(r"(.+?)__p(\d+)$", fig)
    if m and os.path.isfile(f"{ROOT}/ablation_plots/data/{m.group(1)}.csv"):
        try:
            rows = list(_csv.DictReader(io.open(f"{ROOT}/ablation_plots/data/{m.group(1)}.csv",
                                                encoding="utf-8", errors="replace")))
            i = int(m.group(2)) - 1
            if rows and "batch" in rows[0] and 0 <= i < len(rows):
                return rows[i]["batch"].strip(), "parent data row"
        except Exception:
            pass
    # name fallback: strip the family prefix, then match the longest known batch inside what is left,
    # allowing the underscore-for-space spelling the filenames use
    stem = re.sub(r"__piece\d+$", "", fig)
    flat = stem.replace("_", " ")
    for b in MASTER:
        if b in stem or b.replace(" ", "_") in stem or b in flat:
            return b, "name"
    return None, "unidentified"


def read(path):
    rows = [l.rstrip("\n").split("\t") for l in io.open(path, encoding="utf-8", errors="replace")]
    H = {c: i for i, c in enumerate(rows[0])}
    def g(r, c):
        i = H[c]; return r[i] if i < len(r) else ""
    out = collections.defaultdict(set)
    for r in rows[1:]:
        if len(r) < 6 or g(r, "kind") != "PlacedItem": continue
        name = re.sub(r"__piece\d+$", "", g(r, "name"))
        e = PS.get(name) or {}
        t = " ".join(str(v) for v in ((e.get("settings") or {}).get("type", ""),
                                      (e.get("settings") or {}).get("kind", ""),
                                      e.get("caption", "")))
        if not (IMAGERY_NAME.match(name) or IMAGERY_TYPE.search(t)): continue
        out[g(r, "ab_centre")].add(name)
    return out


def main():
    L = ["# Cells shown as imagery on the publication decks — 2026-08-21", "",
         "Every cell a reader actually SEES: timestrips, frame captures, excerpts and kymographs. Plots are",
         "excluded — a violin draws on many cells but shows none of them.", "",
         "`how` says where the identification came from: **recorded** = the figure's own `batch` in",
         "`PLOT_SETTINGS.json`; **caption** = its recorded caption; **name** = parsed from the filename, the",
         "weakest form and flagged so it is never mistaken for provenance.", ""]
    grand = {}
    for label, path in GEOM.items():
        if not os.path.isfile(path):
            L += [f"## {label}", "", "_geometry dump not found_", ""]; continue
        per = read(path)
        cells = {}
        L += [f"## {label}", ""]
        for ab in sorted(per, key=lambda x: int(x) if x.isdigit() else 99):
            figs = sorted(per[ab])
            L.append(f"### artboard {ab} — {len(figs)} imagery figures")
            L.append("")
            L.append("| cell (batch) | how | figure |")
            L.append("|---|---|---|")
            for f in figs:
                b, how = batch_of(f)
                L.append(f"| {b or '**unidentified**'} | {how} | `{f}` |")
                if b: cells.setdefault(b, []).append(f)
            L.append("")
        L += [f"**Distinct cells on this deck: {len(cells)}**", ""]
        for b in sorted(cells):
            m = MROWS.get(b, {})
            sis = (m.get("# Sisterless KTs") or "?").strip()
            ph = (m.get("Phase of Ablations") or "?").strip()
            tg = (m.get("On-Target / Off-Target") or "?").strip()
            L.append(f"- `{b}` — {sis}-sisterless · {ph} · {tg} · in {len(cells[b])} figure(s)")
        L.append("")
        grand[label] = cells

    if len(grand) == 2:
        a, b = list(grand.values())
        both = sorted(set(a) & set(b))
        L += ["## Cells shown on BOTH decks", ""]
        L += ([f"- `{x}`" for x in both] if both else ["- none"])
        L += ["", f"**Total distinct cells across both decks: {len(set(a) | set(b))}**", ""]
    io.open(OUT, "w", encoding="utf-8").write("\n".join(L) + "\n")
    for k, v in grand.items():
        print(f"{k}: {len(v)} distinct cells")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    sys.exit(main())
