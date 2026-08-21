#!/usr/bin/env python3
"""Clear overlaps on the publication deck by moving MY figures only, as little as possible.

HER 2026-08-21: *"should be able to maintain figure placement as you swap stuff out or do corrections"* and
*"should be able to do both"* -- i.e. her arrangement is the thing to preserve, and correcting a figure's
proportions must not cost her that arrangement.

Restoring her 08-20 layout while fixing the stretched heights left 21 overlaps: a figure whose height was
wrong is a different height once corrected, so it no longer fits the slot it used to. Every one of those 21
pairs involves a figure on one of MY `session_*` layers, so all of them can be cleared without touching
anything she placed.

THE RULE THIS ENCODES: hers never moves. Mine moves the SHORTEST distance that clears the overlap, stays on
its artboard, and is re-checked against every other item -- so nudging one figure cannot create a new
collision somewhere else. If a figure cannot be cleared without leaving the artboard it is reported, never
shoved off-board (NOTES: "never park an item off-board").

Writes a JSX plan; it does not touch the document itself.
"""
import collections, io, json, os, re, sys

ROOT = "/Volumes/4 MB"
GEOM = f"{ROOT}/_claude_tmp/geom9_pub0814.tsv"
OUT  = f"{ROOT}/ablation_plots/RESOLVE_OVERLAPS_20260821.jsx"
PAD  = 6.0          # breathing room left between figures
MIN_FRAC = 0.10     # the same >10% threshold the deck audit uses


def load():
    rows = [l.rstrip("\n").split("\t") for l in io.open(GEOM, encoding="utf-8", errors="replace")]
    H = {c: i for i, c in enumerate(rows[0])}
    def g(r, c):
        i = H[c]; return r[i] if i < len(r) else ""
    art, items = {}, []
    for r in rows[1:]:
        if len(r) < 10: continue
        if g(r, "kind") == "ARTBOARD":
            art[g(r, "ab_centre")] = tuple(float(g(r, x)) for x in ("L", "T", "R", "B"))
        elif g(r, "kind") == "PlacedItem" and g(r, "ab_centre"):
            items.append({"name": g(r, "name"), "ab": g(r, "ab_centre"), "layer": g(r, "layer") or "",
                          "L": float(g(r, "L")), "T": float(g(r, "T")),
                          "R": float(g(r, "R")), "B": float(g(r, "B"))})
    return art, items


def overlap(a, b):
    if a["ab"] != b["ab"]: return 0.0
    x0, x1 = max(a["L"], b["L"]), min(a["R"], b["R"])
    y0, y1 = max(a["B"], b["B"]), min(a["T"], b["T"])
    if x1 <= x0 or y1 <= y0: return 0.0
    inter = (x1 - x0) * (y1 - y0)
    amin = min((a["R"] - a["L"]) * (a["T"] - a["B"]), (b["R"] - b["L"]) * (b["T"] - b["B"]))
    return inter / amin if amin > 0 else 0.0


def fits(art, it):
    aL, aT, aR, aB = art[it["ab"]]
    return it["L"] >= aL - 0.5 and it["R"] <= aR + 0.5 and it["T"] <= aT + 0.5 and it["B"] >= aB - 0.5


def family(name):
    """Pieces of one split strip are ONE rigid object. Moving `__piece3` on its own would slide one band of
    a timestrip out of line with the rest of it -- the exact defect this pass exists to remove."""
    m = re.match(r"(.+)__piece\d+$", name)
    return m.group(1) if m else name


