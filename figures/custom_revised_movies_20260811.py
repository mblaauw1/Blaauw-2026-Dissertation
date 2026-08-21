#!/usr/bin/env python3
"""Movies for the cdc20 strips on REVISED_TIMESTRIPS, cropped to the SAME ROI as their timestrips.

USER 2026-08-11: "on the revised_timestrips board, for all of the cdc ones that arent frap, unmapipulatd
control, or lagging, make a movie. one movie for abltion, and one movie for monitorign. use the same rois
that we used to make the timestrips. also make one for nf9_unmanipulated-control__20250320_ptk_yfpcdc20__1_xy3"

WHICH BATCHES. The cdc20 strips on that board, minus FRAP, minus the lagging strips, minus the unmanipulated
control -- plus the one unmanipulated control she named explicitly. That drops the Mad1 (Eyfpmad1) and
hec1/Mad1 strips too, since neither is a cdc20 line.

SAME ROI, NOT A NEW ONE. The crop comes from group_timestrips.portion_box(batch, role) -- the very function
the aligned strips call -- so every per-batch nudge she has asked for today is already baked in: the
double-chromosome -40 um (clamped to the frame), off-target's up-5/right-8 and 15 um trim, ablation_19's
10 um tightening, persistent-polar's cell+5 um box, and so on. Re-deriving the crop here would have let the
movies drift away from the strips the moment either changed.

CONTENT. Both channels side by side (brightfield | fluor) where both exist, so nothing is lost; a single
channel if that is all the batch has. The burned-in acquisition overlay is stripped with the shared
ts_render.drop_burnin, as on the strips. A small elapsed-time stamp is drawn per frame -- the strips carry
timestamps, and without one a movie is hard to talk about -- but no channel names, per her standing note.
"""
import sys, os, json, glob
sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import numpy as np, cv2
# group_timestrips runs its whole category-strip pipeline at MODULE level, so a plain import here spent
# minutes rebuilding strips before this script did anything. CAT_ONLY is a substring filter over category
# names, so setting it to a name that matches nothing makes the import cheap while leaving every function
# (portion_box, movie, role_ts, ps) available. NF9/NF10 are already env-gated and stay off.
os.environ.setdefault("CAT_ONLY", "__none__")
import lib, ts_render
import group_timestrips as G

OUT = os.environ.get("MOVIE_OUT") or "/Volumes/4 MB/ablation_figures_20260625/revised_movies_20260811"
os.makedirs(OUT, exist_ok=True)

BATCHES = [
    ("off-target",                  "20250402 ptk_yfpcdc20_22"),
    ("1-sisterless-persistent-polar","20250402 ptk_yfpcdc20_2"),
    ("double-chromosome",           "20260420 ptk2 eyfp cdc20 1 ablation_71"),
    ("3-sisterless",                "20260417 ptk2 eyfp cdc20 ablation_18"),
    ("2-sisterless",                "20260417 ptk2 eyfp cdc20 ablation_19"),
    ("unmanipulated-control",       "20250320 ptk_yfpcdc20__1_xy3"),
]
FPS = {"Ablation": 5.0, "Monitoring": 10.0}
TRIM_AFTER = {}          # batch -> last t_sec to include (monitoring only); see build()
FONT = cv2.FONT_HERSHEY_SIMPLEX


def hms(t):
    s = int(round(abs(t))); sign = "-" if t < 0 else ""
    if s >= 3600: return f"{sign}{s//3600}:{(s%3600)//60:02d}:{s%60:02d}"
    return f"{sign}{s//60}:{s%60:02d}"


def crop_to(fr, box):
    return ts_render.crop_pad(ts_render.drop_burnin(fr), box)


