"""Re-render a batch's MP4 videos from its cached cropped TIFs + frames.json.

Usage:
    python3 rerender_from_cropped.py <batch_dir>
    python3 rerender_from_cropped.py <date_dir>     # all batches under date
    python3 rerender_from_cropped.py <root> --all   # every batch under root

Avoids re-reading source TIFs from external drives. ~10–100× faster than full
pipeline run for cosmetic-only changes (channel labels, overlays, contrast).
"""
import argparse
import json
import os
import sys

import numpy as np
import tifffile
import cv2

from process import (
    CropROI,
    colorize_green,
    draw_ablation_marker,
    draw_scale_bar,
    draw_timestamp,
    normalize_uint8,
    _transcode_to_h264,
)


def _format_ts(t_sec):
    sign = "-" if t_sec < 0 else ""
    a = abs(t_sec)
    return f"{sign}{int(a // 3600):02d}:{int((a % 3600) // 60):02d}:{int(a % 60):02d}"


def _label_for(role, channel_kind, ch_names, fluor_ch, phase_ch):
    """Top-right channel label. channel_kind = 'phase' or 'fluor'."""
    if channel_kind == 'phase':
        if phase_ch is not None and phase_ch < len(ch_names):
            return ch_names[phase_ch].upper()
        return "PHASE"
    if fluor_ch is not None and fluor_ch < len(ch_names):
        return ch_names[fluor_ch].upper()
    return "FLUOR"


def rerender_batch(batch_dir):
    """Re-emit the 6 MP4s for one batch from cached cropped TIFs + frames.json."""
    bname = os.path.basename(batch_dir.rstrip(os.sep))
    json_path = os.path.join(batch_dir, f'{bname}_frames.json')
    phase_tif = os.path.join(batch_dir, f'{bname}_Phase_Cropped.tif')
    fluor_tif = os.path.join(batch_dir, f'{bname}_Fluor_Cropped.tif')

    if not os.path.isfile(json_path):
        print(f"  SKIP {bname}: no frames.json (re-run pipeline first to emit it)")
        return False
    with open(json_path) as f:
        meta = json.load(f)

    fps = int(meta['fps'])
    roi = CropROI(**meta['roi'])
    pixel_size_um = meta.get('pixel_size_um')
    ch_names = meta.get('ch_names', [])
    fluor_ch = meta.get('fluor_ch')
    phase_ch = meta.get('phase_ch')
    fluor_low, fluor_high = meta['fluor_contrast']
    phase_low, phase_high = meta['phase_contrast']
    ablation_events = meta.get('ablation_events_local', [])
    frames = meta['frames']
    has_phase = meta.get('has_phase', True)
    has_fluor = meta.get('has_fluor', True)

    # Open cropped TIF readers once
    p_reader = tifffile.TiffFile(phase_tif) if has_phase and os.path.isfile(phase_tif) else None
    f_reader = tifffile.TiffFile(fluor_tif) if has_fluor and os.path.isfile(fluor_tif) else None

    # Build per-frame ablation marker index (frames already keyed by abs idx in JSON)
    # The pipeline previously matched events by frame_in_file within ablation file.
    # Reconstruct the same: for each ablation-role frame, find events whose epoch_ms
    # falls between this frame's t_sec and next.
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    size = (roi.w, roi.h)
    writers = {}
    _kinds = ['Phase_Pre', 'Fluor_Pre', 'Phase_Ablation', 'Fluor_Ablation', 'Phase_Monitoring', 'Fluor_Monitoring']
    if any(fm.get('role') == 'zstack' for fm in frames):   # z-stack snapshots have their own outputs
        _kinds += ['Phase_Zstack', 'Fluor_Zstack']
    for kind in _kinds:
        path = os.path.join(batch_dir, f'{bname}_{kind}.mp4')
        writers[kind] = cv2.VideoWriter(path, fourcc, fps, size)

    phase_label = _label_for(None, 'phase', ch_names, fluor_ch, phase_ch)
    fluor_label = _label_for(None, 'fluor', ch_names, fluor_ch, phase_ch)

    # ---- ablation markers: choose ONE frame PER CHANNEL per event ------------------------------------
    # USER 2026-07-22: "sometimes they contain ablation markers only on the phase movie or only on the 488
    # movie. It should be on both."  Cause: phase and fluor are sampled at different rates, so a frame can
    # carry a phase page and no fluor page. The old code tested one shared tolerance against the frame's
    # t_sec and drew on whichever channels that frame happened to have -- so an event landing on a
    # phase-only frame marked phase alone. Now each channel picks its OWN nearest frame independently, so
    # every event is marked once in EVERY channel that exists.
    _mark = {}                       # (id(frame_dict), 'phase'|'fluor') -> [events]
    if ablation_events:
        _anchor_ms = min(e['epoch_ms'] for e in ablation_events)
        _abl = [fm for fm in frames if fm.get('role') == 'ablation']
        for _ch, _key in (('phase', 'phase_tif_idx'), ('fluor', 'fluor_tif_idx')):
            _cand = [fm for fm in _abl if fm.get(_key) is not None]
            if not _cand:
                continue
            for _ev in ablation_events:
                _t = (_ev['epoch_ms'] - _anchor_ms) / 1000.0
                _best = min(_cand, key=lambda fm: abs(fm['t_sec'] - _t))
                _mark.setdefault((id(_best), _ch), []).append(_ev)

    for fm in frames:
        role = fm['role']
        t_sec = fm['t_sec']
        ts_text = _format_ts(t_sec)

        # Read phase / fluor pages from cropped TIFs
        phase_rgb = None
        fluor_rgb = None
        if fm.get('phase_tif_idx') is not None and p_reader is not None:
            phase_raw = p_reader.pages[fm['phase_tif_idx']].asarray()
            phase_8 = normalize_uint8(phase_raw, phase_low, phase_high)
            phase_rgb = np.stack([phase_8] * 3, axis=-1)
        if fm.get('fluor_tif_idx') is not None and f_reader is not None:
            fluor_raw = f_reader.pages[fm['fluor_tif_idx']].asarray()
            fluor_8 = normalize_uint8(fluor_raw, fluor_low, fluor_high)
            fluor_rgb = colorize_green(fluor_8)

        # Overlays
        if phase_rgb is not None:
            draw_timestamp(phase_rgb, ts_text)
            draw_timestamp(phase_rgb, "HH:MM:SS", position=(10, 60))
            draw_scale_bar(phase_rgb, pixel_size_um)
            draw_timestamp(phase_rgb, phase_label, position=(roi.w - 220, 30))
        if fluor_rgb is not None:
            draw_timestamp(fluor_rgb, ts_text)
            draw_timestamp(fluor_rgb, "HH:MM:SS", position=(10, 60))
            draw_scale_bar(fluor_rgb, pixel_size_um)
            draw_timestamp(fluor_rgb, fluor_label, position=(roi.w - 220, 30))

        # Ablation markers: drawn on the frame chosen per channel above (see _mark).
        if role == 'ablation' and ablation_events:
            for _ev in _mark.get((id(fm), 'phase'), []):
                if phase_rgb is not None:
                    draw_ablation_marker(phase_rgb, _ev['x_px'], _ev['y_px'], roi, pixel_size_um)
            for _ev in _mark.get((id(fm), 'fluor'), []):
                if fluor_rgb is not None:
                    draw_ablation_marker(fluor_rgb, _ev['x_px'], _ev['y_px'], roi, pixel_size_um)

        # Write to role-appropriate writers
        role_cap = {'pre': 'Pre', 'ablation': 'Ablation', 'monitoring': 'Monitoring', 'zstack': 'Zstack'}[role]
        if phase_rgb is not None:
            writers[f'Phase_{role_cap}'].write(phase_rgb)
        if fluor_rgb is not None:
            writers[f'Fluor_{role_cap}'].write(fluor_rgb)

    for kind, w in writers.items():
        w.release()
    if p_reader is not None: p_reader.close()
    if f_reader is not None: f_reader.close()

    # Transcode to H.264 for browser playback
    for kind in writers:
        _transcode_to_h264(os.path.join(batch_dir, f'{bname}_{kind}.mp4'))

    print(f"  OK  {bname}: {len(frames)} frames re-rendered")
    return True


