"""build_if_paired_slides.py — IF slides for the batches that contain BOTH the ablation acquisition
AND the IF scan (user 2026-07-22).

THE PROBLEM THIS FIXES
Each of these batches already holds two acquisitions in `Source Files`:
    IF dish 1 ro ptk2 cdc20_1_MMStack_Pos10.ome.tif   <- the IF SCAN (multi-position acquisition "_1")
    IF dish 1 ro ptk2 cdc20_11_MMStack_Pos0.ome.tif   <- that cell's ABLATION
but `frames.json` labels every frame `ablation`/`pre` and none `monitoring`, so the scan frames are never
rendered — which is why each of these batches ships a 257-byte empty `_Monitoring.mp4` placeholder.
Same class of role-misassignment as the known z-stack-as-monitoring bug.

FIX (non-destructive): we never touch the original frames.json. A CORRECTED copy is written into the
package, in which any frame whose `source` is the scan acquisition is re-roled `monitoring`, so the scan
renders in its own panel beside the ablation. The rule is purely "which acquisition did this frame come
from", read from the frame's own `source` field — no inference about content.
"""
import csv, io, json, os, re, shutil, subprocess, sys

ROOT = "/Volumes/4 MB"
PKG_ROOT = f"{ROOT}/_working/_annotation_packages/if_paired_annot_pkgs_20260722"
STAGE = f"{ROOT}/_scratch/if_paired_stage"
TOOL = os.path.expanduser("~/ablation-pipeline/make_annotation_html_plain.py")
INDEX = os.path.join(PKG_ROOT, "index.html")

t = open(f"{ROOT}/ABLATION_MASTER.csv", encoding="utf-8", errors="replace").read()
rows = list(csv.reader(io.StringIO(t)))
hdr = [c.strip() for c in rows[1]]
bi, pi, si = hdr.index("Batch Name"), hdr.index("Drive Path"), hdr.index("Source Files")


def acq_of(fname):
    """'IF dish 1 ro ptk2 cdc20_11_MMStack_Pos0.ome.tif' -> acquisition stem 'IF dish ... cdc20_11'"""
    m = re.match(r"(.+?)_MMStack_Pos\d+", fname.strip())
    return m.group(1) if m else fname.strip()


def scan_acq_for(batch, srcs):
    """The IF SCAN acquisition = the source acquisition that is NOT the batch's own ablation acquisition.
    The ablation acquisition matches the batch name's trailing index; the scan is the other one."""
    acqs = [acq_of(s) for s in srcs if s.strip()]
    uniq = []
    for a in acqs:
        if a not in uniq: uniq.append(a)
    if len(uniq) < 2: return None
    stem = re.sub(r"^\d{8}\s+", "", batch).strip()
    own = [a for a in uniq if a == stem]
    other = [a for a in uniq if a != stem]
    return other[0] if own and other else (uniq[0] if len(uniq) > 1 else None)


sel = []
for r in rows[2:]:
    if not r or len(r) <= max(pi, si): continue
    b = r[bi].strip()
    if not re.search(r"\bIF\b|IF stained|IF dish", b, re.I): continue
    dp = r[pi].strip()
    if not os.path.isdir(dp): continue
    srcs = [s for s in r[si].split(";") if s.strip()]
    if len({acq_of(s) for s in srcs}) < 2: continue      # needs BOTH acquisitions
    sel.append((b, dp, srcs))

print(f"{len(sel)} IF batches contain BOTH the ablation and the IF scan", flush=True)
os.makedirs(PKG_ROOT, exist_ok=True); os.makedirs(STAGE, exist_ok=True)

specs, fails, fixed = [], [], 0
for n, (b, dp, srcs) in enumerate(sel, 1):
    scan = scan_acq_for(b, srcs)
    stage = os.path.join(STAGE, b)
    if os.path.isdir(stage): shutil.rmtree(stage)
    os.makedirs(stage, exist_ok=True)
    # stage a copy of the batch dir (symlink the big files, rewrite only frames.json)
    fj_name = None
    for f in os.listdir(dp):
        s, d = os.path.join(dp, f), os.path.join(stage, f)
        if f.endswith("_frames.json"): fj_name = f; continue
        try: os.symlink(s, d)
        except Exception: pass
    if not fj_name:
        fails.append((b, "no frames.json")); continue
    meta = json.loads(open(os.path.join(dp, fj_name), encoding="utf-8", errors="replace").read())
    nfix = 0
    for fr in meta.get("frames", []):
        src = str(fr.get("source", ""))
        if scan and acq_of(src) == scan and fr.get("role") != "monitoring":
            fr["role"] = "monitoring"; nfix += 1
    if nfix: fixed += 1
    json.dump(meta, open(os.path.join(stage, fj_name), "w"))
    pkg = os.path.join(PKG_ROOT, b); os.makedirs(pkg, exist_ok=True)
    p = subprocess.run([sys.executable, "-u", TOOL, "--batch-dir", stage, "--pkg-dir", pkg,
                        "--phases", "abl,mon"], capture_output=True, text=True)
    if p.returncode != 0 or not os.path.isfile(os.path.join(pkg, "index.html")):
        fails.append((b, (p.stderr or p.stdout)[-160:]))
        print(f"[{n}/{len(sel)}] FAIL {b}", flush=True); continue
    specs.append({"name": b, "pkg_dir": pkg})
    print(f"[{n}/{len(sel)}] OK   {b}   scan_acq={scan}  re-roled {nfix} frames", flush=True)

if specs:
    subprocess.run([sys.executable, "-u", TOOL, "--multi-batch", json.dumps(specs),
                    "--index-out", INDEX, "--pkg-root", PKG_ROOT, "--phases", "abl,mon"], check=False)
print(f"DONE — {len(specs)} slides, {len(fails)} failed, {fixed} batches had scan frames re-roled", flush=True)
for b, why in fails[:10]:
    print(f"   FAIL {b}: {why}")