def build(cat, b, role):
    # 🔴 BUG FIXED 2026-08-17 (user: "the ablation movies didnt render/display correctly").
    # `role_ts` decides with `r = 'ablation' if role == 'Ablation' else 'monitoring'` — a CAPITALISED
    # comparison. Passing `role.lower()` therefore never matched, so BOTH roles silently fell through to
    # 'monitoring' and every "ablation" movie was actually the monitoring clip, just written at 5 fps
    # instead of 10. The tell was in the files themselves: each ablation movie had EXACTLY the same frame
    # count as its monitoring partner (124/124, 136/136, 126/126, 112/112, 133/133), which is impossible —
    # 20260417 ...ablation_18 has 31 ablation frames against 126 monitoring frames.
    ts = G.role_ts(b, role)
    if ts is None or len(ts) == 0:
        print(f"   {b} {role}: no frames -- skipped"); return None
    box = G.portion_box(b, role)
    if box is None:
        # 2026-08-17: the FRAP cell (20250711 double ablation_18) has its strip built by
        # group_frap_timestrips, which computes its own window, so group_timestrips has no portion box for
        # it and the movie was silently skipped. Fall back to the FULL FRAME rather than dropping the clip
        # -- the movie then shows a wider field than the strip, which is stated in the index, not hidden.
        _m0 = None
        for _ch in ("Phase", "Fluor"):
            _m0 = G.movie(b, _ch, role)
            if _m0: break
        if not _m0:
            print(f"   {b} {role}: no crop box and no readable movie -- skipped"); return None
        _cap0 = _m0[0]
        _w = int(_cap0.get(cv2.CAP_PROP_FRAME_WIDTH)); _h = int(_cap0.get(cv2.CAP_PROP_FRAME_HEIGHT))
        _cap0.release()
        if _w < 8 or _h < 8:
            print(f"   {b} {role}: no crop box -- skipped"); return None
        box = (0, 0, _w, _h)
        print(f"   {b} {role}: no strip crop box -> using the FULL FRAME ({_w}x{_h})")
    caps = {}
    for ch in ("Phase", "Fluor"):
        m = G.movie(b, ch, role)
        if m: caps[ch] = m
    if not caps:
        print(f"   {b} {role}: no readable movie -- skipped"); return None

    w = int(round(box[2] - box[0])); h = int(round(box[3] - box[1]))
    scale = min(1.0, 520.0 / max(w, h))
    tw, th = int(w * scale), int(h * scale)
    ncol = len(caps)
    out_w, out_h = tw * ncol + 6 * (ncol - 1), th
    path = os.path.join(OUT, f"{cat}__{b.replace(' ', '_')}__{role.lower()}.mp4")
    vw = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*"mp4v"), FPS[role], (out_w, out_h))
    t0 = float(ts[0])
    n = 0
    # USER 2026-08-17: monitoring clips are "trimmed to about 30 seconds following the annotated
    # cytokinesis timepoint if applicable". TRIM_AFTER is filled per batch by the deck-movie driver from
    # the master's Cytokinesis Onset (falling back to Anaphase Onset); an absent entry means no trim, so
    # this is inert for every existing caller.
    _cut = TRIM_AFTER.get(b) if role != "Ablation" else None
    _times = sorted(float(x) for x in ts)
    if _cut is not None:
        _kept = [x for x in _times if x <= _cut]
        if len(_kept) >= 5: _times = _kept
    for i, t in enumerate(_times):
        tiles = []
        for ch in ("Phase", "Fluor"):
            if ch not in caps: continue
            cap, cts = caps[ch]
            fi = int(np.argmin(np.abs(np.asarray(cts) - t)))
            cap.set(cv2.CAP_PROP_POS_FRAMES, fi)
            ok, fr = cap.read()
            tile = (cv2.resize(crop_to(fr, box), (tw, th), interpolation=cv2.INTER_AREA)
                    if ok and fr is not None else np.zeros((th, tw, 3), np.uint8))
            tiles.append(tile)
        row = tiles[0] if len(tiles) == 1 else np.hstack(
            [tiles[0], np.full((th, 6, 3), 20, np.uint8), tiles[1]])
        fs = max(0.45, th / 620.0)
        lab = hms(t - t0)
        cv2.putText(row, lab, (8, int(24 * fs) + 6), FONT, fs, (0, 0, 0), max(3, int(4 * fs)), cv2.LINE_AA)
        cv2.putText(row, lab, (8, int(24 * fs) + 6), FONT, fs, (255, 255, 255), max(1, int(2 * fs)), cv2.LINE_AA)
        vw.write(row); n += 1
    vw.release()
    for ch in caps: caps[ch][0].release()
    px = G.ps(b)
    print(f"   {cat:30s} {role:10s} {n:4d} frames  crop {w}x{h}px ({w*px:.1f} um)  -> {os.path.basename(path)}")
    return path, n, box


def main():
    made = []
    for cat, b in BATCHES:
        print(f"{b}")
        for role in ("Ablation", "Monitoring"):
            r = build(cat, b, role)
            if r: made.append((cat, b, role) + r)
    print(f"\n{len(made)} movies -> {OUT}")
    if made:
        lib.record_plot("revised_movies_20260811",
                        ["category", "batch", "role", "file", "n_frames", "crop_x0", "crop_y0", "crop_x1", "crop_y1"],
                        [[c, b, r, os.path.basename(p), n, box[0], box[1], box[2], box[3]]
                         for c, b, r, p, n, box in made],
                        {"kind": "cropped movies matching the revised timestrips",
                         "crop": "group_timestrips.portion_box(batch, role) -- the same ROI the strips use",
                         "content": "brightfield | fluor side by side where both exist",
                         "fps": FPS},
                        __file__,
                        "Ablation and monitoring movies for the cdc20 strips on REVISED_TIMESTRIPS, cropped "
                        "to the same ROI as their timestrips.",
                        key_column="batch")


if __name__ == "__main__":
    main()
