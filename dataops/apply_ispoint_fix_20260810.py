#!/usr/bin/env python3
"""Re-declare `timestrip_frame` a POINT tool on every shipped timestrip slide.

USER 2026-08-10: "the monitoring/ablation frame buttons arent [working] ... nothing seems to happen when i
click ablation starts/ends, monitoring starts/ends, etc".

CAUSE. The page decides on click whether a tool records a single point or begins a polygon:

    const isPoint = (tool.type === 'kt_point' || tool.type === 'polar_track' || tool.type === 'pole');

`timestrip_frame` was missing, so all eight `ts:` buttons fell into the polygon branch: the first click just
opened a `drawing` that never closed, which looks exactly like nothing happening. The fix existed in
fix_timestrip_buttons_20260810.py, but that script patched the HTML only -- so the rebuild from the generator
dropped it and the buttons went dead again. It is now folded into make_timestrip_setup_v2_20260809.py
(patch_dispatcher, 4/4), and this script repairs the slides already on disk.

Non-destructive: each file is backed up to .bak_pre_ispoint_20260810 before it is rewritten, and a file that
is already correct is left untouched.
"""
import os, re, shutil, sys

ROOTS = ["/Volumes/4 MB/_working/_annotation_packages/kt_outline_annot_pkgs_20260722",
         "/Volumes/4 MB/_working/_annotation_packages/meta_ontarget_cdc20_pkgs_20260723",
         "/Volumes/4 MB/_working/_annotation_packages/kt_outline_annot_pkgs_cdc20_two_three_ontarget_20260725"]
SUFFIX = ".bak_pre_ispoint_20260810"

OLD = """const isPoint = (tool.type === 'kt_point'
                    || tool.type === 'polar_track'
                    || tool.type === 'pole');"""
NEW = """const isPoint = (tool.type === 'kt_point'
                    || tool.type === 'polar_track'
                    || tool.type === 'pole'
                    || tool.type === 'timestrip_frame');"""


def patch(path):
    html = open(path, encoding="utf-8", errors="replace").read()
    if "timestrip_frame" not in html:
        return "not a timestrip slide"
    if "|| tool.type === 'timestrip_frame')" in html:
        return "already correct"
    if OLD in html:
        out = html.replace(OLD, NEW, 1)
    else:
        m = re.search(r"const isPoint = \(tool\.type === 'kt_point'[\s\S]{0,200}?\);", html)
        if not m:
            return "ANCHOR NOT FOUND"
        out = html.replace(m.group(0),
                           m.group(0).replace(");", "\n                    || tool.type === 'timestrip_frame');"), 1)
    if "|| tool.type === 'timestrip_frame')" not in out:
        return "PATCH DID NOT TAKE"
    shutil.copyfile(path, path + SUFFIX)
    tmp = path + ".tmp"
    open(tmp, "w", encoding="utf-8").write(out)
    os.replace(tmp, path)
    return "FIXED"


def main():
    seen = 0
    for root in ROOTS:
        if not os.path.isdir(root):
            continue
        for name in sorted(os.listdir(root)):
            if not name.endswith(".html") or ".bak" in name:
                continue
            path = os.path.join(root, name)
            r = patch(path)
            if r == "not a timestrip slide":
                continue
            seen += 1
            print(f"  {r:18s} {name}")
    print(f"\n{seen} timestrip slide(s) checked")


if __name__ == "__main__":
    sys.exit(main())
