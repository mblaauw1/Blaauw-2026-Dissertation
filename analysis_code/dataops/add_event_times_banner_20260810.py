#!/usr/bin/env python3
"""Put each batch's EVENT TIMES in the top banner of an annotation slide.

USER 2026-08-10: "on both the kt outline slides with the 11 batches and the timestrip-making slides, i need
you to include the event times for that batch on the top banner"

HOW, and why this way. The slide already has a `#batch-meta-host` in `#top-strip`, and `showBatch(i)` clones
that batch's `.batch-meta` into it on every switch. So the times must be (a) attached to the batch, not the
page, and (b) re-rendered on switch. This appends one script that wraps the page's OWN `showBatch` rather
than replacing it: the original runs first (so its meta-clone still happens), then the times are appended
into the same host. Nothing in the page's logic is edited, so this cannot disturb marking or saving.

Times come from the master row, in the same H:MM:SS the rest of the deck uses: NEB, metaphase start,
anaphase onset, and metaphase duration. Missing values are shown as "--" rather than hidden, so a gap in
master is visible on the slide instead of silently absent.
"""
import sys, os, re, json, csv
sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import lib

csv.field_size_limit(10 ** 9)


def hms(sec):
    if sec is None:
        return "--"
    neg = sec < 0
    sec = abs(float(sec))
    h = int(sec // 3600); m = int((sec % 3600) // 60); s = int(round(sec % 60))
    if s == 60: s = 0; m += 1
    if m == 60: m = 0; h += 1
    return ("-" if neg else "") + (f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}")


def batches_in(html):
    b = set()
    m = re.search(r"BATCH_METAS\s*=\s*(\[.*?\])\s*;", html, re.S)
    if m:
        try:
            for e in json.loads(m.group(1)):
                v = e.get("batch") or e.get("name")
                if v: b.add(v)
        except Exception:
            pass
    b |= set(re.findall(r'data-batch="([^"]+)"', html))
    return sorted(x for x in b if x and not x.startswith("$"))


def build(path):
    html = open(path, encoding="utf-8", errors="replace").read()
    rows, _ = lib.load_master(); MR = {r["Batch Name"]: r for r in rows}
    bs = batches_in(html)
    ev = {}
    for b in bs:
        r = MR.get(b, {}) or {}
        neb = lib.parse_time(r.get("NEB Time (s)", ""))
        ms  = lib.parse_time(r.get("Metaphase Start (s)", ""))
        an  = lib.parse_time(r.get("Anaphase Onset (s)", ""))
        dur = ((an - ms) / 60.0) if (ms is not None and an is not None and an > ms) else None
        ev[b] = (f"NEB {hms(neb)}  ·  metaphase {hms(ms)}  ·  anaphase {hms(an)}"
                 + (f"  ·  metaphase lasts {dur:.1f} min" if dur is not None else "")
                 + f"  ·  #sisterless {(r.get('# Sisterless KTs','') or '--').strip() or '--'}"
                 + f"  ·  {(r.get('Phase of Ablations','') or '--').strip() or '--'}")
    if not ev:
        print(f"   no batches found in {os.path.basename(path)}"); return False

    MARK = "<!-- EVENT-TIMES-BANNER -->"
    if MARK in html:                                   # idempotent: replace a previous injection
        html = re.sub(re.escape(MARK) + r".*?" + re.escape("<!-- /EVENT-TIMES-BANNER -->"), "", html, flags=re.S)

    # `#top-strip` is `height:74px; overflow:hidden`, so an appended line was being CLIPPED rather than
    # missing -- the text was in the DOM the whole time. The strip is released to auto-height (keeping 74px
    # as a minimum so nothing else shifts) and the line is given its own full-width row inside the host.
    script = (MARK + "\n<style>"
              "#top-strip{height:auto!important;min-height:74px;overflow:visible!important}"
              "#batch-meta-host{overflow:visible!important}"
              "#evt-times{flex:1 1 100%;display:block;margin-top:2px;font-size:11.5px;"
              "color:#8ab4f8;letter-spacing:.01em;white-space:nowrap;overflow-x:auto}"
              "</style>\n<script>\n"
              "(function(){\n"
              "  var EVT = " + json.dumps(ev) + ";\n"
              "  function paint(){\n"
              "    try{\n"
              "      var host=document.getElementById('batch-meta-host'); if(!host) return;\n"
              "      var b=(typeof currentBatch==='function')?currentBatch():null; if(!b) return;\n"
              "      var el=document.getElementById('evt-times');\n"
              "      if(!el){ el=document.createElement('span'); el.id='evt-times'; host.appendChild(el); }\n"
              "      else if(el.parentNode!==host){ host.appendChild(el); }\n"
              "      el.textContent = EVT[b] || 'no event times in master for this batch';\n"
              "    }catch(e){}\n"
              "  }\n"
              "  // wrap the page's own showBatch so its meta-clone still runs first\n"
              "  var _orig = window.showBatch;\n"
              "  if(typeof _orig==='function'){ window.showBatch=function(i){ var r=_orig.apply(this,arguments); paint(); return r; }; }\n"
              "  document.addEventListener('DOMContentLoaded', paint);\n"
              "  setTimeout(paint, 400); setTimeout(paint, 1500);\n"
              "})();\n</script>\n<!-- /EVENT-TIMES-BANNER -->\n")
    html = html.replace("</body>", script + "</body>", 1)
    tmp = path + ".tmp"
    open(tmp, "w", encoding="utf-8").write(html)
    os.replace(tmp, path)
    print(f"   {os.path.basename(path)}: event times injected for {len(ev)} batches")
    return True


if __name__ == "__main__":
    targets = sys.argv[1:] or [
        "/Volumes/4 MB/_working/_annotation_packages/kt_outline_annot_pkgs_20260722/plate_outlines_prometaphase_9cells.html",
        "/Volumes/4 MB/_working/_annotation_packages/kt_outline_annot_pkgs_20260722/timestrip_setup_ALL.html",
    ]
    for t in targets:
        if os.path.isfile(t):
            build(t)
        else:
            print(f"   MISSING: {t}")
