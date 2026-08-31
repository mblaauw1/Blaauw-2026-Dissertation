"""Identify every strip she pasted, by exhaustive BURNED-IN TIMESTAMP matching.

BUG FIXED FIRST: strips written through `ts_render.emit`'s aligned path store their frame times under
`ablation` + `monitoring`, while others store a flat `times` list. Reading only `times` silently skipped
every `nf9_`/`nf10_` strip -- i.e. most of the ones she pasted. Both shapes are unioned now.
"""
import glob, json, os
SC = {}
for p in glob.glob("ablation_figures_20260625/group1/timestrips2/*_frames.json") + \
         glob.glob("ablation_figures_20260625/group4/*_frames.json"):
    try: j = json.load(open(p))
    except Exception: continue
    ts = []
    for k in ("times", "ablation", "monitoring"):
        ts += [float(x) for x in (j.get(k) or [])]
    if ts:
        SC[os.path.basename(p)[:-len("_frames.json")]] = (sorted(set(ts)), j.get("batch"))
print(f"{len(SC)} strip sidecars indexed (was 38 reading only `times`)\n")

def sgn(t):
    neg = t.startswith("-"); m, s = t.lstrip("-").split(":")
    v = int(m)*60 + int(s)
    return -v if neg else v

Q = {
 "p6  unmodified-cell strip":  ["13:04","14:04","21:04","25:04","44:04","48:04"],
 "p7  hec1/mad1 3-channel":    ["1:25","7:22","15:04"],
 "p8  thumb A (small)":        ["-0:06","-0:03","0:14"],
 "p9/p12 zoom+mon 5:00..31:26":["-0:06","-0:03","0:17","5:00","10:54","15:50","21:11","23:50","26:26","31:26"],
 "p10/p14 zoom+mon 2:01..34:21":["-0:06","-0:03","0:14","2:01","7:01","23:21","28:21","34:21"],
 "p13 item-12 strip":          ["2:40","2:43","3:07","4:09","10:48","17:27","24:06","30:45","39:36"],
}
for label, times in Q.items():
    want = [sgn(t) for t in times]
    sc = []
    for nm, (ts, b) in SC.items():
        hit = sum(1 for w in want if any(abs(w-t) <= 3.0 for t in ts))
        if hit: sc.append((hit, nm, b, len(ts)))
    sc.sort(reverse=True)
    print(f"{label}   ({len(want)} timestamps)")
    for h, nm, b, n in sc[:3]:
        tag = "  <== ALL MATCH" if h == len(want) else ""
        print(f"    {h}/{len(want)}  {nm[:64]:66s} [{b}]{tag}")
    if not sc: print("    nothing matched")
    print()
