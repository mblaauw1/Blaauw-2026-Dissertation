"""build_triple_prometa_cdc20_slides_20260806.py — kinetochore-outline (8811 format) slides.

USER 2026-08-06: "open the triple sisterless on target prometaphase cdc20 non-excluded batches in
kinetochore outline format slides."

SET, each filter from her sentence:
    Cell Type            == 'eYFP cdc20'
    On-Target/Off-Target == 'On-target'
    # Sisterless KTs     == '3'
    Phase of Ablations   == 'prometaphase'      (the master column IS the v2 binning as of 2026-08-06)
    not lib.plot_excluded(batch)                 -> drops Exclude=Yes, drugs (incl. ZM), review outliers,
                                                    metaphase AND prophase ablations, 4-sisterless

The phase test is kept explicit even though plot_excluded now drops prophase and metaphase on its own:
she asked for prometaphase by name, and a blank phase would otherwise slip through.

Same MONITORING-only package build as the other kt_outline slide builders.
"""
import os, sys, json, subprocess

os.chdir("/Volumes/4 MB/ablation_figures_20260625"); sys.path.insert(0, ".")
import lib

PKG_ROOT = "/Volumes/4 MB/_working/_annotation_packages/kt_outline_annot_pkgs_triple_prometa_cdc20_20260806"
TOOL = os.path.expanduser("~/ablation-pipeline/make_annotation_html.py")
INDEX = os.path.join(PKG_ROOT, "index.html")


def gv(r, c):
    return (r.get(c, "") or "").strip()


def batch_set():
    data, _ = lib.load_master()
    return [r for r in data
            if gv(r, "Cell Type").lower() == "eyfp cdc20"
            and gv(r, "On-Target / Off-Target").lower() == "on-target"
            and gv(r, "# Sisterless KTs") == "3"
            and gv(r, "Phase of Ablations").lower().startswith("promet")
            and not lib.plot_excluded(r["Batch Name"])]


def main():
    os.makedirs(PKG_ROOT, exist_ok=True)
    sel = batch_set()
    print(f"{len(sel)} batches in the set", flush=True)
    specs, fails = [], []
    for n, r in enumerate(sel, 1):
        b, dp = r["Batch Name"], r.get("Drive Path", "")
        pkg = os.path.join(PKG_ROOT, b)
        if not dp or not os.path.isdir(dp):
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
                        "--index-out", INDEX, "--pkg-root", PKG_ROOT, "--phases", "mon"], check=False)
    print(f"\nDONE — {len(specs)} slides, {len(fails)} failed")
    print(f"INDEX: {INDEX}")
    for b, why in fails:
        print(f"  FAIL {b}: {why}")


if __name__ == "__main__":
    main()
