#!/usr/bin/env python3
"""Build annotation slides for ON-TARGET ablations in CDC20 cells in METAPHASE (user 2026-07-23).
Set = master filter (On-target + cdc20 Cell Type + Phase of Ablations==metaphase), keeping non-excluded
batches PLUS excluded ones whose Exclude Reason is only 'ablation movie / no monitoring' (not a quality/
death problem). Shows the ABLATION movie (+ monitoring where it exists). Same tool/format as the 8811 slides."""
import os, sys, json, subprocess

os.chdir("/Volumes/4 MB/ablation_figures_20260625"); sys.path.insert(0, ".")
import lib

PKG_ROOT = "/Volumes/4 MB/_working/_annotation_packages/meta_ontarget_cdc20_pkgs_20260723"
TOOL = os.path.expanduser("~/ablation-pipeline/make_annotation_html.py")
INDEX = os.path.join(PKG_ROOT, "index.html")
LIST = "/Volumes/4 MB/_scratch/meta_ontarget_cdc20.txt"


def main():
    os.makedirs(PKG_ROOT, exist_ok=True)
    names = [x for x in open(LIST).read().splitlines() if x.strip()]
    mr = {r["Batch Name"]: r for r in lib.load_master()[0]}
    print(f"{len(names)} batches in the set", flush=True)
    specs, fails = [], []
    for n, b in enumerate(names, 1):
        r = mr.get(b, {}); dp = (r.get("Drive Path", "") or "").strip()
        pkg = os.path.join(PKG_ROOT, b)
        if not dp or not os.path.isdir(dp):
            fails.append((b, "no output dir")); print(f"[{n}/{len(names)}] SKIP {b}", flush=True); continue
        os.makedirs(pkg, exist_ok=True)
        p = subprocess.run([sys.executable, "-u", TOOL, "--batch-dir", dp, "--pkg-dir", pkg,
                            "--phases", "abl,mon"], capture_output=True, text=True)
        if p.returncode != 0 or not os.path.isfile(os.path.join(pkg, "index.html")):
            fails.append((b, (p.stderr or p.stdout)[-160:])); print(f"[{n}/{len(names)}] FAIL {b}", flush=True); continue
        specs.append({"name": b, "pkg_dir": pkg})
        print(f"[{n}/{len(names)}] OK   {b}", flush=True)
    if specs:
        subprocess.run([sys.executable, "-u", TOOL, "--multi-batch", json.dumps(specs),
                        "--index-out", INDEX, "--pkg-root", PKG_ROOT, "--phases", "abl,mon"], check=False)
    print(f"\nDONE — {len(specs)} slides, {len(fails)} failed")
    for b, why in fails[:20]:
        print(f"  FAIL {b}: {why}")


if __name__ == "__main__":
    main()
