"""FRESHNESS-CHAIN VERIFIER (redundancy so a code change always reaches the end products).
For every plot placed in the deck, checks the mtime chain:
    generating-script  <=  PNG  <=  compact-cache JPEG  <=  figure PDF
    generating-script  <=  _ai_relink/pdf (Adobe-linked PDF)
Any STALE link = a change to how the plot is made did NOT propagate to that end product.
Run this after any plot edit; it prints exactly which plots are stale in which end product."""
import os, glob, re, json, datetime
ROOT="/Volumes/4 MB/ablation_figures_20260625"
def mt(p): return os.path.getmtime(p) if os.path.exists(p) else None
def hm(t): return datetime.datetime.fromtimestamp(t).strftime("%m-%d %H:%M") if t else "MISSING"

# 1) which PNGs the deck places (from build_pdfs_feedback.py manifest mutations + deck.py GROUPS)
ns={}; top=open(f"{ROOT}/deck.py").read().split("# ---------------- PPTX")[0]; exec(top,ns)
placed=set()
for g in ns["GROUPS"]:
    for s in g["slides"]:
        if "img" in s: placed.add(s["img"])
build=open(f"{ROOT}/build_pdfs_feedback.py").read()
# apply the SWAPS build_pdfs_feedback.py performs (old placed path -> new path), so we check the ACTUAL
# plots in the final PDF, not deck.py's pre-swap manifest.
for old,new in re.findall(r'swap_img\(\d+,"([^"]+\.png)","([^"]+\.png)"\)', build):
    hit=[p for p in placed if p.endswith(os.path.basename(old))]
    for p in hit: placed.discard(p)
    placed.add(new)
for m in re.findall(r'insert_after\(\d+,"[^"]+","([^"]+\.png)"', build): placed.add(m)
# removals
for m in re.findall(r'remove\(\d+,"([^"]+\.png)"\)', build): placed.discard("group4/"+m); placed.discard(m)
placed={p for p in placed if p.endswith(".png")}
# RETIRED plots (build_pdfs RETIRE list) are archived at the end, NOT regenerated, so their Adobe-relink PDFs
# legitimately stay old — don't require them to be fresh.
_retire=re.findall(r'RETIRE=\[([^\]]*)\]', build)
_retpat=re.findall(r'"([^"]+)"', _retire[0]) if _retire else []
placed={p for p in placed if not any(rp in p for rp in _retpat)}

# 2) map each PNG -> generating script (grep savefig/imwrite of that basename)
scripts=glob.glob(f"{ROOT}/*.py")
def gen_script(png):
    """The script that actually WRITES this PNG: match a savefig/imwrite call whose filename ends in the
    basename (not an incidental mention). Timestrips are written by cv2.imwrite with an f-string path, so
    also accept an imwrite whose path f-string ends in the basename token."""
    base=os.path.basename(png)[:-4]
    pats=[re.compile(r'(?:savefig|imwrite)\([^)]*'+re.escape(base)+r'\.(?:png)'),
          re.compile(r'(?:savefig|imwrite)\(f?"[^"]*/'+re.escape(base)+r'\.png'),
          re.compile(re.escape(base)+r'\}?\.png["\'],')]   # f-string OUT + name
    for s in scripts:
        if os.path.basename(s) in ("verify_freshness.py","build_pdfs_feedback.py","deck.py","deck_compact.py"): continue
        try: t=open(s).read()
        except: continue
        if any(p.search(t) for p in pats): return s
    # timestrips: written as f"{OUT}/{cat}.png" or {b}_frap{si}.png -> map by folder convention
    if "/timestrips2/" in png: return f"{ROOT}/group_timestrips.py"
    if "/frap_timestrips/" in png: return f"{ROOT}/group_frap_timestrips.py"
    return None

pdf=mt(f"{ROOT}/ablation_figures.pdf")
print(f"figure PDF built: {hm(pdf)}\n")
# The compact deck is a CURATED presentation built from deck.py's GROUPS manifest (102 figures);
# the .ai decks place more than that (123). A placed figure that the compact deck was never meant to
# include has no _compact_img entry, and flagging that as "stale cache" is a permanent false positive
# -- it made [B] read 32-45 no matter how many times deck_compact was rebuilt. Scope the cache check
# to the compact manifest and report the remainder separately as informational. (2026-07-29)
import re as _re
try:
    _src = open(f"{ROOT}/deck.py", encoding="utf-8", errors="ignore").read()
    _m = _re.search(r'GROUPS\s*=\s*\[.*?\n\]', _src, _re.S)
    _ns = {}; exec(_m.group(0), _ns)
    COMPACT_SET = {sl[k] for g in _ns['GROUPS'] for sl in g['slides']
                   for k in ('img','image','png','path') if isinstance(sl, dict) and k in sl}
except Exception as _e:
    COMPACT_SET = None
    print(f"   (could not read deck.py GROUPS: {_e} — cache check left unscoped)")

stale_png=[]; stale_cache=[]; stale_ai=[]; nomap=[]; not_in_compact=[]
for png in sorted(placed):
    pp=f"{ROOT}/{png}"; pm=mt(pp)
    if pm is None: nomap.append((png,"PNG MISSING")); continue
    sc=gen_script(png); sm=mt(sc) if sc else None
    if sc and sm and sm>pm+1:                      # script newer than PNG -> edit not re-rendered
        stale_png.append((png,os.path.basename(sc),hm(sm),hm(pm)))
    # compact cache
    if COMPACT_SET is not None and png not in COMPACT_SET:
        not_in_compact.append(png)                 # placed in .ai but outside the curated compact deck
    else:
        cj=f"{ROOT}/_compact_img/"+png.replace("/","__")[:-4]+".jpg"; cm=mt(cj)
        if cm is None or cm<pm-1: stale_cache.append((png,hm(pm),hm(cm)))
        elif pdf and cm>pdf+1: stale_cache.append((png,"cache newer than PDF",hm(pdf)))
    # adobe relink pdf
    ai=f"{ROOT}/_ai_relink/pdf/"+os.path.basename(png)[:-4]+".pdf"; am=mt(ai)
    if am is not None and sm and sm>am+1: stale_ai.append((png,hm(sm),hm(am)))

print(f"=== {len(placed)} plots placed in the deck ===")
print(f"\n[A] SCRIPT NEWER THAN PNG (edit not re-rendered): {len(stale_png)}")
for p,s,sm,pm in stale_png: print(f"   {p}  script({s}) {sm} > png {pm}")
print(f"\n[B] PNG NOT IN THE PDF (compact cache stale/missing): {len(stale_cache)}")
for p,pm,cm in stale_cache: print(f"   {p}  png {pm} cache {cm}")
print(f"\n[C] ADOBE _ai_relink PDF STALE vs script: {len(stale_ai)}")
for p,sm,am in stale_ai: print(f"   {p}  script {sm} > ai-pdf {am}")
print(f"\n[B2] placed in the .ai deck but NOT in the curated compact deck (informational): {len(not_in_compact)}")
for p_ in not_in_compact[:8]: print(f"   {p_}")
print(f"\n[D] PLACED PNG MISSING: {len(nomap)}")
for p,w in nomap: print(f"   {p} {w}")
ok = not(stale_png or stale_cache or stale_ai or nomap)
print(f"\n=== {'ALL FRESH — every change propagated to PDF + Adobe' if ok else 'STALE LINKS FOUND (above) — rebuild needed'} ===")