def main():
    art, items = load()
    mine = lambda it: it["layer"].startswith("session_")
    orig = {it["name"]: (it["L"], it["T"]) for it in items}
    moved, stuck = {}, []
    fam = collections.defaultdict(list)
    for it in items: fam[family(it["name"])].append(it)

    def clashes(cand, skip):
        return [o for o in items if o is not skip and overlap(cand, o) > MIN_FRAC]

    # SPIRAL SEARCH, not escape-one-partner. Trying to clear a single overlapping neighbour produced 970pt
    # jumps -- it cleared that neighbour and then had to keep going to clear everything it landed on. Instead
    # search offsets outward from the figure's OWN position and take the first that clears everything, so the
    # move is the smallest that works and "maintain figure placement" means what she said it means.
    # A figure that was NOT in her 08-20 layout (the kymographs, the collagen variants) has no placement of
    # hers to preserve, so it may search the whole artboard rather than a tight spiral. Anything that WAS in
    # her layout stays within LIMIT of where she put it.
    import io as _io
    _snap = f"{ROOT}/_claude_tmp/idfigs_snapshot/20260820_141516/geom_pub0814.tsv"
    HERS = set()
    if os.path.isfile(_snap):
        _r = [l.rstrip("\n").split("\t") for l in _io.open(_snap, encoding="utf-8", errors="replace")]
        _H = {c: i for i, c in enumerate(_r[0])}
        for _x in _r[1:]:
            if len(_x) >= 6 and _x[_H["kind"]] == "PlacedItem": HERS.add(_x[_H["name"]])
    STEP, LIMIT, FREE = 12.0, 420.0, 5200.0
    offsets = [(0.0, 0.0)]
    r = STEP
    while r <= LIMIT:
        for dx, dy in ((0, r), (0, -r), (r, 0), (-r, 0), (r, r), (r, -r), (-r, r), (-r, -r)):
            offsets.append((float(dx), float(dy)))
        r += STEP
    offsets.sort(key=lambda d: abs(d[0]) + abs(d[1]))
    wide = [(0.0, 0.0)]
    r = STEP
    while r <= FREE:
        for dx, dy in ((0, r), (0, -r), (r, 0), (-r, 0), (r, r), (r, -r), (-r, r), (-r, -r)):
            wide.append((float(dx), float(dy)))
        r += STEP
    wide.sort(key=lambda d: abs(d[0]) + abs(d[1]))

    for _round in range(200):
        bad = None
        for i in range(len(items)):
            for j in range(i + 1, len(items)):
                if overlap(items[i], items[j]) > MIN_FRAC:
                    bad = (items[i], items[j]); break
            if bad: break
        if not bad: break
        a, b = bad
        if mine(a) and not mine(b): mover = a
        elif mine(b) and not mine(a): mover = b
        elif mine(a) and mine(b): mover = a if (a["R"] - a["L"]) <= (b["R"] - b["L"]) else b
        else:
            stuck.append((a["name"], "both figures are YOURS — not moved")); break
        grp = fam[family(mover["name"])]                    # move the WHOLE strip, never one band of it
        placed = False
        # hers -> tight spiral; mine-and-new -> the whole board
        _off = offsets if any(m["name"] in HERS for m in grp) else wide
        for dx, dy in _off:
            trials = []
            ok = True
            for m in grp:
                b0 = orig[m["name"]]
                w, h = m["R"] - m["L"], m["T"] - m["B"]
                t = dict(m); t.update(L=b0[0] + dx, R=b0[0] + dx + w, T=b0[1] + dy, B=b0[1] + dy - h)
                if not fits(art, t): ok = False; break
                trials.append((m, t))
            if not ok: continue
            others = [o for o in items if o not in grp]
            if any(overlap(t, o) > MIN_FRAC for _, t in trials for o in others): continue
            for m, t in trials:
                m.update(t); moved[m["name"]] = (round(dx, 2), round(dy, 2))
            placed = True; break
        if not placed:
            stuck.append((family(mover["name"]),
                          f"no free position on artboard {mover['ab']} clears it (as a whole strip)"))
            items = [x for x in items if x not in grp]

    left = sum(1 for i in range(len(items)) for j in range(i + 1, len(items))
               if overlap(items[i], items[j]) > MIN_FRAC)
    print(f"moved {len(moved)} of MY figures; overlaps remaining among the solved set: {left}")
    if stuck:
        print(f"COULD NOT CLEAR {len(stuck)} (left exactly where they are, reported not shoved):")
        for n, why in stuck: print(f"   {n[:56]:58s} {why}")
    for n, (dx, dy) in sorted(moved.items(), key=lambda kv: -abs(kv[1][0]) - abs(kv[1][1]))[:10]:
        print(f"   {n[:56]:58s} dx={dx:+8.1f} dy={dy:+8.1f}")

    ent = "\n".join('M["%s"]={dx:%s,dy:%s};' % (n, d[0], d[1]) for n, d in moved.items())
    jsx = '''// Clear the overlaps left by restoring her layout with corrected heights -- moving only MY figures.
// Generated by dataops/resolve_overlaps_minimal.py. Nothing on her layers is touched.
#target illustrator
var _u = app.userInteractionLevel; app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS;
var LOG=[]; var PATH="/Volumes/4 MB/1_DECKS/META_FIGURES_20260814_PUBLICATION_20260820.ai";
var doc=null;
for (var d=0; d<app.documents.length; d++) if (app.documents[d].fullName.fsName===PATH) { doc=app.documents[d]; break; }
if (doc===null) doc=app.open(new File(PATH));
app.activeDocument=doc;
var placed=[];
function collect(c){for(var i=0;i<c.pageItems.length;i++){var it=c.pageItems[i];
 if(it.typename==="PlacedItem")placed.push(it); else if(it.typename==="GroupItem")collect(it);}}
collect(doc);
function idOf(it){var n="";try{if(it.file)n=decodeURI(it.file.name).replace(/\\.pdf$/i,"");}catch(e){}
 if(!n){try{n=it.name;}catch(e2){}}return n;}
var M={};
''' + ent + '''
var n=0;
for (var p=0;p<placed.length;p++){var id=idOf(placed[p]);
 if(!M.hasOwnProperty(id))continue;
 placed[p].left=placed[p].left+M[id].dx; placed[p].top=placed[p].top+M[id].dy; n++;}
LOG.push("nudged "+n+" of my figures to clear overlaps; her placements untouched");
if(n>0){var o=new IllustratorSaveOptions();o.pdfCompatible=false;doc.saveAs(new File(PATH),o);LOG.push("SAVED");}
app.userInteractionLevel=_u;
var f=new File("/Volumes/4 MB/_claude_tmp/RESOLVE_OVERLAPS_20260821.log");
f.open("w");f.write(LOG.join("\\n"));f.close();
LOG.join("\\n");
'''
    io.open(OUT, "w", encoding="utf-8").write(jsx)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    sys.exit(main())
