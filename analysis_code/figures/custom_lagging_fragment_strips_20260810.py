#!/usr/bin/env python3
"""Fragmenting-laggard timestrips: one frame per minute from anaphase, with whole-cell context above.

USER 2026-08-10:
  (2) "Generate more of the fractured lagging timestrips - but in the one you just made you jumped from
       8mins to 31mins for some reason?? By 31 mins the event is over. You should look at the first trace
       for the lagging that falls after the start of anaphase and take a frame for the timestrip once every
       minute or so"
  (3) "do include frames above showing the corresponding brightfield and fluor for the cell, and then place
       a little box on the frames for where the zoom for the polar or paired or lagging, etc is coming from"

WHAT WENT WRONG BEFORE. The old strip sampled by EVENT, not by time: it took the first post-anaphase outline
(8.0 min) and then the frames around maximum stretch (30.4 / 31.0 / 31.4 min), so it skipped the entire
fragmentation and showed only its aftermath. Its own recorded data says exactly that -- t_min_after_anaphase
= 8.02, 30.35, 31.02, 31.35. Frames are now chosen on the CLOCK: the first traced lagging outline at or
after anaphase onset, then the next one at least MIN_GAP_S later, walking forward.

FRAME MAPPING -- the thing that would have silently ruined this. An outline's `frame` equals the frames.json
`idx`, but the two files' `t_sec` do NOT share an origin: on 20250910 triple_ablation_collagen_22 they differ
by a constant 1960 s. Joining on time would have pulled frames ~33 min away while looking perfectly healthy.
So the join is on `frame`, per her standing rule, and the movie index is that record's position within its
own role. Master event times (anaphase onset) are in the ANNOTATION base and are only ever compared with
outline t_sec, never with frames.json.

LAYOUT. Three rows: brightfield whole-cell, fluor whole-cell, fluor zoom. A yellow box on both context rows
marks exactly the region the zoom below is cut from -- drawn from the same rectangle used to make the crop,
so it cannot drift out of agreement with it.
"""
import sys, os, csv, json, glob, collections
sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import numpy as np, cv2
import lib, ts_render

csv.field_size_limit(10 ** 9)
ANN = "/Volumes/4 MB/annotations"
OUT = os.environ.get("KTFIG_OUT") or "/Volumes/4 MB/ablation_figures_20260625/group5"
RELINK = "/Volumes/4 MB/ablation_figures_20260625/_ai_relink/pdf"
os.makedirs(OUT, exist_ok=True); os.makedirs(RELINK, exist_ok=True)

MIN_GAP_S = 55.0        # "once every minute or so" -- 55 s so a 60 s cadence is not skipped by rounding
MAX_COLS = 16        # enough columns at a 1-min cadence to reach the fragmentation, not just the run-up
ZOOM_UM = 16.0          # laggards here stretch to 7.7 um; 16 um leaves margin at both ends
CTX_UM = 46.0           # whole-cell context
TILE = 320              # every tile rendered at this size so the three rows align
FONT = cv2.FONT_HERSHEY_SIMPLEX

data, _ = lib.load_master(); MR = {r["Batch Name"]: r for r in data}
def T(b, c): return lib.parse_time((MR.get(b, {}) or {}).get(c, ""))
def ps(b):
    try: return float((MR.get(b, {}) or {}).get("Pixel Size (um)", "") or 0.062)
    except Exception: return 0.062

_RD = {}
def render_dir(b):
    if b in _RD: return _RD[b]
    _RD[b] = None
    for p in glob.glob(f"/Volumes/4 MB/**/{b}_frames.json", recursive=True):
        if "_ARCHIVED" in p or "backup" in p.lower(): continue
        _RD[b] = os.path.dirname(p); break
    return _RD[b]

_FJ = {}
def fj(b):
    if b in _FJ: return _FJ[b]
    d = render_dir(b)
    _FJ[b] = json.load(open(f"{d}/{b}_frames.json")) if d else None
    return _FJ[b]

