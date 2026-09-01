#!/usr/bin/env python3
"""annotate_batch.py — one-command launcher for the iPad annotation pipeline.

Given one or more batch names from ABLATION_MASTER.csv, this script:
  1. Looks up each batch's pipeline-output folder (Drive Path in the
     master CSV; falls back to scanning /Volumes if that path is stale).
  2. Runs the iPad packager to produce the compressed TIFs + frame_map +
     key_frames for each batch.
  3. Launches Fiji with the composite TIF open and the annotation macro
     pre-loaded, so you can start clicking immediately.

USAGE
    # One batch
    python3 annotate_batch.py "20251104 ablations_15"

    # Multiple batches (each packaged; the first is auto-opened in Fiji)
    python3 annotate_batch.py "20251104 ablations_15" "20250901 triple_ablation_11"

    # Customize which channel TIF auto-opens (fluor / phase / composite)
    python3 annotate_batch.py "20251104 ablations_15" --open phase

    # Just package, don't open Fiji
    python3 annotate_batch.py "20251104 ablations_15" --no-open

CONVENTION
    Master CSV  : /Volumes/4 MB/ABLATION_MASTER.csv
    Packages out: /Volumes/2 MB/ipad_packages/<batch>/
    Fiji        : /Users/mblaauw/Downloads/Fiji/Fiji.app
    Macro       : /Users/mblaauw/ablation-pipeline/annotate_mitotic_cell.ijm
    Packager Py : .venv created at /tmp/ipadprep_venv (has imagecodecs)
"""

import argparse
import csv
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path


MASTER_CSV   = "/Volumes/4 MB/ABLATION_MASTER.csv"
PACKAGES_OUT = "/Volumes/2 MB/ipad_packages"
FIJI_BIN     = "/Users/mblaauw/Downloads/Fiji/Fiji.app/Contents/MacOS/fiji-macos-arm64"
PIPELINE_DIR = "/Users/mblaauw/ablation-pipeline"
ANNOT_MACRO  = os.path.join(PIPELINE_DIR, "annotate_mitotic_cell.ijm")
BOOT_MACRO   = os.path.join(PIPELINE_DIR, "_boot_annotation.ijm")
HTML_MAKER   = os.path.join(PIPELINE_DIR, "make_annotation_html.py")
PREP_SCRIPT  = os.path.join(PIPELINE_DIR, "prepare_for_ipad.py")
VENV_PY      = "/tmp/ipadprep_venv/bin/python"


# ── CSV lookup ──────────────────────────────────────────────────────────

def find_batch_csv_row(batch_name):
    with open(MASTER_CSV, encoding="utf-8", errors="replace") as f:
        rdr = csv.reader(f)
        rows = list(rdr)
    # Real header is the row whose first cell is "Batch Name"
    header_idx = None
    for i, r in enumerate(rows):
        if r and r[0].strip() == "Batch Name":
            header_idx = i; break
    if header_idx is None:
        sys.exit(f"Could not find header row in {MASTER_CSV}")
    header = rows[header_idx]
    bn = batch_name.strip().lower()
    for r in rows[header_idx + 1:]:
        if r and r[0].strip().lower() == bn:
            return dict(zip(header, r))
    return None


def find_batch_dir(batch_name, csv_row):
    """Resolve the on-disk batch folder. Strategy:
    1. Try Drive Path from CSV (translating common Windows drive prefixes)
    2. Fall back to searching /Volumes/*/pipeline_output/<date>/<batch>
    3. Fall back to /Volumes/*/<date>/<batch>
    """
    candidates = []

    if csv_row:
        dp = csv_row.get("Drive Path", "").strip()
        if dp:
            # If it's a Windows path, try splitting after the drive letter.
            if re.match(r"^[A-Za-z]:\\", dp):
                tail = re.sub(r"^[A-Za-z]:\\", "", dp).replace("\\", "/")
                # Common tails: "Maddie/pipeline_output/..." → "pipeline_output/..."
                tail = re.sub(r"^Maddie/", "", tail)
                for vol in _list_volumes():
                    candidates.append(os.path.join(vol, tail))
            else:
                candidates.append(dp)

    # Extract date prefix for fallback scans
    m = re.match(r"(\d{8})\s+", batch_name)
    date = m.group(1) if m else None

    if date:
        for vol in _list_volumes():
            for sub in ("pipeline_output", "pipeline_session_output"):
                candidates.append(os.path.join(vol, sub, date, batch_name))
            candidates.append(os.path.join(vol, date, batch_name))

    for c in candidates:
        if os.path.isdir(c):
            return c

    # Last resort: scan
    for vol in _list_volumes():
        for root, dirs, _ in os.walk(vol):
            if root.count(os.sep) > vol.count(os.sep) + 4:
                dirs[:] = []
                continue
            if batch_name in dirs:
                return os.path.join(root, batch_name)
    return None


