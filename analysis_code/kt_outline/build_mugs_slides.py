"""build_mugs_slides.py — annotation-style slides for the MUGs batches (same tool as the KT slides)."""
import os, sys, json, subprocess, csv, io
PKG_ROOT = "/Volumes/4 MB/_working/_annotation_packages/mugs_annot_pkgs_20260722"
# PLAIN annotation slides: the pristine pre-2026-07-22 tool, with none of the
# kinetochore-outline additions (no zoom layer, no KT group panel, no mon-only phases).
TOOL = os.path.expanduser("~/ablation-pipeline/make_annotation_html_plain.py")
INDEX = os.path.join(PKG_ROOT, "index.html")
t = open("/Volumes/4 MB/ABLATION_MASTER.csv", encoding="utf-8", errors="replace").read()
rows = list(csv.reader(io.StringIO(t))); hdr = [c.strip() for c in rows[1]]
bi, pi = hdr.index("Batch Name"), hdr.index("Drive Path")
sel = [(r[bi].strip(), r[pi].strip()) for r in rows[2:] if r and len(r) > pi and "MUG" in r[bi]]
os.makedirs(PKG_ROOT, exist_ok=True)
print(f"{len(sel)} MUGs batches", flush=True)
specs, fails = [], []
for n, (b, dp) in enumerate(sel, 1):
    if not os.path.isdir(dp): fails.append(b); print(f"[{n}] SKIP {b}", flush=True); continue
    pkg = os.path.join(PKG_ROOT, b); os.makedirs(pkg, exist_ok=True)
    p = subprocess.run([sys.executable, "-u", TOOL, "--batch-dir", dp, "--pkg-dir", pkg,
                        "--phases", "abl,mon"], capture_output=True, text=True)
    if p.returncode != 0 or not os.path.isfile(os.path.join(pkg, "index.html")):
        fails.append(b); print(f"[{n}/{len(sel)}] FAIL {b}", flush=True); continue
    specs.append({"name": b, "pkg_dir": pkg}); print(f"[{n}/{len(sel)}] OK {b}", flush=True)
if specs:
    subprocess.run([sys.executable, "-u", TOOL, "--multi-batch", json.dumps(specs),
                    "--index-out", INDEX, "--pkg-root", PKG_ROOT, "--phases", "abl,mon"], check=False)
print(f"DONE — {len(specs)} slides, {len(fails)} failed")