def movie_index(b, frame_no):
    """(role, index within that role's movie) for an outline `frame`, via frames.json idx. None if absent."""
    j = fj(b)
    if not j: return None
    rec = None
    for f in j["frames"]:
        if f["idx"] == frame_no: rec = f; break
    if rec is None: return None
    same = [f for f in j["frames"] if f["role"] == rec["role"]]
    same.sort(key=lambda f: f["idx"])
    for i, f in enumerate(same):
        if f["idx"] == frame_no: return (rec["role"], i)
    return None

_CAP = {}
def cap_for(b, ch, role):
    key = (b, ch, role)
    if key in _CAP: return _CAP[key]
    d = render_dir(b)
    p = f"{d}/{b}_{ch}_{role.capitalize()}.mp4" if d else None
    _CAP[key] = cv2.VideoCapture(p) if (p and os.path.isfile(p) and os.path.getsize(p) > 1000) else None
    return _CAP[key]

def frame_at(b, ch, role, idx):
    c = cap_for(b, ch, role)
    if c is None: return None
    c.set(cv2.CAP_PROP_POS_FRAMES, int(idx))
    ok, fr = c.read()
    # strip the burned-in channel name / timestamp / scale bar before any cropping
    return ts_render.drop_burnin(fr) if ok else None

def crop(img, box):
    x0, y0, x1, y1 = [int(round(v)) for v in box]
    h, w = img.shape[:2]
    bw, bh = x1 - x0, y1 - y0
    out = np.zeros((bh, bw, 3), np.uint8)
    sx0, sy0 = max(0, x0), max(0, y0)
    sx1, sy1 = min(w, x1), min(h, y1)
    if sx1 > sx0 and sy1 > sy0:
        out[sy0 - y0:sy0 - y0 + (sy1 - sy0), sx0 - x0:sx0 - x0 + (sx1 - sx0)] = img[sy0:sy1, sx0:sx1]
    return out

def square(cx, cy, side):
    h = side / 2.0
    return (cx - h, cy - h, cx + h, cy + h)


EDGE_MARGIN_UM = 3.0    # keep the context window this far inside the frame

def square_inside(cx, cy, side, W, H, margin_px):
    """A square window that never touches the frame edge.

    USER 2026-08-10: "pull that context crop in ~3 um so it stops touching the edge". The 46 um context box
    ran off the bottom of the 1248x1056 frame, and everything outside was fill -- first black, then (after
    the burn-in mask became a row-replicate) a smear. Neither is data. The window is now slid inside the
    frame, and only shrunk if the frame genuinely cannot hold it, so the tiles stay the same size wherever
    possible and the strip keeps one magnification.
    """
    side = min(side, W - 2 * margin_px, H - 2 * margin_px)
    h = side / 2.0
    cx = min(max(cx, margin_px + h), W - margin_px - h)
    cy = min(max(cy, margin_px + h), H - margin_px - h)
    return (cx - h, cy - h, cx + h, cy + h)

def stretch(img, lo_p=2, hi_p=99.6, green=False):
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img.ndim == 3 else img
    lo, hi = np.percentile(g, lo_p), np.percentile(g, hi_p)
    if hi - lo < 3: hi = lo + 3
    v = np.clip((g.astype(np.float32) - lo) * 255.0 / (hi - lo), 0, 255).astype(np.uint8)
    if green:
        o = np.zeros((*v.shape, 3), np.uint8); o[..., 1] = v; return o
    return cv2.cvtColor(v, cv2.COLOR_GRAY2BGR)

# ---- outlines -------------------------------------------------------------------------------------
tracks = collections.defaultdict(list)
percell_frame = collections.defaultdict(list)
for r in csv.DictReader(open(f"{ANN}/KT_OUTLINE_TRACKS_20260723.csv")):
    if not r["t_sec"] or not r["frame"].isdigit(): continue
    try:
        rec = dict(b=r["batch"], trk=r["track_id"], label=r["label"], frame=int(r["frame"]),
                   t=float(r["t_sec"]), cx=float(r["cx_px"]), cy=float(r["cy_px"]),
                   npx=int(r["n_pieces"] or 1), major=float(r["major_um"] or 0))
    except Exception:
        continue
    percell_frame[(rec["b"], rec["frame"])].append(rec)
    if r["label"] == "lagging": tracks[(rec["b"], rec["trk"])].append(rec)


