#!/usr/bin/env python3
"""Read the burned-in timestamps off a rendered movie and repair that batch's stale frames.json.

WHY.  Five batches were re-rendered AFTER their sidecar was written, so `frames.json` disagrees with
their own film (it says 00:08:49 at frame 30 where the film reads 00:15:09).  NOTES §8 rule: when they
disagree, THE FILM IS THE RECORD -- the pipeline burns the timestamp onto every frame.
  20260420 ptk2 eyfp cdc20 1 ablation_{11,13,18,20,43}

HOW.  `process.draw_timestamp` writes the time with a known, fixed rendering:
FONT_HERSHEY_SIMPLEX, scale 0.9, thickness 2 white on a thickness-3 black outline, at (10, 30).
So this does not need a general OCR -- it renders each glyph 0-9 and ':' with those exact parameters
and template-matches them along the timestamp strip.  A frame is only accepted when all 8 glyph slots
match above threshold AND the result parses as HH:MM:SS.

The pipeline prints the time with int() TRUNCATION, so a film reading is exact to the second and can be
up to 1 s below the true value -- that is recorded in the output as `precision: "+0/-1 s (truncated)"`.

Usage:
    python3 read_film_times_20260722.py <batch>            # report only
    python3 read_film_times_20260722.py <batch> --apply    # rewrite frames.json (backs up first)
    python3 read_film_times_20260722.py --stale --apply    # all five known-stale batches
"""
import csv, glob, json, os, shutil, sys, datetime
import numpy as np, cv2

ROOT = "/Volumes/4 MB"
APPLY = "--apply" in sys.argv
STALE = [f"20260420 ptk2 eyfp cdc20 1 ablation_{n}" for n in (11, 13, 18, 20, 43)]
FONT, SCALE, TH = cv2.FONT_HERSHEY_SIMPLEX, 0.9, 2


def drive_paths():
    rows = list(csv.reader(open(f"{ROOT}/ABLATION_MASTER.csv", encoding="utf-8", errors="replace")))
    hi = next(i for i, r in enumerate(rows) if r and r[0].strip() == "Batch Name")
    hdr = [c.strip() for c in rows[hi]]
    bi, pi = hdr.index("Batch Name"), hdr.index("Drive Path")
    return {r[bi].strip(): r[pi].strip() for r in rows[hi + 1:] if r and len(r) > pi and r[bi].strip()}


def glyphs():
    """one binary template per character, rendered exactly as the pipeline renders it"""
    out = {}
    for ch in "0123456789:-":
        (w, h), base = cv2.getTextSize(ch, FONT, SCALE, TH)
        img = np.zeros((h + base + 8, w + 8), np.uint8)
        cv2.putText(img, ch, (4, h + 2), FONT, SCALE, 255, TH, cv2.LINE_AA)
        ys, xs = np.where(img > 40)
        out[ch] = img[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    return out


G = glyphs()


def read_stamp(frame):
    """Return the burned-in HH:MM:SS as seconds, or None.

    Glyphs TOUCH at this font/scale, so column-splitting does not separate them. Instead every glyph
    template is slid across the strip; matches above threshold are collected with their x position and
    the best non-overlapping sequence is read off left to right. Measured 0.89-0.95 correlation per
    glyph on a real frame, so 0.62 is a wide margin.
    """
    strip = frame[0:52, 0:340]
    g = cv2.cvtColor(strip, cv2.COLOR_BGR2GRAY) if strip.ndim == 3 else strip
    _, bw = cv2.threshold(g, 200, 255, cv2.THRESH_BINARY)
    hits = []
    for ch, t in G.items():
        if t.shape[0] > bw.shape[0] or t.shape[1] > bw.shape[1]:
            continue
        res = cv2.matchTemplate(bw, t, cv2.TM_CCOEFF_NORMED)
        ys, xs = np.where(res >= 0.62)
        for y, x in zip(ys, xs):
            hits.append((int(x), ch, float(res[y, x]), t.shape[1]))
    if not hits:
        return None
    hits.sort(key=lambda h: (h[0], -h[2]))
    chosen = []
    for x, ch, v, w in hits:
        if chosen and x < chosen[-1][0] + chosen[-1][3] * 0.6:
            if v > chosen[-1][2]:
                chosen[-1] = (x, ch, v, w)
            continue
        chosen.append((x, ch, v, w))
    text = "".join(c[1] for c in chosen)
    neg = text.startswith("-")
    t = text.lstrip("-")
    if len(t) != 8 or t[2] != ":" or t[5] != ":":
        return None
    try:
        h, m, sec = int(t[0:2]), int(t[3:5]), int(t[6:8])
    except ValueError:
        return None
    v = h * 3600 + m * 60 + sec
    return -v if neg else v


def do(batch):
    d = DP.get(batch)
    if not d or not os.path.isdir(d):
        return f"SKIP {batch}: no drive path"
    fj = glob.glob(os.path.join(d, "*_frames.json"))
    if not fj:
        return f"SKIP {batch}: no frames.json"
    j = json.loads(open(fj[0], encoding="utf-8", errors="replace").read())
    pref = os.path.basename(d)
    changed, read_ok, mismatch = 0, 0, []
    for role, movie in (("monitoring", "Phase_Monitoring"), ("ablation", "Phase_Ablation"),
                        ("pre", "Phase_Pre")):
        mp4 = os.path.join(d, f"{pref}_{movie}.mp4")
        if not os.path.isfile(mp4) or os.path.getsize(mp4) < 2000:
            continue
        entries = [f for f in j.get("frames", []) if f.get("role") == role]
        cap = cv2.VideoCapture(mp4)
        i = 0
        while i < len(entries):
            ok, fr = cap.read()
            if not ok:
                break
            t = read_stamp(fr)
            if t is not None:
                read_ok += 1
                old = entries[i].get("t_sec")
                if old is None or abs(float(old) - t) >= 1.0:
                    mismatch.append((role, i, old, t))
                    entries[i]["t_sec_film"] = t
                    changed += 1
            i += 1
        cap.release()
    msg = (f"{batch}: read {read_ok} stamps, {changed} disagree with frames.json by >=1 s"
           + (f"  e.g. {mismatch[:3]}" if mismatch else ""))
    if APPLY and changed:
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        shutil.copy(fj[0], f"{ROOT}/_master_backups/{os.path.basename(fj[0])}.bak_pre_filmread_{ts}")
        for f in j.get("frames", []):
            if "t_sec_film" in f:
                f["t_sec_stale_sidecar"] = f.get("t_sec")
                f["t_sec"] = float(f.pop("t_sec_film"))
        j["t_sec_source"] = "burned-in film timestamps (read 2026-07-22); the sidecar disagreed with the render"
        j["t_sec_precision"] = "+0/-1 s (the pipeline truncates when it draws)"
        tmp = fj[0] + ".tmp"
        open(tmp, "w").write(json.dumps(j, indent=1))
        os.replace(tmp, fj[0])
        chk = json.loads(open(fj[0]).read())
        msg += f"  -> WROTE frames.json ({sum(1 for f in chk.get('frames',[]) if 't_sec_stale_sidecar' in f)} entries corrected)"
    return msg


DP = drive_paths()
targets = STALE if ("--stale" in sys.argv or not [a for a in sys.argv[1:] if not a.startswith("--")]) \
    else [a for a in sys.argv[1:] if not a.startswith("--")]
for b in targets:
    print(" ", do(b), flush=True)
if not APPLY:
    print("\n(dry run -- pass --apply to write frames.json)")
