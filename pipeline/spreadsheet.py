"""Write a tracking spreadsheet matching Ablation_Analysis format.

Auto-fills columns A-M and Extended Metadata. User Input / Calculated / Placeholder
columns are left blank for manual annotation.
"""
import csv
import os
import numpy as np
from datetime import datetime


# Row 1: category labels
CATEGORIES = [
    'Auto', 'Auto', 'Auto', 'Auto', 'Auto', 'Auto', 'Auto', 'Auto', 'Auto',
    'Auto', 'Auto', 'Auto',
    'User Input', 'User Input', 'User Input', 'User Input', 'User Input',
    'User Input', 'User Input', 'User Input', 'User Input', 'User Input',
    'User Input', 'User Input', 'User Input', 'User Input', 'User Input',
    'User Input', 'User Input', 'User Input', 'User Input', 'User Input',
    'Calculated', 'Calculated', 'Calculated', 'Calculated',
    'Calculated', 'Calculated', 'Calculated', 'Calculated',
    'Placeholder', 'Placeholder', 'Placeholder', 'Placeholder',
    'Placeholder', 'Placeholder', 'Placeholder',
    '',  # empty separator
    'Extended Metadata', 'Extended Metadata', 'Extended Metadata',
    'Extended Metadata', 'Extended Metadata', 'Extended Metadata',
    'Extended Metadata', 'Extended Metadata', 'Extended Metadata',
    'Extended Metadata', 'Extended Metadata', 'Extended Metadata',
    'Extended Metadata', 'Extended Metadata', 'Extended Metadata',
    'Extended Metadata', 'Extended Metadata', 'Extended Metadata',
    'Extended Metadata', 'Extended Metadata',
]

# Row 2: column headers
HEADERS = [
    # Auto (A-M)
    'Batch Name', 'Date', '# Files', 'First Ablation (s)',
    '# Unique Targets', 'Total Frames', 'Time Interval (s)', 'Pixel Size (um)',
    'Dropped Frames', 'Dropped %', '% Post-Ablation', 'Time Jitter (ms)',
    # User Input (N-AG)
    'On-Target / Off-Target', 'Phase of Ablations', 'Ablation Success',
    'Spindle Damage', 'Stage at Ablation', '# Sisterless KTs',
    'NEB Time (s)', 'First Congression (s)', 'Metaphase Start (s)',
    'Anaphase Onset (s)', 'Cytokinesis Onset (s)', 'Healthy Anaphase',
    'Polar Chromosomes', 'Lagging Chromosomes', 'Cell Fate',
    'Binucleated Daughter', 'Micronuclei', 'Condition', 'Exclude', 'Exclude Reason',
    # Calculated (AH-AO)
    'Ablation->Meta (s)', 'Meta Duration (s)', 'NEB->Meta (s)', 'Total Mitosis (s)',
    'Ablation->Meta (min)', 'Meta Duration (min)', 'NEB->Meta (min)', 'Total Mitosis (min)',
    # Placeholder (AP-AV)
    'Sisterless KT Brightness', 'Background Brightness', 'Paired KT Brightness',
    'Sisterless Dist from Pole', 'Paired Dist from Pole', 'Targeted Chromo Length', 'Notes',
    # Separator
    '',
    # Extended Metadata (AX-BQ)
    'Total Duration (s)', 'Last Ablation (s)', 'Ablation Span (s)',
    '# Marker Frames', 'Log Ablation Events', '1st Event Delta (s)',
    'Pre-Ablation Fluor', 'Post-Ablation Fluor', 'Fluor Change (%)',
    'Baseline Fluor', 'Crop ROI (x,y,w,h)', 'Crop FOV Width (um)',
    'Crop FOV Height (um)', 'Crop Start Frame', '# Cropped Frames',
    'Has Fluor2', 'Alternating', 'Source Files', 'Processing Time (min)',
    'Drive Path',
]


