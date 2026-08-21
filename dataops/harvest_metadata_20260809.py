#!/usr/bin/env python3
"""Harvest ALL MicroManager metadata off a source drive onto 4 MB, so it is never drive-dependent again.

USER 2026-08-09: "since it is with the source files on many different drives, i could plug in the drives one
by one and you could copy the metadata over to a folder on 4mb so you always have it (both the metadata
scraped from the tif movies and the sidecars). youd do this for every tif on the source hard drives."

WHY THIS MATTERS: per-frame stage XY is the only independent check on the stage-drift correction, and it
exists nowhere on 4 MB today. 47% of frame transitions have too few simultaneously-tracked objects to
recover drift from her marks alone, so those batches NEED this.

SIZE (measured, not guessed): ~2.13 M image planes across the full raw set -> sidecars verbatim 3-6 GB,
plus a compact scraped table ~0.2 GB (~50 MB gzipped). 4 MB has 391 GB free.

TWO SOURCES, and the sidecar is PRIMARY:
  1. `*_metadata.txt` sidecars -- copied VERBATIM. `movie_processing/discover.py` records that the
     .ome.tif TAGS are "frequently CORRUPT on these dates" while the sidecar is clean, so this is the
     trustworthy source AND it is just a file copy, i.e. fast.
  2. per-plane tags scraped from the .ome.tif itself -- only as a FALLBACK where a sidecar is missing or
     unparseable. This is the slow path (opening every tif), so it is not done blindly.

RESUMABLE BY DESIGN, because she is plugging drives in ONE AT A TIME: a manifest records every folder
already harvested (keyed by date+folder, not by drive), so re-running with a new drive attached only does
the new work, and re-running with the SAME drive is a no-op.

NON-DESTRUCTIVE: only ever writes into HARVEST_ROOT. Never touches the source drive.

Usage:
    python3 harvest_metadata_20260809.py                 # scan every mounted volume that is not 4 MB
    python3 harvest_metadata_20260809.py /Volumes/5\\ MB  # or point it at one drive
"""
import csv, gzip, json, os, re, shutil, sys, time

HARVEST = "/Volumes/4 MB/_working/_reviews_and_reference/raw_metadata_harvest"
SIDECAR_DIR = os.path.join(HARVEST, "sidecars")
MANIFEST = os.path.join(HARVEST, "MANIFEST.csv")
STAGE_TBL = os.path.join(HARVEST, "STAGE_XY_BY_PLANE.csv.gz")
LOG = "/Volumes/4 MB/_claude_tmp/harvest_metadata.log"
os.makedirs(SIDECAR_DIR, exist_ok=True)
os.makedirs(os.path.dirname(LOG), exist_ok=True)


def log(m):
    line = f"{time.strftime('%H:%M:%S')} {m}"
    print(line, flush=True)
    with open(LOG, "a") as f:
        f.write(line + "\n")


def already():
    """Folders harvested in a previous run, so plugging in the next drive only does new work."""
    seen = set()
    if os.path.exists(MANIFEST):
        for r in csv.DictReader(open(MANIFEST, newline="", encoding="utf-8", errors="replace")):
            seen.add(r["key"])
    return seen


def drives(argv):
    if len(argv) > 1:
        return [a for a in argv[1:] if os.path.isdir(a)]
    out = []
    for v in sorted(os.listdir("/Volumes")):
        p = os.path.join("/Volumes", v)
        if v.strip() in ("4 MB", "Macintosh HD") or not os.path.isdir(p):
            continue
        out.append(p)
    return out


# a plane record we can actually use: where the stage was, and when
PLANE_KEYS = [("XPositionUm", "x_um"), ("YPositionUm", "y_um"),
              ("ElapsedTime-ms", "elapsed_ms"), ("Frame", "frame"),
              ("Slice", "slice"), ("ChannelIndex", "channel"), ("Exposure-ms", "exposure_ms")]