def find_batches(root):
    """Yield batch dirs (any dir with a *_frames.json inside)."""
    for d in sorted(os.listdir(root)):
        sub = os.path.join(root, d)
        if not os.path.isdir(sub):
            continue
        # Direct batch dir?
        if any(f.endswith('_frames.json') for f in os.listdir(sub)):
            yield sub
            continue
        # Date dir containing batches
        for b in sorted(os.listdir(sub)):
            bd = os.path.join(sub, b)
            if os.path.isdir(bd) and any(f.endswith('_frames.json') for f in os.listdir(bd)):
                yield bd


def main():
    p = argparse.ArgumentParser()
    p.add_argument('target', help='Batch dir, date dir, or root with --all')
    p.add_argument('--all', action='store_true', help='Walk all batches under target')
    args = p.parse_args()

    if args.all:
        batches = list(find_batches(args.target))
    elif os.path.isdir(args.target) and any(
        f.endswith('_frames.json') for f in os.listdir(args.target)
    ):
        batches = [args.target]
    else:
        # treat as date dir
        batches = [
            os.path.join(args.target, b)
            for b in sorted(os.listdir(args.target))
            if os.path.isdir(os.path.join(args.target, b))
            and any(f.endswith('_frames.json') for f in os.listdir(os.path.join(args.target, b)))
        ]

    if not batches:
        print(f"No batches with frames.json found under {args.target}")
        sys.exit(1)

    print(f"Re-rendering {len(batches)} batches...")
    ok = 0
    for b in batches:
        try:
            if rerender_batch(b):
                ok += 1
        except Exception as e:
            print(f"  ERR {os.path.basename(b)}: {e}")
    print(f"\n{ok}/{len(batches)} batches re-rendered.")


if __name__ == '__main__':
    main()
