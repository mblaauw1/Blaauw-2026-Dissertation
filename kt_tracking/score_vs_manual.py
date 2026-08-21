"""score_vs_manual.py — score a TrackMate results dir against the MANUAL KT marks (ground truth).

Join is by TIME, never by frame index: TrackMate's `frame` indexes the trimmed KTmon stack
(monitoring start -> anaphase+3min), while a manual mark's frame indexes full monitoring. The stack's
`_timing.csv` sidecar maps stitched_frame -> t_sec, and manual marks carry a real t_sec (after the
2026-07-22 repair), so time is the only common axis. Joining by frame understates recall badly
(56% vs the true 70% measured on the live results).

Reports, per run:
  RECALL     fraction of manual KT marks that have a TrackMate spot within TOL um at the same time
  SPOTS/FRM  detector load (a proxy for false positives — real cells have a handful of KTs)
  TRACKS     how fragmented the result is
  COVERAGE   manual marks that fall outside the tracked time window at all

Usage: python3 score_vs_manual.py <results_dir> [--batches file] [--tol 1.5] [--label name]
"""
import csv, os, sys, glob
from collections import defaultdict
import numpy as np

ROOT = "/Volumes/4 MB"
STACKS = os.environ.get("KT_STACKS", f"{ROOT}/kt_tracking/stacks")
TOL = 1.5      # um — a manual mark counts as found if a spot is this close
DT = 12.0      # s  — and within this much time (frame interval is ~20 s)


def manual_marks():
    rows = list(csv.reader(open(f"{ROOT}/annotations/kt_points.csv")))
    ix = {c: i for i, c in enumerate(rows[0])}
    man = defaultdict(list)
    for r in rows[1:]:
        if r[ix['label']].strip() not in ('polar', 'sisterless'):
            continue
        if not r[ix['t_hms']].strip():        # only marks with a real (repaired) time
            continue
        try:
            man[r[ix['batch']].strip()].append((float(r[ix['t_sec']]), float(r[ix['x']]), float(r[ix['y']])))
        except Exception:
            pass
    return man


def pixel_sizes():
    rows = list(csv.reader(open(f"{ROOT}/ABLATION_MASTER.csv")))
    hdr = [c.strip() for c in rows[1]]
    pi = hdr.index("Pixel Size (um)")
    out = {}
    for r in rows[2:]:
        if not r or not r[0].strip() or len(r) <= pi:
            continue
        try:
            v = float(r[pi]); out[r[0].strip()] = v if v > 0 else 0.062
        except Exception:
            out[r[0].strip()] = 0.062
    return out


def timing_map(batch):
    """stitched_frame -> t_sec, from the stack sidecar."""
    p = os.path.join(STACKS, batch.replace(" ", "_") + "_timing.csv")
    if not os.path.isfile(p):
        return None
    m = {}
    for r in csv.DictReader(open(p)):
        try:
            m[int(r["stitched_frame"])] = float(r["t_sec"])
        except Exception:
            pass
    return m


def load_spots(resdir, batch):
    """(t_sec, x_um, y_um) for every spot. Prefers a *.spots_timed.csv (already has t_sec);
    otherwise uses *.spots.csv + the timing sidecar."""
    safe = batch.replace(" ", "_")
    timed = os.path.join(resdir, safe + ".spots_timed.csv")
    if os.path.isfile(timed):
        out = []
        for s in csv.DictReader(open(timed)):
            try: out.append((float(s["t_sec"]), float(s["x_um"]), float(s["y_um"])))
            except Exception: pass
        return out
    raw = os.path.join(resdir, safe + ".spots.csv")
    if not os.path.isfile(raw):
        return []
    tm = timing_map(batch)
    if not tm:
        return []
    out = []
    for s in csv.DictReader(open(raw)):
        try:
            f = int(float(s["frame"]))
            if f in tm: out.append((tm[f], float(s["x_um"]), float(s["y_um"])))
        except Exception: pass
    return out


def score(resdir, batches=None, tol=TOL, label=""):
    man = manual_marks(); ps = pixel_sizes()
    todo = batches or sorted(man)
    tot = hit = outside = 0
    nspots = nframes = 0
    per = []
    for b in todo:
        marks = man.get(b) or []
        if not marks:
            continue
        sp = load_spots(resdir, b)
        if not sp:
            continue
        p = ps.get(b, 0.062)
        t0, t1 = min(q[0] for q in sp), max(q[0] for q in sp)
        ins = [m for m in marks if t0 - DT <= m[0] <= t1 + DT]
        outside += len(marks) - len(ins)
        if len(ins) < 5:
            continue
        byt = defaultdict(list)
        for (t, x, y) in sp: byt[round(t, 1)].append((x, y))
        nspots += len(sp); nframes += max(1, len(byt))
        h = 0
        for (t, x, y) in ins:
            near = [(sx, sy) for (st, sx, sy) in sp if abs(st - t) <= DT]
            if any(np.hypot(sx - x * p, sy - y * p) <= tol for sx, sy in near):
                h += 1
        hit += h; tot += len(ins)
        per.append((h / len(ins), len(ins), b))
    rec = 100 * hit / max(1, tot)
    spf = nspots / max(1, nframes)
    print(f"[{label or os.path.basename(resdir)}]  RECALL {hit}/{tot} = {rec:.1f}%   "
          f"spots/frame {spf:.1f}   batches {len(per)}   marks outside window {outside}")
    return rec, spf, per


if __name__ == "__main__":
    resdir = sys.argv[1]
    bfile = sys.argv[sys.argv.index("--batches") + 1] if "--batches" in sys.argv else None
    lab = sys.argv[sys.argv.index("--label") + 1] if "--label" in sys.argv else ""
    tol = float(sys.argv[sys.argv.index("--tol") + 1]) if "--tol" in sys.argv else TOL
    bs = [l.strip() for l in open(bfile) if l.strip()] if bfile else None
    rec, spf, per = score(resdir, bs, tol, lab)
    per.sort()
    print("  worst:", "  ".join(f"{100*r:.0f}%:{b.split()[-1]}" for r, n, b in per[:6]))