def _list_volumes():
    out = []
    for name in os.listdir("/Volumes"):
        p = os.path.join("/Volumes", name)
        if os.path.isdir(p) and not name.startswith("."):
            out.append(p)
    return out


# ── Packaging + launch ──────────────────────────────────────────────────

def ensure_venv():
    """Make sure /tmp/ipadprep_venv exists and has tifffile + imagecodecs."""
    if os.path.isfile(VENV_PY):
        try:
            subprocess.check_call(
                [VENV_PY, "-c", "import tifffile, imagecodecs"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return
        except subprocess.CalledProcessError:
            pass
    print("[setup] Creating venv at /tmp/ipadprep_venv with imagecodecs…")
    subprocess.check_call([sys.executable, "-m", "venv", "/tmp/ipadprep_venv"])
    subprocess.check_call(
        ["/tmp/ipadprep_venv/bin/pip", "install", "-q",
         "tifffile", "imagecodecs", "numpy"])


def package_batch(batch_dir, force=False):
    """For the HTML annotation flow, all we need is a package directory.
    The actual MP4 copy/re-encode happens later in build_multi_batch…
    via make_annotation_html.py, which is robust across both flat and
    individual_NNNN_ pipeline output formats. The TIF packager
    (prepare_for_ipad.py) was for the abandoned ImageJ-viewer path and
    fails on older flat-layout batches — bypass it here."""
    bn = os.path.basename(batch_dir.rstrip("/"))
    out_dir = os.path.join(PACKAGES_OUT, bn)
    os.makedirs(out_dir, exist_ok=True)
    return out_dir


def find_tif_to_open(pkg_dir, which):
    """which ∈ {fluor, phase, composite}. Prefer the longest phase (mon → abl → pre)
    since it usually contains the metaphase/anaphase events of interest."""
    for phase in ("mon", "abl", "pre"):
        for f in sorted(os.listdir(pkg_dir)):
            if f == f"{phase}_{which}.tif":
                return os.path.join(pkg_dir, f)
    # Fallback: any TIF containing the channel name
    for f in sorted(os.listdir(pkg_dir)):
        if f.endswith(".tif") and f"_{which}" in f:
            return os.path.join(pkg_dir, f)
    return None


def build_multi_batch_html_and_serve(resolved, outline=False):
    """Generate a multi-batch slideshow HTML (one section per batch) and
    start the range-aware HTTP server in the parent of all packages."""
    # Generate per-batch HTML payloads (each writes its own MP4s in its
    # subfolder; the multi-batch index references them by relative path).
    # One bad batch shouldn't kill the whole run.
    batch_specs = []
    failed = []
    for bn, pkg in resolved:
        bdir = find_batch_dir(bn, find_batch_csv_row(bn))
        if not bdir:
            print(f"  [skip] {bn} — source folder not found")
            failed.append((bn, "source folder not found"))
            continue
        try:
            subprocess.check_call([sys.executable, HTML_MAKER,
                                   "--batch-dir", bdir, "--pkg-dir", pkg])
            batch_specs.append({"name": bn, "pkg_dir": pkg})
        except subprocess.CalledProcessError as e:
            print(f"  [skip] {bn} — packager exited {e.returncode}")
            failed.append((bn, f"packager exited {e.returncode}"))
            continue
    if failed:
        print(f"\n[WARN] {len(failed)} batch(es) failed during MP4 packaging:")
        for bn, why in failed:
            print(f"  {bn}  — {why}")
    if not batch_specs:
        sys.exit("No batches packaged successfully — nothing to serve.")

    # Write the multi-batch index into the common parent (PACKAGES_OUT).
    parent = os.path.commonpath([s["pkg_dir"] for s in batch_specs])
    parent = parent if os.path.isdir(parent) else PACKAGES_OUT
    if outline:
        multi_html = os.path.join(parent, "outline_index.html")
        outline_maker = os.path.join(PIPELINE_DIR, "make_outline_html.py")
        subprocess.check_call([sys.executable, outline_maker,
                               "--specs", json.dumps(batch_specs),
                               "--pkg-root", parent,
                               "--out", multi_html])
    else:
        multi_html = os.path.join(parent, "annotate_index.html")
        subprocess.check_call([sys.executable, HTML_MAKER,
                               "--multi-batch", json.dumps(batch_specs),
                               "--index-out", multi_html,
                               "--pkg-root", parent])

    # Start the range-aware server at the parent level so all batch
    # subdirs are reachable by relative path.
    serve_script = os.path.join(PIPELINE_DIR, "serve_annotation.py")
    port = 8766
    print(f"\n  [serve] index: {os.path.basename(multi_html)} (port {port})")
    proc = subprocess.Popen([sys.executable, serve_script, parent, "--port", str(port)])
    try:
        import time, webbrowser
        time.sleep(1.0)
        webbrowser.open(f"http://localhost:{port}/{os.path.basename(multi_html)}")
        print("  press Ctrl-C to stop the server")
        while True:
            try: input("> ")
            except EOFError: break
    except KeyboardInterrupt:
        pass
    finally:
        proc.terminate()


def build_html_and_serve(batch_dir, pkg_dir):
    """Generate the annotation HTML page (copies MP4s + writes index.html)
    and start a small HTTP server in the package folder so the page can
    be opened in a browser on Mac OR iPad (via Mac's LAN IP)."""
    subprocess.check_call([sys.executable, HTML_MAKER,
                           "--batch-dir", batch_dir,
                           "--pkg-dir",   pkg_dir])
    # Start an HTTP server in the pkg dir
    import http.server, socketserver, threading, webbrowser, socket
    port = 8765
    handler = lambda *a, **k: http.server.SimpleHTTPRequestHandler(
        *a, directory=pkg_dir, **k)
    httpd = socketserver.ThreadingTCPServer(("0.0.0.0", port), handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    # Find LAN IP for iPad access
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("8.8.8.8", 80))
        lan_ip = sock.getsockname()[0]
    except OSError:
        lan_ip = "127.0.0.1"
    finally:
        sock.close()
    mac_url   = f"http://localhost:{port}/index.html"
    ipad_url  = f"http://{lan_ip}:{port}/index.html"
    print(f"\n  [serve] Mac browser:  {mac_url}")
    print(f"  [serve] iPad Safari: {ipad_url}\n  (Mac + iPad must be on same Wi-Fi)\n")
    webbrowser.open(mac_url)
    # Block so the server stays up. User Ctrl-C to stop.
    try:
        while True:
            input("press Ctrl-C to stop the server > ")
    except (KeyboardInterrupt, EOFError):
        print("\nstopping…")
        httpd.shutdown()


def launch_fiji(tif_path):
    if not os.path.isfile(FIJI_BIN):
        print(f"[WARN] Fiji not found at {FIJI_BIN}; opening package folder only.")
        subprocess.Popen(["open", os.path.dirname(tif_path)])
        return
    print(f"  [fiji] opening {os.path.basename(tif_path)} + installing hotkeys")
    subprocess.Popen([FIJI_BIN, "-macro", BOOT_MACRO, tif_path])


# ── Main ────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("batches", nargs="+",
        help="One or more batch names exactly as in ABLATION_MASTER.csv")
    ap.add_argument("--open", default="composite",
        choices=["composite", "fluor", "phase"],
        help="Which TIF variant to auto-open in Fiji (default: composite)")
    ap.add_argument("--no-open", action="store_true",
        help="Package only, don't launch Fiji")
    ap.add_argument("--force", action="store_true",
        help="Re-package even if a package already exists")
    ap.add_argument("--outline", action="store_true",
        help="Launch the outline-only tool (writes to outlines_master.csv) "
             "instead of the full annotator")
    args = ap.parse_args()

    ensure_venv()

    resolved = []
    skipped_excluded = []
    for bn in args.batches:
        print(f"\n[{bn}]")
        row = find_batch_csv_row(bn)
        if row is None:
            print(f"  [WARN] not found in ABLATION_MASTER.csv "
                  f"(will still try to locate on disk)")
        else:
            # Skip batches marked Exclude=Yes in the master CSV.
            excl = (row.get("Exclude", "") or "").strip().lower()
            if excl in ("yes", "true", "1", "y"):
                reason = (row.get("Exclude Reason", "") or "").strip()
                print(f"  [skip] Exclude=Yes ({reason or 'no reason given'})")
                skipped_excluded.append((bn, reason))
                continue
        bdir = find_batch_dir(bn, row)
        if bdir is None:
            print(f"  [FAIL] batch folder not found on any mounted drive — skipping")
            continue
        print(f"  resolved → {bdir}")
        try:
            pkg = package_batch(bdir, force=args.force)
        except subprocess.CalledProcessError as e:
            print(f"  [FAIL] packager exited {e.returncode} — skipping")
            continue
        resolved.append((bn, pkg))

    if skipped_excluded:
        print(f"\nSkipped {len(skipped_excluded)} excluded batch(es):")
        for bn, reason in skipped_excluded:
            print(f"  {bn}  — {reason or 'no reason'}")

    if not resolved:
        sys.exit("No batches were packaged successfully.")

    if args.no_open:
        print("\nPackaged:")
        for bn, pkg in resolved:
            print(f"  {bn}  →  {pkg}")
        return

    # Build a multi-batch HTML index that lets the user click through all
    # resolved batches in a slideshow, then start the range-aware server.
    build_multi_batch_html_and_serve(resolved, outline=args.outline)

    if len(resolved) > 1:
        print("\nOther packaged batches (open later by re-running with one name):")
        for bn, pkg in resolved[1:]:
            print(f"  {bn}  →  {pkg}")


if __name__ == "__main__":
    main()
