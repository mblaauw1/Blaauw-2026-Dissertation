"""Small shared compositor for the 'pick-from-candidates' slides.

Stacks several already-rendered timestrip PNGs into ONE image, each with a clear batch-name
header bar above it so the user can eyeball the candidates and pick the best. Pure raster
(cv2) — no matplotlib, no re-rendering; it only reads the per-candidate .png the timestrip
scripts already wrote. Used by group_timestrips.py (unmanip candidates) and
group_frap_timestrips.py (FRAP candidates).
"""
import cv2, numpy as np

def _header(width, text, h=46):
    bar = np.full((h, width, 3), 245, np.uint8)          # light strip
    cv2.rectangle(bar, (0, 0), (width - 1, h - 1), (210, 210, 210), 1)
    cv2.putText(bar, text, (14, int(h * 0.68)), cv2.FONT_HERSHEY_SIMPLEX,
                0.8, (20, 20, 20), 2, cv2.LINE_AA)
    return bar

def compose(items, out_path, sup_title=None, pad=18, bg=255):
    """items: list of (label, png_path). Stacks each PNG under a batch-name header bar.
    Missing/unreadable PNGs are skipped. Returns the number of candidates composed."""
    tiles = []
    for label, path in items:
        img = cv2.imread(path)
        if img is None:
            print(f"  compose: MISSING {path}")
            continue
        tiles.append((label, img))
    if not tiles:
        print("  compose: nothing to compose"); return 0
    W = max(img.shape[1] for _, img in tiles)
    W = max(W, 640)
    rows = []
    if sup_title:
        rows.append(_header(W, sup_title, h=60))
        rows.append(np.full((pad, W, 3), bg, np.uint8))
    for label, img in tiles:
        rows.append(_header(W, label))
        if img.shape[1] < W:                             # centre-pad narrower strips
            left = (W - img.shape[1]) // 2
            img = cv2.copyMakeBorder(img, 0, 0, left, W - img.shape[1] - left,
                                     cv2.BORDER_CONSTANT, value=(bg, bg, bg))
        rows.append(img)
        rows.append(np.full((pad, W, 3), bg, np.uint8))
    canvas = np.vstack(rows)
    cv2.imwrite(out_path, canvas)
    print(f"  compose: {len(tiles)} candidates -> {out_path} ({canvas.shape[1]}x{canvas.shape[0]})")
    return len(tiles)
