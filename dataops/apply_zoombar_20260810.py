#!/usr/bin/env python3
"""Make the timestrip zoom-box size visible in µm and adjustable, on the slides already on disk.

USER 2026-08-10: "the zoom crop box placed on click seems too big. this box should be the size of the zoom
crop box used for the kinetochore ablation events."

WHAT THE STAMPED SIZE ACTUALLY IS. 140 px, and that is already the ablation-event window, checked end to end:
ts_render.STD_ZOOM_HALF_UM = 70*0.062 = 4.34 µm HALF; ts_render.zoom_half_px(0.062) = 70;
group_timestrips.aligned_closeup_panels(..., half=70) -> box = 2*half = 140; closeup_portions defaults
half=zoom_half_px(pxs) = 70 and its `zoom=3` only cv2.resizes the crop for display without widening the
region; eff_pxs = ps(b)*box/N confirms the physical window is box*0.062 = 8.68 µm. Every mon/abl clip in
these packages is 1248x1056 and every batch on the slides is 0.062 µm/px, so 140 px on the slide covers the
same 8.68 µm as the strip. The page also draws the box through its own panel._toCanvasCoords, the exact
inverse of the _toPanelCoords used to place it, so what is drawn is what would be cropped.

SO WHY TOUCH IT. The number is right but nothing on screen said so -- the size was a constant buried in the
generator, readable only as a raw pixel count. This puts the window in µm next to the buttons, marks the
standard, and lets her step it up or down if she wants a different one. Her choice persists in localStorage
across slides and restarts; "reset" returns to the verified 8.68 µm standard. Nothing about how the box is
placed, drawn or saved changes.

Non-destructive: backup first, then an atomic replace, and a file already carrying the bar is skipped.
"""
import os, re, shutil, sys

ROOTS = ["/Volumes/4 MB/_working/_annotation_packages/kt_outline_annot_pkgs_20260722",
         "/Volumes/4 MB/_working/_annotation_packages/meta_ontarget_cdc20_pkgs_20260723",
         "/Volumes/4 MB/_working/_annotation_packages/kt_outline_annot_pkgs_cdc20_two_three_ontarget_20260725"]
SUFFIX = ".bak_pre_zoombar_20260810"
UM_PER_PX = 0.062

CSS_ANCHOR = "  #ts-counts{flex:1 1 100%;font-size:11.5px;color:#9fd39f;white-space:nowrap;margin-top:2px}"
CSS_ADD = CSS_ANCHOR + """
  #ts-zoombar{display:flex;align-items:center;gap:6px;margin:4px 0 8px;font-size:11.5px;color:#8ab4f8}
  #ts-zoombar .lab{white-space:nowrap}
  #ts-zoombar button{background:#243040;color:#cfe3ff;border:1px solid #3a4a60;border-radius:4px;
    padding:1px 7px;cursor:pointer;font-size:11.5px;line-height:1.5}
  #ts-zoombar button:hover{background:#2f3f55}
  #ts-zoom-val{color:#9fd39f;white-space:nowrap;min-width:150px;text-align:center}"""

JS_ADD = """  var ZOOM_STD = %(std)d;
  var ZOOM_KEY = 'ts_zoom_px_v1';
  var ZOOM_PX  = (function(){ var v = parseInt(localStorage.getItem(ZOOM_KEY)||'',10);
                              return (v && v>=20 && v<=600) ? v : ZOOM_STD; })();
  var UM_PER_PX = %(um)r;
  function zoomLabel(){
    var el = document.getElementById('ts-zoom-val');
    if(el) el.textContent = ZOOM_PX + ' px  (' + (ZOOM_PX*UM_PER_PX).toFixed(1) + ' µm)'
                            + (ZOOM_PX===ZOOM_STD ? '  ✓ standard' : '');
  }
  function setZoom(px){
    ZOOM_PX = Math.max(20, Math.min(600, px));
    try{ localStorage.setItem(ZOOM_KEY, String(ZOOM_PX)); }catch(e){}
    if(typeof setCropSize==='function'){ try{ setCropSize(ZOOM_PX, ZOOM_PX); }catch(e){} }
    zoomLabel();
  }
  function buildZoomUI(){
    if(document.getElementById('ts-zoombar')) return;
    var host = document.getElementById('tool-buttons-flow') || document.getElementById('controls');
    if(!host || !host.parentNode) return;
    var d = document.createElement('div');
    d.id = 'ts-zoombar';
    d.innerHTML = '<span class="lab">zoom box</span>'
                + '<button type="button" data-z="-10">−</button>'
                + '<span id="ts-zoom-val"></span>'
                + '<button type="button" data-z="10">+</button>'
                + '<button type="button" data-z="std">reset</button>';
    host.parentNode.insertBefore(d, host);
    d.addEventListener('click', function(e){
      var b = e.target.closest ? e.target.closest('button[data-z]') : null;
      if(!b) return;
      e.preventDefault(); e.stopPropagation();
      setZoom(b.dataset.z==='std' ? ZOOM_STD : ZOOM_PX + parseInt(b.dataset.z,10));
    }, true);
    zoomLabel();
  }
  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded', buildZoomUI);
  else buildZoomUI();
"""


def patch(path):
    html = open(path, encoding="utf-8", errors="replace").read()
    m = re.search(r"^  var ZOOM_PX = (\d+);\s*$", html, re.M)
    if not m:
        return "no zoom constant (not a v2 timestrip slide)"
    if "ts-zoombar" in html:
        return "already has the size bar"
    std = int(m.group(1))

    out = html.replace(m.group(0), JS_ADD % {"std": std, "um": UM_PER_PX}, 1)
    if CSS_ANCHOR in out:
        out = out.replace(CSS_ANCHOR, CSS_ADD, 1)
    else:
        return "CSS ANCHOR NOT FOUND"
    if "ts-zoombar" not in out or "ZOOM_STD" not in out:
        return "PATCH DID NOT TAKE"

    shutil.copyfile(path, path + SUFFIX)
    tmp = path + ".tmp"
    open(tmp, "w", encoding="utf-8").write(out)
    os.replace(tmp, path)
    return f"FIXED (standard {std}px = {std*UM_PER_PX:.2f} um)"


def main():
    n = 0
    for root in ROOTS:
        if not os.path.isdir(root):
            continue
        for name in sorted(os.listdir(root)):
            if not name.endswith(".html") or ".bak" in name:
                continue
            r = patch(os.path.join(root, name))
            if r.startswith("no zoom constant"):
                continue
            n += 1
            print(f"  {r:38s} {name}")
    print(f"\n{n} slide(s) touched")


if __name__ == "__main__":
    sys.exit(main())
