"""build_cdc20_two_three_ontarget_slides.py — kinetochore-tracing slides (8811 format) for the
TWO- and THREE-on-target-ablation cdc20 set, for annotating metaphase/anaphase timing.

SET: Cell Type == 'eYFP cdc20'  AND  On-Target  AND  # Sisterless KTs in {2,3}
     AND not lib.plot_excluded (drops Exclude=Yes, drugs incl. ZM, review outliers,
         metaphase-ablations, 4-sisterless)  AND both Metaphase Start (s) & Anaphase Onset (s) defined.
     MONITORING movies only (--phases mon), same as build_all_kt_slides.py.
"""
import os, sys, json, subprocess

os.chdir("/Volumes/4 MB/ablation_figures_20260625"); sys.path.insert(0, ".")
import lib

PKG_ROOT = "/Volumes/4 MB/_working/_annotation_packages/kt_outline_annot_pkgs_cdc20_two_three_ontarget_20260725"
TOOL = os.path.expanduser("~/ablation-pipeline/make_annotation_html.py")
INDEX = os.path.join(PKG_ROOT, "index.html")


def _defined(v):
    return bool((v or "").strip())


def batch_set():
    data, _ = lib.load_master()
    return [r for r in data
            if (r.get("Cell Type", "") or "").strip().lower() == "eyfp cdc20"
            and (r.get("On-Target / Off-Target", "") or "").strip().lower() == "on-target"
            and (r.get("# Sisterless KTs", "") or "").strip() in ("2", "3")
            and not lib.plot_excluded(r["Batch Name"])
            and _defined(r.get("Metaphase Start (s)")) and _defined(r.get("Anaphase Onset (s)"))]


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
