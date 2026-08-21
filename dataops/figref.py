#!/usr/bin/env python3
"""Identify a figure two ways, so troubleshooting never starts with "which one do you mean?".

USER 2026-08-18: "i want to just be able to copy and paste ones im talking about into terminal here or
refer to them by the assigned letter+artboard+ai file ... and you'll know exactly what im talking about"

    python3 dataops/figref.py index                 # (re)build the reference table from the deck dumps
    python3 dataops/figref.py resolve 4B            # -> the figure at panel B, artboard 4, main deck
    python3 dataops/figref.py resolve "0813supp 2A"
    python3 dataops/figref.py identify shot.png     # -> which figure that image IS, by pixel match
    python3 dataops/figref.py show G4_lagging_bar   # -> every path, deck placement and builder for it

PANEL LETTERS are assigned per ARTBOARD in published-paper reading order: banded into rows top-to-bottom,
then left-to-right within a row, A, B, C, ... That is the convention a reader expects, and it is
recomputed from geometry each time, so moving a figure on the board renumbers it rather than going stale.
"""
import argparse, csv, io, json, os, re, subprocess, sys, glob, collections

R    = "/Volumes/4 MB"
FIG  = R + "/ablation_figures_20260625"
PDF  = FIG + "/_ai_relink/pdf"
PUB  = FIG + "/_ai_relink/pdf_pub"
OUT  = R + "/ablation_plots/FIGURE_REFERENCE.csv"
THUMB= R + "/_claude_tmp/figthumbs"

DECKS = {                      # short key -> (dump tag, deck file)
    "0814":     ("0814",     "META_FIGURES_20260814.ai"),
    "0813supp": ("0813supp", "META_FIGURES_20260813_supplemental.ai"),
    "newfig":   ("newfig",   "NEW_FIGURES_20260804.ai"),
    "supp":     ("supp",     "supplemental.ai"),
    "newts":    ("newts",    "NEW_TIMESTRIPS_20260804.ai"),
}
DEFAULT_DECK = "0814"          # "4B" with no deck means the main figure doc
ALIASES = {"main":"0814","meta":"0814","0814supp":"0813supp","supplemental":"supp",
           "new":"newfig","timestrips":"newts","0813":"0813supp"}

def _rows(tag):
    p = f"{R}/_claude_tmp/geom9_{tag}.tsv"
    if not os.path.exists(p): return []
    out=[]
    for ln in io.open(p,encoding="utf-8",errors="replace").read().replace("\r","\n").split("\n"):
        f=ln.split("\t")
        if len(f)>11 and f[0]=="PlacedItem" and f[5] and "hidden" not in (f[4] or ""):
            try: out.append(dict(name=f[5],ab=f[1],L=float(f[6]),T=float(f[7]),
                                 Rr=float(f[8]),B=float(f[9]),layer=f[10],link=f[11].strip()))
            except Exception: pass
    return out

def letters(n):
    """A..Z, then AA, AB, ... so a dense artboard never runs out."""
    s=""; n+=1
    while n: n,r = divmod(n-1,26); s = chr(65+r)+s
    return s

