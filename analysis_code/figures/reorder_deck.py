"""#13a — Reorder deck.py GROUPS into the paper's narrative sequence (matches the writeup story order).
Programmatic: extracts every existing (img,cap) slide, re-buckets by theme, rewrites GROUPS. No slide or
caption is edited or lost (asserts count in == count out). Backs up deck.py first."""
import re, shutil, os
ROOT="/Volumes/4 MB/ablation_figures_20260625"
src=open(f"{ROOT}/deck.py").read()
ns={}; m=re.search(r'GROUPS=(\[.*?\n\])\n',src,re.S); exec("GROUPS="+m.group(1),ns)
OLD=ns["GROUPS"]
slides=[]; placeholders=[]
for g in OLD:
    for s in g.get("slides",[]):
        if s.get("img"): slides.append(s)
        else: placeholders.append(s)
N=len(slides)

# narrative themes (order = paper story); each = (title, color, [substrings]). First match wins, so order matters.
THEMES=[
 ("1 · Unperturbed mitosis & ablation examples","1b7837",
   ["timestrips2/unmanipulated","timestrips2/traced_cell","timestrips2/1-sisterless","timestrips2/2-sisterless","timestrips2/3-sisterless","timestrips2/off-target","timestrips2/double","frap_timestrips"]),
 ("2 · Ablation validation — targeted-KT loss & (no) recovery","2166ac",
   ["ablation_intensity","ablation_individual","frap_both","frap_individual","G4_frap","prepost_intensity"]),
 ("3 · Sisterless-KT phenotype — metaphase duration","762a83",
   ["violin2","violin1","G1_survival","G1_statgrid","roundness","area","start_rounded","exhaustion_violin","exhaustion_statgrid","duration_combined"]),
 ("4 · Timing & phase dependence of the delay","b35806",
   ["phase_split","metaphase_ablated","metaphase_dynamics","abl_to_meta","prophase_dynamics"]),
 ("5 · K–K distance & chromosome length","1b5e20",
   ["kk_distance","chromo_length"]),
 ("6 · Pole localization, congression & KT fate","d6604d",
   ["kt_fate","origin_position","edge_distance","pole_time","plate_join","congression","polar_timestrip"]),
 ("7 · KT dynamics — distance-to-plate, oscillation, velocity, intensity","4a148c",
   ["plate_distance","oscillation","velocity","kt_intensity_time"]),
 ("8 · Polar / lagging chromosomes at anaphase","d95f02",
   ["lagging","polar_bar","neither_bar","polar_lagging"]),
 ("9 · Drug controls — nocodazole & ZM (not slippage)","6e6e6e",
   ["nocodazole","G4_zm"]),
 ("10 · eYFP-Cdc20 retention & cell fluorescence","1f77b4",
   ["cdc20","distance_vs_fluor","fluor_over_time","fluor_vs_duration"]),
 ("11 · Mad1 / IF (SAC marker)","999999",
   ["G5_IF","mad1hec1","G5_"]),
]
def theme_of(img):
    b=img.lower()
    for ti,(title,col,subs) in enumerate(THEMES):
        if any(s.lower() in b for s in subs): return ti
    return len(THEMES)  # "Other"
buckets={}
for s in slides: buckets.setdefault(theme_of(s["img"]),[]).append(s)

NEW=[]
for ti,(title,col,subs) in enumerate(THEMES):
    if buckets.get(ti): NEW.append({"n":ti+1,"title":title,"color":col,"slides":buckets[ti]})
if buckets.get(len(THEMES)):
    NEW.append({"n":len(THEMES)+1,"title":"12 · Other figures","color":"888888","slides":buckets[len(THEMES)]})
if placeholders:
    NEW.append({"n":len(NEW)+1,"title":"Mad1 Expression (Placeholders)","color":"cccccc","slides":placeholders})

got=sum(len(g["slides"]) for g in NEW)
assert got==N+len(placeholders), f"slide count mismatch! in={N+len(placeholders)} out={got}"
print(f"reordered {N} plot slides + {len(placeholders)} placeholders into {len(NEW)} narrative sections; none lost")

# serialize NEW as a Python literal and splice back into deck.py
import json
def pyify(groups):
    out="[\n"
    for g in groups:
        out+=" {"+f'"n":{g["n"]},"title":{json.dumps(g["title"],ensure_ascii=False)},"color":{json.dumps(g["color"],ensure_ascii=False)},"slides":['
        out+=", ".join(json.dumps(s,ensure_ascii=False) for s in g["slides"])
        out+="]},\n"
    out+="]"
    return out
_repl="GROUPS="+pyify(NEW)+"\n"
new_src=re.sub(r'GROUPS=\[.*?\n\]\n', lambda _:_repl, src, count=1, flags=re.S)
shutil.copy(f"{ROOT}/deck.py", f"{ROOT}/deck.py.bak_pre_reorder_20260701")
open(f"{ROOT}/deck.py","w").write(new_src)
import ast; ast.parse(new_src)   # verify still valid python
print("deck.py reordered + syntax OK (backup: deck.py.bak_pre_reorder_20260701)")
