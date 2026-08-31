#!/usr/bin/env python3
"""Radius sweep for the KT-intensity plots — PARALLEL across radii.
Re-runs the 6 intensity scripts at r=3..8 (r=9 stays the main-deck version) and builds
ONE review slideshow per affected plot (r=9..r=3) so the user can pick a radius.

Two modes:
  worker  (KT_SWEEP_RADIUS set): run the 6 scripts for that single radius, sequentially.
  driver  (default): launch the 6 radii as concurrent workers (cap=3), then build slideshows.
Everything on /Volumes/4 MB (nothing local)."""
import os, sys, subprocess, html, datetime, time
FIG="/Volumes/4 MB/ablation_figures_20260625"
MAIN=f"{FIG}/group4"                                   # r=9 lives here (the main deck)
SWEEP="/Volumes/4 MB/ablation_plots/r_sweep_20260627"
GEN=f"{SWEEP}/_gen"
os.makedirs(GEN,exist_ok=True)
RADII=[8,7,6,5,4,3]                                    # r=9 already exists in MAIN
MAXPAR=3                                               # concurrent radii (I/O on one external drive)

PLOTS={                                                # affected plot PNG -> script that produces it
 "G4_frap.png":"group4_frap.py",
 "G4_ablation_intensity.png":"group4_ablation_intensity.py",
 "G4_prepost_intensity.png":"group4_prepost.py",
 "G4_cdc20_intensity_near_poles.png":"group4_cdc20_poles.py",
 "G4_kt_intensity_time.png":"group4_movement.py",
 "G4_cdc20_vs_distance.png":"group4_tracking_dist.py",
 "G4_cdc20_intensity_sanitycheck.png":"group4_tracking_dist.py",
}
SCRIPTS=sorted(set(PLOTS.values()))

def stamp(): return datetime.datetime.now().strftime("%H:%M:%S")

# ---------------- worker mode: one radius ----------------
if os.environ.get("KT_SWEEP_RADIUS"):
    R=int(os.environ["KT_SWEEP_RADIUS"])
    outdir=f"{GEN}/r{R}"; os.makedirs(outdir,exist_ok=True)
    wlog=open(f"{SWEEP}/sweep_r{R}.log","w")
    def wl(m): wlog.write(f"[{stamp()}] {m}\n"); wlog.flush()
    wl(f"=== worker r={R} start: {len(SCRIPTS)} scripts ===")
    for scr in SCRIPTS:
        env=dict(os.environ,KT_R=str(R),KT_SWEEP_OUT=outdir,MPLBACKEND="Agg")
        env.pop("KT_SWEEP_RADIUS",None)
        wl(f"r={R} {scr} ...")
        p=subprocess.run([sys.executable,f"{FIG}/{scr}"],env=env,capture_output=True,text=True)
        tail=(p.stdout.strip().splitlines() or [""])[-1]
        if p.returncode!=0:
            wl(f"r={R} {scr} FAILED rc={p.returncode}: {(p.stderr.strip().splitlines() or [''])[-1]}")
        else:
            wl(f"r={R} {scr} ok :: {tail}")
    wl(f"=== worker r={R} DONE ===")
    wlog.close(); sys.exit(0)

# ---------------- driver mode ----------------
LOG=open(f"{SWEEP}/sweep.log","w")
def log(m):
    line=f"[{stamp()}] {m}"; print(line,flush=True); LOG.write(line+"\n"); LOG.flush()
log(f"=== PARALLEL radius sweep start: {len(RADII)} radii, cap={MAXPAR} ===")
running={}; pending=list(RADII)
def launch(R):
    env=dict(os.environ,KT_SWEEP_RADIUS=str(R),MPLBACKEND="Agg")
    p=subprocess.Popen([sys.executable,__file__],env=env)
    running[R]=p; log(f"launched worker r={R} (pid {p.pid})")
while pending or running:
    while pending and len(running)<MAXPAR:
        launch(pending.pop(0))
    time.sleep(5)
    for R,p in list(running.items()):
        if p.poll() is not None:
            log(f"worker r={R} exited rc={p.returncode}")
            del running[R]
log("=== all workers done; collating per-radius logs ===")
for R in RADII:
    lp=f"{SWEEP}/sweep_r{R}.log"
    if os.path.isfile(lp):
        for ln in open(lp):
            if " ok ::" in ln or "FAILED" in ln: LOG.write(ln)
LOG.flush()

# ---- per-plot review slideshow (r=9 .. r=3) ----
def img_path(png,R): return f"{MAIN}/{png}" if R==9 else f"{GEN}/r{R}/{png}"
SHOW=f"{SWEEP}/slideshows"; os.makedirs(SHOW,exist_ok=True)
RALL=[9]+RADII; built=[]
for png in PLOTS:
    slides=[(R,img_path(png,R)) for R in RALL if os.path.isfile(img_path(png,R))]
    if not slides: log(f"slideshow {png}: NO images, skipped"); continue
    title=png.replace(".png","")
    body=[]
    for i,(R,p) in enumerate(slides):
        tag=f"r={R}"+(" (main deck)" if R==9 else "")
        body.append(f'<div class="slide" data-i="{i}" style="display:{ "block" if i==0 else "none"}">'
          f'<div class="cap">{html.escape(title)} &nbsp;·&nbsp; <b>{tag}</b> '
          f'<span class="ix">[{i+1}/{len(slides)}]</span></div>'
          f'<img src="file://{html.escape(p)}"></div>')
    htmls=f"""<!doctype html><meta charset=utf-8><title>{html.escape(title)} — radius review</title>
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
    outp=f"{SHOW}/{title}__radius_review.html"; open(outp,"w").write(htmls)
    built.append((title,outp,len(slides))); log(f"slideshow {png}: {len(slides)} radii -> {os.path.basename(outp)}")

idx=["<!doctype html><meta charset=utf-8><title>Radius sweep — review index</title>",
 "<style>body{font-family:-apple-system,Arial;max-width:760px;margin:30px auto;padding:0 16px}",
 "li{margin:8px 0;font-size:15px} a{color:#1558d6;text-decoration:none} a:hover{text-decoration:underline}",
 ".n{color:#888;font-size:13px}</style>","<h2>KT-intensity radius sweep</h2>",
 "<p>Each plot has a review slideshow showing the same plot remeasured at r=9 (main deck), 8, 7, 6, 5, 4, 3. "
 "Use &larr; &rarr; (or j/k) to flip between radii. The main deck keeps r=9; pick a radius per plot.</p><ul>"]
for title,outp,nslide in built:
    idx.append(f'<li><a href="file://{html.escape(outp)}">{html.escape(title)}</a> <span class=n>({nslide} radii)</span></li>')
idx.append("</ul>")
open(f"{SWEEP}/index.html","w").write("\n".join(idx))
log(f"=== DONE: {len(built)} slideshows; index at {SWEEP}/index.html ===")
LOG.close()