def build_index():
    recs=[]
    for key,(tag,deck) in DECKS.items():
        rows=_rows(tag)
        by=collections.defaultdict(list)
        for r in rows: by[r["ab"]].append(r)
        for ab,items in by.items():
            # band into rows: a new row starts when the top drops by more than 55% of the median height
            items.sort(key=lambda r:-r["T"])
            hs=sorted(abs(r["T"]-r["B"]) for r in items) or [1]
            tol=max(hs[len(hs)//2]*0.55, 40)
            bands=[]; cur=[]
            for r in items:
                if cur and abs(cur[-1]["T"]-r["T"])>tol: bands.append(cur); cur=[]
                cur.append(r)
            if cur: bands.append(cur)
            i=0
            for band in bands:
                band.sort(key=lambda r:r["L"])          # left to right within the row
                for r in band:
                    recs.append(dict(ref=f"{ab}{letters(i)}", deck=key, deck_file=deck, artboard=ab,
                                     letter=letters(i), figure=r["name"], layer=r["layer"],
                                     left=round(r["L"],1), top=round(r["T"],1),
                                     width=round(abs(r["Rr"]-r["L"]),1), height=round(abs(r["T"]-r["B"]),1),
                                     link=r["link"]))
                    i+=1
    recs.sort(key=lambda r:(r["deck"],int(r["artboard"] or 0),r["letter"]))
    hdr=["ref","deck","deck_file","artboard","letter","figure","layer","left","top","width","height","link"]
    with io.open(OUT,"w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=hdr); w.writeheader()
        for r in recs: w.writerow(r)
    print(f"{len(recs)} panels indexed across {len(DECKS)} live decks -> {OUT}")
    for k in DECKS:
        n=sum(1 for r in recs if r["deck"]==k)
        boards=sorted({r["artboard"] for r in recs if r["deck"]==k}, key=lambda x:int(x or 0))
        print(f"   {k:10s} {n:4d} panels on artboards {boards}")
    return recs

def load():
    if not os.path.exists(OUT): return build_index()
    return list(csv.DictReader(io.open(OUT,encoding="utf-8")))

def parse_ref(q):
    """'4B' | '0813supp 2A' | 'AB4 B' | '4B on 0814' -> (deck, artboard, letter)"""
    q=q.strip()
    deck=DEFAULT_DECK
    for k in list(DECKS)+list(ALIASES):
        if re.search(rf"\b{re.escape(k)}\b", q, re.I):
            deck=ALIASES.get(k.lower(),k); q=re.sub(rf"\b{re.escape(k)}\b","",q,flags=re.I); break
    m=re.search(r"(?:AB)?\s*(\d+)\s*([A-Za-z]{1,2})\b", q)
    if not m: return None
    return deck, m.group(1), m.group(2).upper()

def cmd_resolve(q):
    p=parse_ref(q)
    if not p: print(f"could not parse a reference from {q!r}  (try '4B' or '0813supp 2A')"); return 1
    deck,ab,letter=p
    rows=[r for r in load() if r["deck"]==deck and r["artboard"]==ab and r["letter"]==letter]
    if not rows:
        near=[r for r in load() if r["deck"]==deck and r["artboard"]==ab]
        print(f"no panel {letter} on artboard {ab} of {deck}.")
        if near: print("   that artboard has: "+", ".join(sorted(r["letter"] for r in near)))
        return 1
    for r in rows: cmd_show(r["figure"], ref=r)
    return 0

def cmd_show(name, ref=None):
    idx=load()
    hits=[r for r in idx if r["figure"]==name] or [r for r in idx if name.lower() in r["figure"].lower()]
    if not hits and not ref: print(f"'{name}' is not placed on any live deck"); return 1
    fig=(ref or hits[0])["figure"]
    print(f"\n=== {fig}")
    where=[f"{r['deck']}({r['deck_file']}) artboard {r['artboard']} panel {r['letter']}  ->  ref \"{r['artboard']}{r['letter']}\""
           for r in idx if r["figure"]==fig]
    for w in where: print("   placed:", w)
    for label,p in (("working PDF",f"{PDF}/{fig}.pdf"),("publication PDF",f"{PUB}/{fig}.pdf"),
                    ("data CSV",f"{R}/ablation_plots/data/{fig}.csv")):
        print(f"   {label:16s} {'OK ' if os.path.exists(p) else '-- '}{p}")
    png=[p for p in glob.glob(f"{FIG}/**/{fig}.png",recursive=True) if "/_pub/" not in p]
    if png: print(f"   {'rendered PNG':16s} OK {png[0]}")
    try:
        ps=json.load(io.open(R+"/ablation_plots/PLOT_SETTINGS.json",encoding="utf-8",errors="replace"))
        code=(ps.get(fig) or {}).get("code")
        if code:
            base=os.path.basename(code)
            if "__" in base: base=base.split("__",1)[1]
            live=[c for c in (f"{FIG}/{base}",f"{FIG}/figures/{base}") if os.path.exists(c)]
            print(f"   {'builder':16s} {'OK ' if live else '-- '}{live[0] if live else base}")
    except Exception: pass
    return 0

# ---------------------------------------------------------------- image identification
def _thumb(src, dst, px=260):
    try:
        subprocess.run(["sips","-s","format","png","-Z",str(px),src,"--out",dst],
                       capture_output=True,timeout=60)
        return os.path.exists(dst)
    except Exception: return False

def cmd_thumbs():
    os.makedirs(THUMB,exist_ok=True)
    idx=load(); names=sorted({r["figure"] for r in idx})
    made=0
    for n in names:
        d=f"{THUMB}/{n}.png"
        src=f"{PDF}/{n}.pdf"
        if not os.path.exists(src): continue
        if os.path.exists(d) and os.path.getmtime(d)>=os.path.getmtime(src): continue
        if _thumb(src,d): made+=1
    print(f"thumbnails: {made} rebuilt, {len(glob.glob(THUMB+'/*.png'))} total in {THUMB}")

def cmd_identify(path, top=5):
    try:
        import numpy as np
        from PIL import Image
    except Exception as e:
        print("needs pillow+numpy:",e); return 1
    if not os.path.exists(path): print("no such file:",path); return 1
    os.makedirs(THUMB,exist_ok=True)
    if len(glob.glob(THUMB+"/*.png"))==0: cmd_thumbs()
    q=path
    if path.lower().endswith(".pdf"):
        q=f"{THUMB}/_query.png"; _thumb(path,q)
    def vec(p,s=(200,200)):
        im=Image.open(p).convert("L")
        bg=Image.new("L",im.size,255); bg.paste(im); im=bg
        a=np.asarray(im.resize(s),float)
        a=(a-a.mean())/(a.std()+1e-9)
        return a
    Q=vec(q)
    scores=[]
    for p in glob.glob(THUMB+"/*.png"):
        if os.path.basename(p).startswith("_query"): continue
        try: scores.append((float((Q*vec(p)).mean()), os.path.basename(p)[:-4]))
        except Exception: pass
    scores.sort(reverse=True)
    if not scores: print("no thumbnails to match against; run `figref.py thumbs`"); return 1
    idx=load()
    print(f"\nbest matches for {os.path.basename(path)}:")
    for sc,n in scores[:top]:
        refs=[f"{r['artboard']}{r['letter']} on {r['deck']}" for r in idx if r["figure"]==n]
        flag = "  <-- confident" if sc>0.72 and (len(scores)<2 or sc-scores[1][0]>0.08) else ""
        print(f"   {sc:5.3f}  {n:52s} {', '.join(refs)}{flag}")
    if scores[0][0] < 0.45:
        print("\n   ⚠ weak match — this may not be one of the placed figures, or the crop differs a lot.")
    return 0

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("cmd",choices=["index","resolve","identify","show","thumbs"])
    ap.add_argument("arg",nargs="*")
    a=ap.parse_args()
    q=" ".join(a.arg)
    if a.cmd=="index":    return 0 if build_index() else 1
    if a.cmd=="thumbs":   return cmd_thumbs() or 0
    if a.cmd=="resolve":  return cmd_resolve(q)
    if a.cmd=="identify": return cmd_identify(q)
    if a.cmd=="show":     return cmd_show(q)

if __name__=="__main__":
    sys.exit(main() or 0)