def init_spreadsheet(output_dir, date_str):
    """Create or return path to the tracking spreadsheet."""
    path = os.path.join(output_dir, date_str, f'{date_str}_processing_log.csv')
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not os.path.isfile(path):
        with open(path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(CATEGORIES)
            writer.writerow(HEADERS)
    return path


def count_unique_targets(events, radius_px=5):
    """Count unique ablation targets by clustering nearby XY positions."""
    if not events:
        return 0
    targets = []
    for ev in events:
        matched = False
        for t in targets:
            if abs(ev.x_px - t[0]) <= radius_px and abs(ev.y_px - t[1]) <= radius_px:
                matched = True
                break
        if not matched:
            targets.append((ev.x_px, ev.y_px))
    return len(targets)


def compute_timing_stats(frame_times_ms, interval_ms):
    """Compute dropped frames and time jitter from frame timestamps.

    Returns (dropped_count, dropped_pct, jitter_ms).
    """
    if not frame_times_ms or len(frame_times_ms) < 2:
        return 0, 0.0, 0.0

    intervals = np.diff(frame_times_ms)
    expected = interval_ms if interval_ms and interval_ms > 0 else np.median(intervals)

    # A frame is "dropped" if the interval is > 1.5x expected
    threshold = expected * 1.5
    dropped = int(np.sum(intervals > threshold))
    dropped_pct = dropped / len(frame_times_ms) * 100

    # Jitter = std deviation of intervals
    jitter = float(np.std(intervals))

    return dropped, dropped_pct, jitter


def log_batch(csv_path, batch, result):
    """Append a row for a completed (or failed) batch."""
    meta = batch.meta
    events = result.get('ablation_events_list', [])
    frame_times = result.get('frame_times_ms', [])
    total_frames = result.get('total_frames', 0)
    elapsed = result.get('elapsed', 0)

    # Auto columns A-M
    n_files = result.get('total_files', 0)
    n_events = len(events)
    interval_s = (meta.interval_ms / 1000) if meta and meta.interval_ms else ''
    pixel_size = meta.pixel_size_um if meta else ''

    # First ablation time relative to first frame
    first_abl_s = ''
    if events and frame_times:
        first_abl_s = f'{(events[0].epoch_ms - frame_times[0]) / 1000:.2f}'

    unique_targets = count_unique_targets(events)

    # Dropped frames and jitter
    dropped, dropped_pct, jitter = 0, 0.0, 0.0
    if frame_times and meta and meta.interval_ms:
        dropped, dropped_pct, jitter = compute_timing_stats(frame_times, meta.interval_ms)

    # % post-ablation
    post_abl_pct = ''
    if events and frame_times and total_frames > 0:
        first_event_ms = events[0].epoch_ms
        post_frames = sum(1 for t in frame_times if t >= first_event_ms)
        post_abl_pct = f'{post_frames / total_frames * 100:.1f}'

    # Extended metadata
    total_duration_s = ''
    if frame_times and len(frame_times) >= 2:
        total_duration_s = f'{(frame_times[-1] - frame_times[0]) / 1000:.2f}'

    last_abl_s = ''
    abl_span_s = ''
    if events and frame_times:
        last_abl_s = f'{(events[-1].epoch_ms - frame_times[0]) / 1000:.2f}'
        if len(events) > 1:
            abl_span_s = f'{(events[-1].epoch_ms - events[0].epoch_ms) / 1000:.2f}'

    marker_frames = result.get('marker_frames', 0)
    first_event_delta = ''
    if events and frame_times:
        first_event_delta = f'{(events[0].epoch_ms - frame_times[0]) / 1000:.1f}'

    pre_fluor = result.get('pre_ablation_fluor', '')
    post_fluor = result.get('post_ablation_fluor', '')
    fluor_change = ''
    if pre_fluor and post_fluor and pre_fluor > 0:
        fluor_change = f'{(post_fluor - pre_fluor) / pre_fluor * 100:.2f}'
    baseline_fluor = result.get('baseline_fluor', '')

    roi = result.get('roi', None)
    crop_roi_str = f'{roi.x},{roi.y},{roi.w},{roi.h}' if roi else ''
    crop_fov_w = f'{roi.w * pixel_size:.1f}' if roi and pixel_size else ''
    crop_fov_h = f'{roi.h * pixel_size:.1f}' if roi and pixel_size else ''

    # Source files
    source_files = '; '.join(result.get('source_files', []))
    drive_path = result.get('output_dir', '')

    # Build row matching HEADERS order
    row = [
        # Auto A-M
        batch.name,
        batch.date_str,
        n_files,
        first_abl_s,
        unique_targets,
        total_frames,
        interval_s,
        pixel_size,
        dropped,
        f'{dropped_pct:.1f}' if dropped_pct else '0.0',
        post_abl_pct,
        f'{jitter:.1f}',
        # User Input N-AG (20 blank columns)
        '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '',
        # Calculated AH-AO (8 blank — computed from user input)
        '', '', '', '', '', '', '', '',
        # Placeholder AP-AV (7 blank)
        '', '', '', '', '', '', '',
        # Separator
        '',
        # Extended Metadata AX-BQ
        total_duration_s,
        last_abl_s,
        abl_span_s,
        marker_frames,
        len(events),
        first_event_delta,
        f'{pre_fluor:.2f}' if isinstance(pre_fluor, (int, float)) else '',
        f'{post_fluor:.2f}' if isinstance(post_fluor, (int, float)) else '',
        fluor_change,
        f'{baseline_fluor:.2f}' if isinstance(baseline_fluor, (int, float)) else '',
        crop_roi_str,
        crop_fov_w,
        crop_fov_h,
        '',  # Crop Start Frame
        total_frames,
        'No',  # Has Fluor2
        'No',  # Alternating
        source_files,
        f'{elapsed / 60:.1f}',
        drive_path,
    ]

    with open(csv_path, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(row)
