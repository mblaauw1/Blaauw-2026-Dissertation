"""build_all_kt_slides.py — build the kinetochore-tracing slides for the whole batch set,
using the ESTABLISHED annotation-slide tool (~/ablation-pipeline/make_annotation_html.py).

SET: single-ablation (# Sisterless KTs == 1) + ON-TARGET + non-drug + not-excluded + non-metaphase
     (lib.plot_excluded enforces the standing exclusions), MONITORING movies only.

Per batch: make_annotation_html.py --phases mon  ->  package with all-keyframe mon_phase/mon_fluor mp4s,
master key times, compiled batch comments, and the kt_outline grouping tool.
Then one multi-batch index over all of them.
"""
import os, sys, json, subprocess

os.chdir("/Volumes/4 MB/ablation_figures_20260625"); sys.path.insert(0, ".")
import lib

PKG_ROOT = "/Volumes/4 MB/_working/_annotation_packages/kt_outline_annot_pkgs_20260722"
TOOL = os.path.expanduser("~/ablation-pipeline/make_annotation_html.py")
INDEX = os.path.join(PKG_ROOT, "index.html")


def batch_set():
    data, _ = lib.load_master()
    return [r for r in data
            if r.get("# Sisterless KTs") == "1"
            and r.get("On-Target / Off-Target", "").lower() == "on-target"
            and not lib.plot_excluded(r["Batch Name"])]


def main():
    os.makedirs(PKG_ROOT, exist_ok=True)
    sel = batch_set()
    print(f"{len(sel)} batches in the set", flush=True)
    specs, fails = [], []
    for n, r in enumerate(sel, 1):
        b, dp = r["Batch Name"], r["Drive Path"]
        pkg = os.path.join(PKG_ROOT, b)
        if not os.path.isdir(dp):
            fails.append((b, "no output dir")); print(f"[{n}/{len(sel)}] SKIP {b} — no output dir", flush=True); continue
        os.makedirs(pkg, exist_ok=True)
        p = subprocess.run([sys.executable, "-u", TOOL, "--batch-dir", dp, "--pkg-dir", pkg,
                            "--phases", "mon"], capture_output=True, text=True)
        if p.returncode != 0 or not os.path.isfile(os.path.join(pkg, "index.html")):
            fails.append((b, (p.stderr or p.stdout)[-200:]))
            print(f"[{n}/{len(sel)}] FAIL {b}", flush=True); continue
        specs.append({"name": b, "pkg_dir": pkg})
        print(f"[{n}/{len(sel)}] OK   {b}", flush=True)

    if specs:
        subprocess.run([sys.executable, "-u", TOOL, "--multi-batch", json.dumps(specs),
                        "--index-out", INDEX, "--pkg-root", PKG_ROOT, "--phases", "mon"],
                       check=False)
    print(f"\nDONE — {len(specs)} slides, {len(fails)} failed")
    for b, why in fails:
        print(f"  FAIL {b}: {why}")


if __name__ == "__main__":
    main()