def candidates(min_pieces=3, top=6):
    out = []
    for (b, trk), rs in tracks.items():
        ana = T(b, "Anaphase Onset (s)")
        if ana is None: continue
        post = sorted([x for x in rs if x["t"] >= ana], key=lambda x: x["t"])
        if len(post) < 3: continue
        mp = max(x["npx"] for x in post)
        if mp < min_pieces: continue
        out.append((mp, len(post), b, trk, ana, post))
    out.sort(key=lambda x: (-x[0], -x[1]))
    return out[:top]


def pick_frames(post, ana):
    """First traced outline at/after anaphase, then the next at least MIN_GAP_S later.

    The peak-fragmentation frame is then guaranteed to be present. A pure clock walk capped at 10 columns
    ran out at +10.3 min on 20260416 single ablation_15 and every column read 1-2 pieces -- the strip
    covered the run-up and stopped just before the event it exists to show. The cadence is still hers; this
    only makes sure the frame with the most pieces is one of the columns.
    """
    sel = [post[0]]
    for x in post[1:]:
        if x["t"] - sel[-1]["t"] >= MIN_GAP_S:
            sel.append(x)
        if len(sel) >= MAX_COLS: break
    peak = max(post, key=lambda x: (x["npx"], x["major"]))
    if peak["frame"] not in {y["frame"] for y in sel}:
        sel.append(peak)
        sel.sort(key=lambda x: x["t"])
    return sel


