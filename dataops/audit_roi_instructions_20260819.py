"""ITEMS 9 + 10 AUDIT: every ROI instruction she has given, and whether it is in the code.

Her item 9: "There are still cases where i gave you instructions to trim a batch's ROI in a timestrip for
clarity of viewing and you did not ... Go find feedback i gave you regarding changing the ROI for certain
timestrips, then check past work to see if you actually did it, and if you didnt do it, do it."
Her item 10: "for the timestrip below, I'm certain that in past feedback I gave you instructions for
adjusting the ROI placement on the monitoring frames, and you did not implement it here."

METHOD: pull every message in the verbatim feedback record that talks about an ROI / crop / zoom / trim /
shift, pull every batch named in it, and check that batch against the four override tables the renderers
actually read. A batch she gave an ROI instruction for and that appears in NO table is a real gap.
"""
import io, os, re, sys, collections
sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
os.environ.setdefault("CAT_ONLY", "__none__")
import group_timestrips as G
import ts_render, importlib

TABLES = {
    "ROI_UM": getattr(G, "ROI_UM", {}),
    "ROI_UM_FRAMES": getattr(G, "ROI_UM_FRAMES", {}),
    "ZOOM_PANEL_SHIFT_UM": getattr(G, "ZOOM_PANEL_SHIFT_UM", {}),
    "CROP_OFFSETS": getattr(ts_render, "CROP_OFFSETS", {}),
    "MON_USE_ABL_BOX": {b: 1 for b in getattr(G, "MON_USE_ABL_BOX", set())},
    "TIGHT_CROP_UM": getattr(G, "TIGHT_CROP_UM", {}),
}
covered = set()
for t, d in TABLES.items():
    for k in d:
        covered.add(k if isinstance(k, str) else k[0])
print("batches covered by an ROI override table:")
for t, d in TABLES.items():
    print(f"   {t:22s} {len(d):3d} entries")
print(f"   -> {len(covered)} distinct batches\n")

VERB = "/Volumes/4 MB/4_TABLES_AND_REPORTS/_feedback_log/FEEDBACK_VERBATIM.txt"
txt = io.open(VERB, encoding="utf-8", errors="replace").read()
KEY = re.compile(r"\broi\b|\bcrop\b|zoom(ed|ing)?\b|\btrim\b|shift the|move the (roi|frames?)", re.I)
# batch names look like 20250402 ptk_yfpcdc20_22 / 20260420 ptk2 eyfp cdc20 1 ablation_13
BATCH = re.compile(r"\b(20\d{6})[ _]([A-Za-z0-9_ ]{3,60}?)(?=[,.;:\n)]|\s{2,}|$)")
msgs = re.split(r"\n(?=\s*\[\d|\s*\d{2}-\d{2} )", txt)
named = collections.Counter()
for m in msgs:
    if not KEY.search(m):
        continue
    for d, rest in BATCH.findall(m):
        b = f"{d} {rest.strip()}"
        named[b] += 1
print(f"{len(named)} batch-like names appear in ROI/crop/zoom feedback\n")

def known(b):
    """Match on the DATE plus the TRAILING NUMBER, both exactly.

    The obvious substring test is wrong here and gave a false clean bill of health on the first run:
    `20250402 ptk_yfpcdc20_2` "matched" `20250402 ptk_yfpcdc20_22` because one name contains the other.
    That is the same substring trap that broke 177 paths in the reorg and that the deck rename had to dodge.
    A batch is identified by (date, trailing index), so compare exactly that."""
    def key(s):
        s = s.strip().lower()
        m = re.match(r"(20\d{6})", s)
        d = m.group(1) if m else ""
        nums = re.findall(r"_(\d+)(?:_xy(\d+))?\s*$", s) or re.findall(r"[ _](\d+)\s*$", s)
        tail = nums[-1] if nums else ""
        if isinstance(tail, tuple): tail = "_".join(x for x in tail if x)
        return (d, tail)
    kb = key(b)
    if not kb[0]:
        return True                      # not a batch name at all -- a regex artefact
    return any(key(c) == kb for c in covered)

miss = [(b, n) for b, n in named.most_common() if not known(b)]
hit = [(b, n) for b, n in named.most_common() if known(b)]
print(f"COVERED by an override table ({len(hit)}):")
for b, n in hit[:25]: print(f"   {n:2d}x  {b}")
print(f"\nNOT in any override table ({len(miss)}) -- candidates for a missed ROI instruction:")
for b, n in miss[:40]: print(f"   {n:2d}x  {b}")
