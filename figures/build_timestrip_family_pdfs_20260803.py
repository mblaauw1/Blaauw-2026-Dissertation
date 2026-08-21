#!/usr/bin/env python3
"""One PDF per TIMESTRIP FAMILY (user 2026-08-03: "open G5 Mad1, G4 polar, G9 drug, G3 slippage, FRAP").

The big deck PDFs interleave timestrips with plots, and the only timestrips-ONLY collection (the 1,184-page
wide deliverable) is archived on 2 MB. This splits the on-4 MB timestrips into one browsable PDF per family.

SOURCE: `_ai_relink/pdf/<base>.pdf` — the VECTOR PDFs `lib.py`'s savefig monkeypatch emits beside every PNG.
They are the same artefacts the .ai deck links, so these PDFs and the deck can never disagree. Nothing is
re-rendered and nothing is rasterised; pages are concatenated with qpdf.

VARIANTS: `_notext` versions are EXCLUDED — they exist so Illustrator can carry editable type, and they are
unreadable on their own. Each strip's labelled and `_aligned` versions are kept and sorted ADJACENT, so the
two readings of one cell sit on consecutive pages.

Output: /Volumes/4 MB/ablation_plots/timestrips_by_type_20260803/
"""
import os, re, subprocess, sys

ROOT = "/Volumes/4 MB"
PDFDIR = f"{ROOT}/ablation_figures_20260625/_ai_relink/pdf"
OUT = f"{ROOT}/ablation_plots/timestrips_by_type_20260803"

# family -> (output basename, regex on the PDF basename WITHOUT extension)
FAMILIES = [
    ("G5 Mad1",                  "TS_G5_mad1",          re.compile(r"^G5_mad1_timestrip_")),
    ("G4 polar / sisterless",    "TS_G4_polar",         re.compile(r"^G4_polar_timestrip_")),
    ("G9 drug ablation",         "TS_G9_drug_ablation", re.compile(r"^G9_drug_timestrip_")),
    ("G3 drug slippage",         "TS_G3_slippage",      re.compile(r"^G3_slippage_timestrip_")),
    ("FRAP",                     "TS_FRAP",             re.compile(r"^\d{8}_.+_frap\d+(_aligned)?$")),
]


def sort_key(base):
    """group a strip's labelled + _aligned pages together: strip the suffix, then order plain before aligned."""
    stem = base[:-8] if base.endswith("_aligned") else base
    return (stem, 1 if base.endswith("_aligned") else 0)


def main():
    if not os.path.isdir(PDFDIR):
        sys.exit(f"missing {PDFDIR}")
    os.makedirs(OUT, exist_ok=True)
    allbases = sorted(os.path.splitext(f)[0] for f in os.listdir(PDFDIR) if f.lower().endswith(".pdf"))
    made = []
    for label, outname, rx in FAMILIES:
        picks = [b for b in allbases if rx.match(b) and not b.endswith("_notext")]
        picks.sort(key=sort_key)
        if not picks:
            print(f"{label}: NO source PDFs — skipped")
            continue
        dst = f"{OUT}/{outname}.pdf"
        tmp = dst + ".tmp.pdf"
        cmd = ["qpdf", "--empty", "--pages"] + [f"{PDFDIR}/{b}.pdf" for b in picks] + ["--", tmp]
        r = subprocess.run(cmd, capture_output=True, text=True)
        # qpdf exit 3 = warnings only, output is still written
        if r.returncode not in (0, 3) or not os.path.isfile(tmp):
            print(f"{label}: qpdf FAILED rc={r.returncode}\n{r.stderr[-400:]}")
            if os.path.isfile(tmp):
                os.remove(tmp)
            continue
        os.replace(tmp, dst)
        n = subprocess.run(["pdfinfo", dst], capture_output=True, text=True).stdout
        pages = next((l.split()[1] for l in n.splitlines() if l.startswith("Pages:")), "?")
        size = os.path.getsize(dst) / 1e6
        assert str(pages) == str(len(picks)), f"{label}: {pages} pages from {len(picks)} sources"
        print(f"{label:26s} -> {os.path.basename(dst):26s} {pages:>4} pages  {size:6.1f} MB")
        made.append(dst)
    print(f"\n{len(made)} PDFs -> {OUT}")
    return made


if __name__ == "__main__":
    main()
