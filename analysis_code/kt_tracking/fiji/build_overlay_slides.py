#!/usr/bin/env python3
"""
build_overlay_slides.py — browsable slideshow of the KT-tracking QC overlays.
Writes overlays/kt_overlay_slides.html (one slide per batch, with metadata,
prev/next + arrow-key nav and a jump dropdown). Videos load via a local HTTP
server rooted at the overlays/ dir.
"""
import os, csv, json, glob

OUT = "/Volumes/5 MB/kt_tracking"
OVL = os.path.join(OUT, "overlays")
SUMMARY = os.path.join(OUT, "results", "KT_tracking_summary.csv")

stats = {}
if os.path.isfile(SUMMARY):
    for r in csv.DictReader(open(SUMMARY)):
        stats[r["batch"]] = r

entries = []
for mp4 in glob.glob(os.path.join(OVL, "*_KToverlay.mp4")):
    base = os.path.basename(mp4).replace("_KToverlay.mp4", "")
    s = stats.get(base, {})
    entries.append({
        "base": base,
        "date": base[:8],
        "name": base[9:].replace("_", " "),
        "video": os.path.basename(mp4),
        "n_tracks": s.get("n_tracks", "?"),
        "n_spots": s.get("n_spots", "?"),
        "speed": s.get("median_kt_speed_um_per_min", "") or "—",
    })
# newest cells first (bottom-up preference): date desc, then name
entries.sort(key=lambda e: (e["date"], e["name"]), reverse=True)

DATA = json.dumps(entries)
html = """<!doctype html><html><head><meta charset="utf-8">
<title>KT tracking overlays (%d batches)</title>
<style>
  :root{color-scheme:dark}
  body{margin:0;background:#0c0c0e;color:#e8e8ea;font:15px/1.4 -apple-system,Segoe UI,Roboto,sans-serif}
  #top{display:flex;align-items:center;gap:16px;padding:10px 16px;background:#17171b;border-bottom:1px solid #2a2a30;position:sticky;top:0;z-index:5}
  #title{font-size:20px;font-weight:600}
  .meta{font-size:15px;color:#b9b9c2}
  .meta b{color:#fff}
  .pill{background:#23232a;border-radius:6px;padding:3px 9px;margin-left:6px}
  #spacer{flex:1}
  select,button{background:#23232a;color:#e8e8ea;border:1px solid #3a3a44;border-radius:7px;padding:7px 12px;font-size:15px;cursor:pointer}
  button:hover,select:hover{background:#2e2e37}
  #wrap{display:flex;justify-content:center;align-items:flex-start;padding:18px}
  video{max-width:min(96vw,1200px);max-height:82vh;border:1px solid #2a2a30;border-radius:8px;background:#000}
  #counter{font-variant-numeric:tabular-nums;color:#9a9aa4}
  kbd{background:#23232a;border:1px solid #3a3a44;border-radius:4px;padding:1px 6px;font-size:12px}
</style></head><body>
<div id="top">
  <span id="title">KT overlays</span>
  <span id="counter"></span>
  <span class="meta" id="info"></span>
  <span id="spacer"></span>
  <span class="meta">jump</span>
  <select id="jump"></select>
  <button onclick="go(-1)">◀ Prev</button>
  <button onclick="go(1)">Next ▶</button>
  <span class="meta" style="margin-left:8px">(<kbd>←</kbd>/<kbd>→</kbd>)</span>
</div>
<div id="wrap"><video id="vid" controls autoplay loop muted playsinline></video></div>
<script>
const D=%s; let i=0;
const vid=document.getElementById('vid'), info=document.getElementById('info'),
      counter=document.getElementById('counter'), jump=document.getElementById('jump');
D.forEach((e,k)=>{const o=document.createElement('option');o.value=k;
  o.textContent=`${e.date}  ${e.name}  (${e.n_tracks} tr)`;jump.appendChild(o);});
function show(){const e=D[i];
  vid.src=encodeURIComponent(e.video);vid.load();
  counter.textContent=`${i+1} / ${D.length}`;
  info.innerHTML=`<b>${e.date}</b> &nbsp; ${e.name} `+
    `<span class="pill">tracks <b>${e.n_tracks}</b></span>`+
    `<span class="pill">spots <b>${e.n_spots}</b></span>`+
    `<span class="pill">med KT speed <b>${e.speed}</b> µm/min</span>`;
  jump.value=i;}
function go(d){i=(i+d+D.length)%%D.length;show();}
jump.addEventListener('change',()=>{i=+jump.value;show();});
document.addEventListener('keydown',ev=>{if(ev.key==='ArrowRight')go(1);
  else if(ev.key==='ArrowLeft')go(-1);});
show();
</script></body></html>""" % (len(entries), DATA)

out = os.path.join(OVL, "kt_overlay_slides.html")
open(out, "w").write(html)
print(f"wrote {out} ({len(entries)} slides)")