def build(b, trk, ana, post):
    pxs = ps(b)
    zoom_px = ZOOM_UM / pxs
    ctx_px = CTX_UM / pxs
    sel = pick_frames(post, ana)
    if len(sel) < 3: return None
    cols = []
    for x in sel:
        mi = movie_index(b, x["frame"])
        if mi is None: continue
        role, idx = mi
        ph = frame_at(b, "Phase", role, idx)
        fl = frame_at(b, "Fluor", role, idx)
        if ph is None and fl is None: continue
        peers = percell_frame.get((b, x["frame"]), [])
        ccx = float(np.mean([p["cx"] for p in peers])) if peers else x["cx"]
        ccy = float(np.mean([p["cy"] for p in peers])) if peers else x["cy"]
        _fh, _fw = (ph if ph is not None else fl).shape[:2]
        # ...but never less than the burn-in band itself: 3 um is 48 px while the overlay band is 64 px, so a
        # 3 um margin still let the window dip into the replicated rows (fine streaking along the bottom).
        _mg = max(EDGE_MARGIN_UM / pxs, float(getattr(ts_render, "BURNIN_PX", 64)))
        cbox = square_inside(ccx, ccy, ctx_px, _fw, _fh, _mg)
        zbox = square(x["cx"], x["cy"], zoom_px)
        # the zoom rectangle in CONTEXT-crop coordinates -- derived from the same zbox that makes the crop
        rx0, ry0 = zbox[0] - cbox[0], zbox[1] - cbox[1]
        rx1, ry1 = zbox[2] - cbox[0], zbox[3] - cbox[1]
        sc = TILE / float(cbox[2] - cbox[0])

        def ctx(img, green):
            if img is None: return np.zeros((TILE, TILE, 3), np.uint8)
            t = cv2.resize(crop(stretch(img, green=green), cbox), (TILE, TILE), interpolation=cv2.INTER_AREA)
            cv2.rectangle(t, (int(rx0 * sc), int(ry0 * sc)), (int(rx1 * sc), int(ry1 * sc)),
                          (0, 225, 255), 2, cv2.LINE_AA)
            return t

        z = (cv2.resize(crop(stretch(fl, green=True), zbox), (TILE, TILE), interpolation=cv2.INTER_NEAREST)
             if fl is not None else np.zeros((TILE, TILE, 3), np.uint8))
        cols.append(dict(ph=ctx(ph, False), fl=ctx(fl, True), zm=z,
                         t=(x["t"] - ana) / 60.0, npc=x["npx"], major=x["major"]))
    if len(cols) < 3: return None

    HDR = 26
    rows = []
    # USER 2026-08-10: no channel names on frames. The two context rows go unlabelled; the zoom row keeps
    # its label because it states the WINDOW SIZE, not a channel.
    for key, lab in (("ph", ""), ("fl", ""), ("zm", f"zoom {ZOOM_UM:.0f} um")):
        strip = np.hstack([c[key] for c in cols])
        gut = np.full((TILE, 96, 3), 20, np.uint8)
        _w = lab.split()                      # empty for the unlabelled context rows
        if _w:
            cv2.putText(gut, _w[0], (5, TILE // 2), FONT, 0.76, (235, 235, 235), 2, cv2.LINE_AA)
            if len(_w) > 1:
                cv2.putText(gut, " ".join(_w[1:]), (5, TILE // 2 + 26), FONT, 0.65, (170, 170, 170), 2, cv2.LINE_AA)
        rows.append(np.hstack([gut, strip]))
        rows.append(np.full((3, 96 + strip.shape[1], 3), 16, np.uint8))
    fig = np.vstack(rows[:-1])
    hdr = np.full((HDR, fig.shape[1], 3), 16, np.uint8)
    for i, c in enumerate(cols):
        cv2.putText(hdr, f"+{c['t']:.1f} min  {c['npc']}pc", (96 + i * TILE + 5, 18),
                    FONT, 0.80, (240, 240, 240), 2, cv2.LINE_AA)
    fig = np.vstack([hdr, fig])
    bar = int(round(5.0 / pxs * (TILE / (ZOOM_UM / pxs))))
    x1 = fig.shape[1] - 12; x0 = x1 - bar; y = fig.shape[0] - 12
    cv2.rectangle(fig, (x0, y - 5), (x1, y), (255, 255, 255), -1)
    cv2.putText(fig, "5 um", (x0, y - 8), FONT, 0.68, (255, 255, 255), 2, cv2.LINE_AA)
    return fig, cols


def main():
    cands = candidates()
    print(f"{len(cands)} fragmenting laggards selected\n")
    made = []
    for mp, npost, b, trk, ana, post in cands:
        r = build(b, trk, ana, post)
        if r is None:
            print(f"  SKIP {b[:44]} {trk.split('|')[-1]}: could not build"); continue
        fig, cols = r
        nm = "G5_lagfrag_" + b.replace(" ", "_") + "_t" + trk.split("|")[-1]
        cv2.imwrite(os.path.join(OUT, nm + ".png"), fig)
        made.append(nm)
        print(f"  {b[:42]:43s} trk {trk.split('|')[-1]:>3s}  {len(cols):2d} cols  "
              f"+{cols[0]['t']:.1f}..{cols[-1]['t']:.1f} min  max {mp} pieces  -> {nm}")
        lib.record_plot(nm, ["batch", "track", "t_min_after_anaphase", "n_pieces", "major_um"],
                        [[b, trk, round(c["t"], 2), c["npc"], round(c["major"], 3)] for c in cols],
                        {"kind": "fragmenting-laggard timestrip with whole-cell context",
                         "sampling": f"first traced lagging outline at/after anaphase onset, then >= {MIN_GAP_S:.0f} s apart",
                         "rows": "brightfield context / fluor context / fluor zoom",
                         "zoom_um": ZOOM_UM, "context_um": CTX_UM,
                         "box": "yellow rectangle on the context rows marks the zoom region",
                         "frame_join": "outline.frame == frames.json idx (t_sec origins differ by a constant)"},
                        __file__,
                        f"Lagging kinetochore fragmenting after anaphase, {b}, one frame per minute.",
                        source=[f"{ANN}/KT_OUTLINE_TRACKS_20260723.csv"], key_column="batch")
    print(f"\n{len(made)} strips -> {OUT}")


if __name__ == "__main__":
    main()
