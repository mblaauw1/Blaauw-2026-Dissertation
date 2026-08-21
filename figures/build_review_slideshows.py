"""Build 3 movie-review slideshows (one per missing-annotation set) so the user can
watch each batch's movies and fill in the missing field. Saved to 4 MB, opened in browser."""
import os, json, html, urllib.parse, sys
sys.path.insert(0,"/Volumes/4 MB/ablation_figures_20260625"); import lib
RD=json.load(open("/tmp/render_index.json"))
SETS=json.load(open("/tmp/review_sets.json"))
_data,_=lib.load_master(); MR={r["Batch Name"]:r for r in _data}
OUTDIR="/Volumes/4 MB/ablation_plots/annotation_review_20260626"; os.makedirs(OUTDIR,exist_ok=True)

def resolve(b):
    """Return (render_dir, file_prefix) using master Drive Path (authoritative), else name-index.
    file_prefix = basename of the render dir (may carry an _xyN suffix the batch name lacks)."""
    dp=(MR.get(b,{}) or {}).get("Drive Path","").strip()
    if dp and os.path.isdir(dp): return dp, os.path.basename(dp)
    if dp and (dp[1:3]==":\\" or dp.startswith("\\\\")): return None, None   # Windows-only path
    d=RD.get(b)
    if d: return d, os.path.basename(d)
    return None, None

PROMPTS={
 "set1_no_on_off_target":("SET 1 — assign On-target vs Off-target","Did the ablation laser hit a kinetochore (On-target) or miss it / hit something else (Off-target)? Watch the <b>Fluor Ablation</b> movie. Field to fill in master: <b>On-Target / Off-Target</b>."),
 "set2_missing_polar_lagging":("SET 2 — score Polar &amp; Lagging chromosomes","Watch the <b>Monitoring</b> movie through anaphase. Are there polar chromosomes (stuck near a pole) and/or lagging chromosomes (trailing at anaphase)? Fields: <b>Polar</b> and <b>Lagging</b> (Yes/No)."),
 "set3_no_phase_of_ablation":("SET 3 — determine Phase at moment of ablation","What mitotic phase was the cell in when ablated (prophase / prometaphase / metaphase / anaphase)? Watch the <b>Ablation</b> movie with the <b>Phase</b> channel. Field: <b>Phase of Ablation</b>."),
}
MOVIES=[("Phase Ablation","Phase_Ablation"),("Fluor Ablation","Fluor_Ablation"),
        ("Phase Monitoring","Phase_Monitoring"),("Fluor Monitoring","Fluor_Monitoring")]
def furl(p): return "file://"+urllib.parse.quote(p)

for skey,blist in SETS.items():
    title,prompt=PROMPTS[skey]
    slides=[]
    for b in blist:
        d,prefix=resolve(b); vids=""
        dp=(MR.get(b,{}) or {}).get("Drive Path","").strip()
        if not d:
            why=("Drive Path points to a Windows drive (<code>"+html.escape(dp)+"</code>) — not on any mounted Mac drive." if dp and (dp[1:3]==":\\" or dp.startswith("\\\\")) else "No render found on any mounted drive — likely unprocessed.")
            body=f'<div class="warn">{why} Cannot annotate from the Mac renders.</div>'
        else:
            cells=""
            for lab,suf in MOVIES:
                mp4=f"{d}/{prefix}_{suf}.mp4"
                if os.path.isfile(mp4):
                    cells+=f'<div class=cell><div class=vlab>{lab}</div><video src="{furl(mp4)}" controls loop muted preload="metadata"></video></div>'
                else:
                    cells+=f'<div class=cell><div class=vlab>{lab}</div><div class="vmiss">not available</div></div>'
            body=f'<div class=grid>{cells}</div><div class=path>{html.escape(d)}</div>'
        slides.append(f'<section class=slide><div class=bn>{html.escape(b)}</div>{body}</section>')
    doc=f"""<!doctype html><html><head><meta charset=utf-8><title>{html.escape(title)}</title>
<style>
*{{box-sizing:border-box}} body{{margin:0;background:#111;color:#eee;font-family:-apple-system,Helvetica,Arial,sans-serif}}
header{{position:sticky;top:0;background:#1b1b1b;padding:10px 18px;border-bottom:1px solid #333;z-index:5}}
header h1{{margin:0 0 3px;font-size:17px}} header p{{margin:0;font-size:13px;color:#bbb}}
#counter{{position:fixed;top:10px;right:18px;font-size:13px;color:#9cf;z-index:6}}
.slide{{display:none;padding:16px 20px 60px}} .slide.on{{display:block}}
.bn{{font-size:20px;font-weight:700;color:#fff;margin-bottom:12px;word-break:break-all}}
.grid{{display:grid;grid-template-columns:1fr 1fr;gap:12px;max-width:1500px}}
.cell{{background:#000;border:1px solid #2a2a2a;border-radius:6px;padding:6px}}
.vlab{{font-size:12px;color:#9cf;margin-bottom:4px}}
video{{width:100%;max-height:46vh;background:#000;display:block}}
.vmiss{{color:#a55;padding:30px;text-align:center;font-size:13px}}
.warn{{background:#3a2a00;border:1px solid #864;color:#fc9;padding:18px;border-radius:6px;max-width:900px}}
.path{{margin-top:10px;font-size:11px;color:#666;word-break:break-all}}
.nav{{position:fixed;bottom:0;left:0;right:0;background:#1b1b1b;border-top:1px solid #333;padding:8px;text-align:center}}
button{{background:#2d2d2d;color:#eee;border:1px solid #444;border-radius:5px;padding:7px 16px;font-size:14px;cursor:pointer;margin:0 6px}}
button:hover{{background:#3a3a3a}}
</style></head><body>
<header><h1>{html.escape(title)}</h1><p>{prompt} &nbsp;·&nbsp; {len(blist)} batches &nbsp;·&nbsp; ←/→ to navigate</p></header>
<div id=counter></div>
{''.join(slides)}
<div class=nav><button onclick="go(-1)">← Prev</button><button onclick="go(1)">Next →</button></div>
<script>
let i=0;const S=[...document.querySelectorAll('.slide')];
function show(){{S.forEach((s,j)=>s.classList.toggle('on',j===i));document.getElementById('counter').textContent=(i+1)+' / '+S.length;
 S.forEach(s=>s.querySelectorAll('video').forEach(v=>{{if(!s.classList.contains('on'))v.pause();}}));}}
function go(d){{i=Math.max(0,Math.min(S.length-1,i+d));show();window.scrollTo(0,0);}}
document.addEventListener('keydown',e=>{{if(e.key==='ArrowRight')go(1);if(e.key==='ArrowLeft')go(-1);}});
show();
</script></body></html>"""
    out=f"{OUTDIR}/{skey}.html"
    open(out,"w").write(doc)
    print("wrote",out,f"({len(blist)} batches)")
print("OUTDIR:",OUTDIR)