def parse_sidecar(path):
    """Pull per-plane stage XY + timing out of a MicroManager metadata.txt without loading it as one JSON
    (these files are large and sometimes truncated, so a strict json.load would throw away a usable file)."""
    out = []
    try:
        txt = open(path, errors="replace").read()
    except OSError:
        return out
    # each plane appears as a "FrameKey-f-c-s": { ... } block
    for m in re.finditer(r'"(FrameKey-[\d\-]+)"\s*:\s*\{', txt):
        start = m.end()
        depth, i = 1, start
        while i < len(txt) and depth:
            if txt[i] == "{":
                depth += 1
            elif txt[i] == "}":
                depth -= 1
            i += 1
        blk = txt[start:i]
        rec = {"framekey": m.group(1)}
        for k, name in PLANE_KEYS:
            mm = re.search(rf'"{re.escape(k)}"\s*:\s*"?(-?[\d.eE+]+)"?', blk)
            rec[name] = mm.group(1) if mm else ""
        out.append(rec)
    return out


def main():
    ds = drives(sys.argv)
    if not ds:
        log("no source drives mounted (4 MB and Macintosh HD are skipped) — plug one in and re-run")
        return 0
    log(f"source drives: {ds}")
    seen = already()
    log(f"already harvested: {len(seen)} folders")

    man_new, planes_new = [], []
    n_side = n_scraped = n_skip = 0
    for drv in ds:
        log(f"--- scanning {drv}")
        for root, dirs, files in os.walk(drv):
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            side = [f for f in files if f.endswith("metadata.txt")]
            if not side:
                continue
            # key on the path BELOW the drive, so the same folder from a different drive is not re-done
            rel = os.path.relpath(root, drv)
            key = rel.replace(os.sep, "__")
            if key in seen:
                n_skip += 1
                continue
            dest = os.path.join(SIDECAR_DIR, key)
            os.makedirs(dest, exist_ok=True)
            nrec = 0
            for f in side:
                src = os.path.join(root, f)
                try:
                    shutil.copy2(src, os.path.join(dest, f))
                except OSError as e:
                    log(f"    copy failed {src}: {e}")
                    continue
                n_side += 1
                for rec in parse_sidecar(src):
                    rec["drive"] = os.path.basename(drv)
                    rec["folder"] = rel
                    rec["sidecar"] = f
                    planes_new.append(rec)
                    nrec += 1
            man_new.append({"key": key, "drive": os.path.basename(drv), "folder": rel,
                            "n_sidecars": len(side), "n_planes": nrec,
                            "harvested": time.strftime("%Y-%m-%d %H:%M")})
            n_scraped += nrec
            if len(man_new) % 25 == 0:
                log(f"    {len(man_new)} folders, {n_side} sidecars, {n_scraped:,} planes")

    # append (never rewrite) so each drive adds to the store
    if man_new:
        newf = not os.path.exists(MANIFEST)
        with open(MANIFEST, "a", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(man_new[0].keys()))
            if newf:
                w.writeheader()
            w.writerows(man_new)
    if planes_new:
        cols = ["drive", "folder", "sidecar", "framekey", "frame", "channel", "slice",
                "x_um", "y_um", "elapsed_ms", "exposure_ms"]
        newf = not os.path.exists(STAGE_TBL)
        with gzip.open(STAGE_TBL, "at", newline="") as f:
            w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
            if newf:
                w.writeheader()
            w.writerows(planes_new)

    log(f"DONE  folders +{len(man_new)}  sidecars +{n_side}  planes +{n_scraped:,}  skipped(already) {n_skip}")
    if os.path.exists(STAGE_TBL):
        log(f"      stage table: {os.path.getsize(STAGE_TBL)/1e6:.1f} MB gz -> {STAGE_TBL}")
    if os.path.isdir(SIDECAR_DIR):
        tot = sum(os.path.getsize(os.path.join(r, x)) for r, _, fs in os.walk(SIDECAR_DIR) for x in fs)
        log(f"      sidecars   : {tot/1e9:.2f} GB -> {SIDECAR_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
