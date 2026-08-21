#!/usr/bin/env python3
"""Lock r=5 as the deck default + finish item 22.
 1. preserve the current r=9 deck PNGs -> _gen/r9 (so the radius-review slideshows keep a true r=9).
 2. run the negative-fraction-by-radius tally (item 22).
 3. re-render the 6 intensity scripts at default r=5 -> group4/ PNGs + provenance CSVs.
 4. rebuild the 7 radius-review slideshows (r=9 from _gen/r9; r=5 marked as the deck default).
Everything on /Volumes/4 MB."""
import os, sys, subprocess, shutil, html, datetime
FIG="/Volumes/4 MB/ablation_figures_20260625"
MAIN=f"{FIG}/group4"
SWEEP="/Volumes/4 MB/ablation_plots/r_sweep_20260627"
GEN=f"{SWEEP}/_gen"
LOG=open(f"{SWEEP}/r5_lock.log","w")
def log(m):
    line=f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {m}"; print(line,flush=True); LOG.write(line+"\n"); LOG.flush()

PNGS=["G4_frap.png","G4_ablation_intensity.png","G4_prepost_intensity.png",
      "G4_cdc20_intensity_near_poles.png","G4_kt_intensity_time.png",
      "G4_cdc20_vs_distance.png","G4_cdc20_intensity_sanitycheck.png"]
SCRIPTS=["group4_ablation_intensity.py","group4_cdc20_poles.py","group4_frap.py",
         "group4_movement.py","group4_prepost.py","group4_tracking_dist.py"]

# 1. preserve current r=9
os.makedirs(f"{GEN}/r9",exist_ok=True)
for p in PNGS:
    src=f"{MAIN}/{p}"
    if os.path.isfile(src): shutil.copy2(src,f"{GEN}/r9/{p}"); log(f"preserved r9 {p}")
    else: log(f"WARN no r9 source {p}")

# 2. negatives tally (item 22)
log("running negatives_by_radius.py ...")
p=subprocess.run([sys.executable,f"{FIG}/negatives_by_radius.py"],env=dict(os.environ,MPLBACKEND="Agg"),capture_output=True,text=True)
for ln in (p.stdout.strip().splitlines() or [])[-9:]: log("  neg> "+ln)
if p.returncode!=0: log("negatives FAILED: "+(p.stderr.strip().splitlines() or [''])[-1])

# 3. re-render at r=5 (default) -> group4 + provenance
for scr in SCRIPTS:
    log(f"r5 render {scr} ...")
    pr=subprocess.run([sys.executable,f"{FIG}/{scr}"],env=dict(os.environ,MPLBACKEND="Agg"),capture_output=True,text=True)
    tail=(pr.stdout.strip().splitlines() or [""])[-1]
    log(f"r5 {scr} {'ok :: '+tail if pr.returncode==0 else 'FAILED: '+(pr.stderr.strip().splitlines() or [''])[-1]}")

# 4. rebuild slideshows: r=9 from _gen/r9, r=5 from group4 (new deck default), others from _gen
SHOW=f"{SWEEP}/slideshows"; os.makedirs(SHOW,exist_ok=True)
def img_path(png,R):
    if R==9: return f"{GEN}/r9/{png}"
    if R==5: return f"{MAIN}/{png}"      # the freshly-rendered deck default
    return f"{GEN}/r{R}/{png}"
RALL=[9,8,7,6,5,4,3]
for png in PNGS:
    slides=[(R,img_path(png,R)) for R in RALL if os.path.isfile(img_path(png,R))]
    if not slides: log(f"slideshow {png}: none"); continue
    title=png.replace(".png","")
    body=[]
    for i,(R,pp) in enumerate(slides):
        tag=f"r={R}"+(" — NOW IN DECK" if R==5 else (" (old default)" if R==9 else ""))
        body.append(f'<div class="slide" data-i="{i}" style="display:{ "block" if i==0 else "none"}">'
          f'<div class="cap">{html.escape(title)} &nbsp;·&nbsp; <b>{tag}</b> '
          f'<span class="ix">[{i+1}/{len(slides)}]</span></div>'
          f'<img src="file://{html.escape(pp)}"></div>')
    h=f"""<!doctype html><meta charset=utf-8><title>{html.escape(title)} — radius review</title>
<style>body{{margin:0;background:#111;color:#eee;font-family:-apple-system,Arial}}
.cap{{padding:8px 14px;font-size:15px;background:#000;position:sticky;top:0}}
.ix{{color:#888}} img{{max-width:100vw;max-height:calc(100vh - 40px);display:block;margin:0 auto;background:#000}}
.hint{{position:fixed;bottom:6px;right:10px;color:#666;font-size:12px}}</style>
<div id=stage>{''.join(body)}</div>
<div class=hint>&larr; &rarr; or j/k to change radius &middot; {len(slides)} radii</div>
<script>
let i=0,n={len(slides)},S=[...document.querySelectorAll('.slide')];
function show(k){{i=(k+n)%n;S.forEach((s,j)=>s.style.display=j==i?'block':'none');}}
document.onkeydown=e=>{{if(e.key==='ArrowRight'||e.key==='j')show(i+1);
 else if(e.key==='ArrowLeft'||e.key==='k')show(i-1);}};
</script>"""
    open(f"{SHOW}/{title}__radius_review.html","w").write(h)
    log(f"slideshow {png}: {[R for R,_ in slides]}")
log("=== R5 LOCK DONE ===")
LOG.close()
