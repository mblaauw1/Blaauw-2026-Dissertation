#!/usr/bin/env python3
"""Make the timestrip buttons behave exactly like the kt-outline buttons.

USER 2026-08-10: "all the buttons need to finciton as the buttons in kt outlines do" / "if i click one for
a frme to be included, it should list that frame, not be some circle thats filled in or now".

THE ACTUAL DEFECT. The page's pointer handler sorts tools into two kinds:

    const isPoint = (tool.type === 'kt_point' || tool.type === 'polar_track' || tool.type === 'pole');
    if (isPoint) { addAnnotation({...}); }            // one click -> a mark, listed, deletable
    else { drawing = { tool, points: [...] , ... }; } // starts a POLYGON that you must close

`timestrip_frame` matched neither, so it fell into the polygon branch and began an outline that was never
meant to exist -- the half-drawn shape she saw, and nothing listed. Routing it through the dispatcher was
necessary but not sufficient: the tool also has to be declared a POINT tool.

So: add `timestrip_frame` to `isPoint`. One click on the movie then records the frame through the page's own
addAnnotation -> autosave -> renderList path, giving it a list row and a delete button exactly like a polar
or sisterless mark. No new code runs on click.

Also: the native crop-box handler reads its name from the `#crop-name` input, not from the tool object, so
the two crop-box buttons set that input first and then delegate to the page's own crop_box tool.
"""
import sys, os, re

MARK = "<!-- TIMESTRIP-BUTTON-FIX -->"
END = "<!-- /TIMESTRIP-BUTTON-FIX -->"

ISPOINT_OLD = """const isPoint = (tool.type === 'kt_point'
                    || tool.type === 'polar_track'
                    || tool.type === 'pole');"""
ISPOINT_NEW = """const isPoint = (tool.type === 'kt_point'
                    || tool.type === 'polar_track'
                    || tool.type === 'pole'
                    || tool.type === 'timestrip_frame');"""

DELEGATE = MARK + """
<script>
(function(){
  /* The native crop-box tool takes its name from the #crop-name input. These two buttons set it, then hand
     off to the page's own crop_box button so the drag/stamp behaviour is entirely native. */
  document.addEventListener('click', function(e){
    var b = e.target && e.target.closest ? e.target.closest('.btn[data-tool^="tsbox:"]') : null;
    if(!b) return;
    var name = (b.dataset.tool||'').slice(6);
    var inp = document.getElementById('crop-name');
    if(inp){ inp.value = name; inp.dispatchEvent(new Event('input',{bubbles:true})); }
  }, true);
})();
</script>
""" + END + "\n"


def build(path):
    html = open(path, encoding="utf-8", errors="replace").read()
    changed = []

    # 1) declare timestrip_frame a POINT tool in the page's own handler
    if ISPOINT_NEW in html:
        changed.append("isPoint already patched")
    elif ISPOINT_OLD in html:
        html = html.replace(ISPOINT_OLD, ISPOINT_NEW, 1)
        changed.append("isPoint: timestrip_frame added")
    else:
        # tolerate whitespace differences
        m = re.search(r"const isPoint = \(tool\.type === 'kt_point'[\s\S]{0,160}?\);", html)
        if m and "timestrip_frame" not in m.group(0):
            html = html.replace(m.group(0), m.group(0).replace(");", "\n                    || tool.type === 'timestrip_frame');"), 1)
            changed.append("isPoint: timestrip_frame added (loose match)")
        else:
            changed.append("WARNING: isPoint not found — frame buttons will still draw a polygon")

    # 2) crop-box name delegation
    if MARK in html:
        html = re.sub(re.escape(MARK) + r"[\s\S]*?" + re.escape(END), "", html)
    html = html.replace("</body>", DELEGATE + "</body>", 1)
    changed.append("crop-box name delegation injected")

    tmp = path + ".tmp"
    open(tmp, "w", encoding="utf-8").write(html)
    os.replace(tmp, path)
    print(f"   {os.path.basename(path)}: " + "; ".join(changed))


if __name__ == "__main__":
    for t in (sys.argv[1:] or ["/Volumes/4 MB/_working/_annotation_packages/kt_outline_annot_pkgs_20260722/timestrip_setup_ALL.html"]):
        if os.path.isfile(t):
            build(t)
        else:
            print(f"   MISSING: {t}")
