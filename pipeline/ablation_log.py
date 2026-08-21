"""Parse PointAndShoot.log to extract ablation event coordinates and times."""
import os
import re
from datetime import datetime
from dataclasses import dataclass


@dataclass
class AblationEvent:
    epoch_ms: float  # absolute time in milliseconds
    x_px: float      # X coordinate in full-image pixels
    y_px: float      # Y coordinate in full-image pixels


def parse_log(log_path):
    """Parse a PointAndShoot.log file.

    Format: datetime<tab>x_px<tab>y_px
    e.g.: 2026-04-20 23:59:01.633	874	494

    Returns list of AblationEvent objects.
    """
    if not os.path.isfile(log_path):
        return []

    events = []
    with open(log_path, 'r', errors='replace') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            event = _parse_line(line)
            if event:
                events.append(event)

    return events


def _parse_line(line):
    """Try to parse a single log line into an AblationEvent."""
    parts = line.split('\t')
    if len(parts) >= 3:
        x_str = parts[-2].strip()
        y_str = parts[-1].strip()
        time_str = '\t'.join(parts[:-2]).strip()

        try:
            x = float(x_str)
            y = float(y_str)
        except ValueError:
            return None

        # Try datetime format: 2026-04-20 23:59:01.633
        epoch_ms = _parse_datetime_ms(time_str)
        if epoch_ms is not None:
            return AblationEvent(epoch_ms=epoch_ms, x_px=x, y_px=y)

        # Try numeric ms timestamp
        try:
            t = float(time_str)
            return AblationEvent(epoch_ms=t, x_px=x, y_px=y)
        except ValueError:
            pass

    return None


def _parse_datetime_ms(s):
    """Parse a datetime string to epoch milliseconds."""
    for fmt in ('%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%d %H:%M:%S'):
        try:
            dt = datetime.strptime(s, fmt)
            return dt.timestamp() * 1000
        except ValueError:
            continue
    return None


def assign_events_to_frames(events, frame_times_ms):
    """Map ablation events to the frame they occurred in.

    frame_times_ms: list of frame timestamps in ms (from TIF metadata).
    Returns dict mapping frame_index -> list of AblationEvent.
    """
    if not events or not frame_times_ms:
        return {}

    result = {}
    for event in events:
        # Find the frame whose time window contains this event
        best_frame = 0
        best_diff = abs(event.epoch_ms - frame_times_ms[0])
        for i, ft in enumerate(frame_times_ms):
            diff = abs(event.epoch_ms - ft)
            if diff < best_diff:
                best_diff = diff
                best_frame = i

        if best_frame not in result:
            result[best_frame] = []
        result[best_frame].append(event)

    return result
