"""ZM review slideshow — one slide per ZM sample: monitoring + ablation movies + classification/durations,
for manual review. Output: /Volumes/4 MB/_working/_reviews_and_reference/zm_review_20260629/index.html (open in a browser)."""
import sys; sys.path.insert(0,"/Volumes/4 MB/ablation_figures_20260625")
import os, glob, json, html, lib
OUT="/Volumes/4 MB/_working/_reviews_and_reference/zm_review_20260629"; os.makedirs(OUT,exist_ok=True)
data,_=lib.load_master()
zm=[r for r in data if lib.is_drug(r["Batch Name"]) and "zm" in r["Batch Name"].lower()]
def mn(s):
    v=lib.parse_time(s); return f"{v/60:.2f} min" if v is not None else "—"
def rdir(b):
    g=glob.glob(f"/Volumes/4 MB/**/{b}/{b}_frames.json",recursive=True); return os.path.dirname(g[0]) if g else None
def vids(b):
    d=rdir(b)
    if not d: return {}
    out={}
    for k,suf in [("mon phase","_Phase_Monitoring.mp4"),("mon fluor","_Fluor_Monitoring.mp4"),
                  ("abl phase","_Phase_Ablation.mp4"),("abl fluor","_Fluor_Ablation.mp4")]:
        p=f"{d}/{b}{suf}"
        if os.path.isfile(p): out[k]=p
    return out
slides=[]
for r in sorted(zm,key=lambda r:r["Batch Name"]):
    b=r["Batch Name"]; v=vids(b)
    meta=mn(r.get("Anaphase Onset (s)","")) if False else None
    ms=lib.parse_time(r.get("Metaphase Start (s)","")); an=lib.parse_time(r.get("Anaphase Onset (s)",""))
    metad=f"{(an-ms)/60:.2f} min" if (ms is not None and an is not None and an>ms) else "—"
    neb=lib.parse_time(r.get("NEB Time (s)",""))
    promet=f"{(ms-neb)/60:.2f} min" if (neb is not None and ms is not None and ms>neb) else "—"
    info=[("Group",r.get("On-Target / Off-Target","") or "—"),("# Sisterless",r.get("# Sisterless KTs","") or "—"),
          ("# Targets",r.get("# Unique Targets","") or "—"),("Phase of abl",r.get("Phase of Ablations","") or "—"),
          ("Prometaphase (NEB→Meta)",promet),("Metaphase (Meta→Ana)",metad),
          ("Cell Fate",r.get("Cell Fate","") or "—"),("Exclude",r.get("Exclude","") or "—"),("Notes",(r.get("Notes","") or r.get("annotation_notes","") or "—"))]
    vid_html="".join(f'<div class=v><div class=vl>{k}</div><video src="file://{html.escape(p)}" controls loop muted preload=metadata></video></div>' for k,p in v.items()) or "<i>no movies found</i>"
    rows="".join(f"<tr><td>{html.escape(k)}</td><td>{html.escape(str(val))}</td></tr>" for k,val in info)
    slides.append(f'<section><h2>{html.escape(b)}</h2><div class=grid><div class=vids>{vid_html}</div><table>{rows}</table></div></section>')
doc=f"""<!doctype html><meta charset=utf-8><title>ZM review {len(zm)} samples</title>
<style>body{{margin:0;background:#111;color:#eee;font-family:Helvetica,Arial}}
section{{display:none;padding:18px 24px;height:100vh;box-sizing:border-box}}section.on{{display:block}}
h2{{margin:.2em 0;color:#ffcf6b}} .grid{{display:flex;gap:20px}} .vids{{display:flex;flex-wrap:wrap;gap:10px;flex:1}}
.v{{background:#000;border:1px solid #333}} .vl{{font-size:12px;color:#aaa;padding:2px 6px}} video{{width:440px;display:block}}
table{{border-collapse:collapse;font-size:14px;height:fit-content}} td{{border:1px solid #333;padding:4px 10px}} td:first-child{{color:#9cf}}
#hud{{position:fixed;bottom:8px;right:14px;color:#888;font-size:13px}}</style>
<div id=stage>{''.join(slides)}</div><div id=hud></div>
<script>let i=0,S=[...document.querySelectorAll('section')];function show(n){{S[i].classList.remove('on');i=(n+S.length)%S.length;S[i].classList.add('on');hud.textContent=(i+1)+' / '+S.length+'  ·  ←/→ to navigate'}}
document.onkeydown=e=>{{if(e.key==='ArrowRight')show(i+1);if(e.key==='ArrowLeft')show(i-1)}};show(0);</script>"""
open(f"{OUT}/index.html","w").write(doc)
print(f"ZM review: {len(zm)} sample slides -> {OUT}/index.html")
