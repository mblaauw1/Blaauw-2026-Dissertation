"""Frame processing: read TIFs, separate channels, crop, normalize, overlay.

Single-pass: read frame, process, write. No multi-pass architecture.
"""
import os
import json
import subprocess
import numpy as np
from dataclasses import dataclass

from metadata import TifMeta, read_tif_meta
from ablation_log import parse_log, assign_events_to_frames, AblationEvent
from discover import _folder_number


def read_channel_settings(tif_path, ch_names):
    """For each channel name, find the first page that uses it and capture
    imaging settings (exposure, binning, emission filter, filter cube).

    Returns dict: channel_name -> {exposure_ms, binning, emission_filter, cube}
    Missing fields are simply omitted from the per-channel dict.
    """
    import tifffile
    result = {}
    try:
        with tifffile.TiffFile(tif_path) as t:
            for pi in range(len(t.pages)):
                tag = t.pages[pi].tags.get('MicroManagerMetadata')
                if not tag:
                    continue
                v = tag.value
                pm = json.loads(v) if isinstance(v, (bytes, str)) else v
                if not isinstance(pm, dict):
                    continue
                ci = pm.get('ChannelIndex')
                if ci is None or ci >= len(ch_names):
                    continue
                name = ch_names[ci]
                if name in result:
                    continue
                settings = {}
                if 'Exposure-ms' in pm:
                    try: settings['exposure_ms'] = float(pm['Exposure-ms'])
                    except Exception: settings['exposure_ms'] = pm['Exposure-ms']
                # Prefer human-readable "2x2" over int "2"
                if 'HamamatsuHam_DCAM-Binning' in pm:
                    settings['binning'] = pm['HamamatsuHam_DCAM-Binning']
                elif 'Binning' in pm:
                    settings['binning'] = pm['Binning']
                if 'Wheel-A-Label' in pm:
                    settings['emission_filter'] = pm['Wheel-A-Label']
                if 'TIFilterBlock1-Label' in pm:
                    settings['cube'] = pm['TIFilterBlock1-Label']
                result[name] = settings
                if len(result) >= len(ch_names):
                    break
    except Exception:
        pass
    return result


def sanitize_channel_name(name):
    """Convert a channel name to a filename-safe identifier.
    '488 (GFP)'    -> '488_GFP'
    '561(mCherry)' -> '561_mCherry'
    '640 (Cy5)'    -> '640_Cy5'
    'Brightfield'  -> 'Brightfield'
    """
    import re
    return re.sub(r'[^A-Za-z0-9]+', '_', name).strip('_')


def _get_ffmpeg():
    """Find ffmpeg binary (imageio-ffmpeg or system)."""
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        pass
    import shutil
    return shutil.which('ffmpeg')


def _transcode_to_h264(mp4_path):
    """Re-encode mp4v to H.264 in-place for browser compatibility.

    Kept for backwards compatibility / rerender_from_cropped tool. The main pipeline
    now uses FFmpegVideoWriter and skips this step.
    """
    ffmpeg = _get_ffmpeg()
    if not ffmpeg:
        return
    tmp = mp4_path + '.h264.mp4'
    try:
        subprocess.run(
            [ffmpeg, '-i', mp4_path, '-c:v', 'libx264', '-pix_fmt', 'yuv420p',
             '-crf', '23', '-movflags', '+faststart', '-y', tmp],
            capture_output=True, check=True)
        os.remove(mp4_path)
        os.rename(tmp, mp4_path)
    except Exception:
        if os.path.exists(tmp):
            os.remove(tmp)


class FFmpegVideoWriter:
    """Drop-in replacement for cv2.VideoWriter that pipes raw BGR frames directly
    to ffmpeg encoding H.264 — half the encoding work of the cv2-mp4v + transcode
    pipeline. write(bgr_frame) accepts H×W×3 uint8 arrays.

    libx264 requires even width and height; this class transparently pads odd
    dimensions by a single pixel before writing.
    """
    def __init__(self, path, size, fps):
        self.path = path
        w, h = size
        self._pad_x = w % 2          # 1 if odd width, else 0
        self._pad_y = h % 2          # 1 if odd height, else 0
        self._enc_w = w + self._pad_x
        self._enc_h = h + self._pad_y
        self.size = (self._enc_w, self._enc_h)
        self.fps = max(1, int(fps))
        self._proc = None
        self._stderr_path = path + '.ffmpeg.log'
        self._frames_written = 0

    def _start(self):
        ffmpeg = _get_ffmpeg()
        if not ffmpeg:
            return False
        cmd = [
            ffmpeg, '-y',
            '-f', 'rawvideo', '-pix_fmt', 'bgr24',
            '-s', f'{self._enc_w}x{self._enc_h}', '-r', str(self.fps),
            '-i', '-',
            '-c:v', 'libx264', '-pix_fmt', 'yuv420p',
            '-crf', '23', '-preset', 'fast',
            '-movflags', '+faststart',
            self.path,
        ]
        self._stderr_fh = open(self._stderr_path, 'wb')
        self._proc = subprocess.Popen(
            cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=self._stderr_fh
        )
        return True

    def write(self, frame):
        if self._proc is None:
            if not self._start():
                return
        # Pad odd dimensions if needed (libx264 requires even W/H)
        if self._pad_x or self._pad_y:
            frame = np.pad(
                frame,
                ((0, self._pad_y), (0, self._pad_x), (0, 0)),
                mode='constant',
            )
        try:
            self._proc.stdin.write(frame.tobytes())
            self._frames_written += 1
        except BrokenPipeError:
            pass

    def release(self):
        if self._proc is None:
            # No frames written — emit a tiny stub so is_batch_done logic stays consistent
            with open(self.path, 'wb') as f:
                f.write(b'\x00' * 257)
            return
        try:
            self._proc.stdin.close()
        except Exception:
            pass
        self._proc.wait()
        try:
            self._stderr_fh.close()
        except Exception:
            pass
        # Clean up the empty stderr log on success
        try:
            if os.path.getsize(self._stderr_path) == 0:
                os.remove(self._stderr_path)
        except OSError:
            pass
        self._proc = None



@dataclass
class CropROI:
    x: int
    y: int
    w: int
    h: int


def compute_mid_crop(width, height):
    """Compute the crop region: full FOV minus edge margins.

    Reference: 415,53,1248,1056 on a 2048x1152 sensor.
    Scales proportionally for other sensor sizes.
    """
    # Reference crop on 2048x1152
    REF_W, REF_H = 2048, 1152
    REF_X, REF_Y, REF_CW, REF_CH = 415, 53, 1248, 1056

    x = int(round(REF_X * width / REF_W))
    y = int(round(REF_Y * height / REF_H))
    cw = int(round(REF_CW * width / REF_W))
    ch = int(round(REF_CH * height / REF_H))
    return CropROI(x=x, y=y, w=cw, h=ch)


def crop_frame(frame, roi):
    """Apply crop ROI to a 2D frame. Always returns exactly (roi.h, roi.w);
    if a (shifted) ROI runs off the frame, the missing border is zero-padded."""
    H, W = frame.shape[:2]
    x0, y0 = roi.x, roi.y
    sx0, sy0 = max(0, x0), max(0, y0)
    sx1, sy1 = min(W, x0 + roi.w), min(H, y0 + roi.h)
    if sx0 == x0 and sy0 == y0 and sx1 == x0 + roi.w and sy1 == y0 + roi.h:
        return frame[y0:y0 + roi.h, x0:x0 + roi.w]
    out = np.zeros((roi.h, roi.w) + frame.shape[2:], dtype=frame.dtype)
    if sx1 > sx0 and sy1 > sy0:
        out[sy0 - y0:sy1 - y0, sx0 - x0:sx1 - x0] = frame[sy0:sy1, sx0:sx1]
    return out


def normalize_uint8(frame, low, high):
    """Normalize a 16-bit frame to uint8 using given contrast limits."""
    if high <= low:
        return np.zeros(frame.shape, dtype=np.uint8)
    clipped = np.clip(frame.astype(np.float32), low, high)
    scaled = ((clipped - low) / (high - low) * 255).astype(np.uint8)
    return scaled


def compute_contrast(frames_sample, percentile_low=0.5, percentile_high=99.5):
    """Compute contrast limits from a sample of frames.

    Returns (low, high) pixel values.
    """
    if not frames_sample:
        return 0, 65535
    combined = np.concatenate([f.ravel() for f in frames_sample])
    low = np.percentile(combined, percentile_low)
    high = np.percentile(combined, percentile_high)
    return float(low), float(high)


def sample_frames_from_tif(tif_path, meta, channel_idx, n_samples=10):
    """Read a sparse sample of frames from a TIF for contrast estimation.

    For fluor channel: max intensity projection across z-slices.
    For phase channel: middle z-slice.
    Uses per-page metadata to find correct channel pages.
    """
    import tifffile
    frames = []
    is_fluor = (channel_idx == meta.fluor_ch)
    with tifffile.TiffFile(tif_path) as t:
        n_pages = len(t.pages)
        n_ch = meta.n_channels
        n_sl = meta.n_slices

        # Build page index from metadata
        from collections import defaultdict as _dd
        frames_by_idx = _dd(list)
        for pi in range(n_pages):
            tag = t.pages[pi].tags.get('MicroManagerMetadata')
            if tag:
                pm = json.loads(tag.value) if isinstance(tag.value, (bytes, str)) else tag.value
                if isinstance(pm, dict):
                    ci = pm.get('ChannelIndex', 0)
                    si = pm.get('SliceIndex', 0)
                    fi = pm.get('FrameIndex', pi // (n_ch * n_sl))
                    frames_by_idx[fi].append((pi, ci, si))
                    continue
            stride = n_ch * n_sl
            fi = pi // stride
            rem = pi % stride
            ci = rem // n_sl
            si = rem % n_sl
            frames_by_idx[fi].append((pi, ci, si))

        sorted_frames = sorted(frames_by_idx.keys())
        step = max(1, len(sorted_frames) // n_samples)
        for fi in sorted_frames[::step]:
            pages = frames_by_idx[fi]
            ch_pages = [(pi, si) for pi, ci, si in pages if ci == channel_idx]
            ch_pages.sort(key=lambda x: x[1])
            if not ch_pages:
                continue
            if is_fluor and len(ch_pages) > 1:
                frame = np.max(
                    np.stack([t.pages[pi].asarray() for pi, _ in ch_pages]),
                    axis=0)
                frames.append(frame)
            else:
                mid = ch_pages[len(ch_pages) // 2]
                frames.append(t.pages[mid[0]].asarray())
            if len(frames) >= n_samples:
                break
    return frames


def read_start_time_ms(tif_path):
    """Read the acquisition start time as epoch ms from TIF Summary metadata."""
    import tifffile
    from datetime import datetime
    with tifffile.TiffFile(tif_path) as t:
        summary = t.micromanager_metadata
        if summary and 'Summary' in summary:
            st = summary['Summary'].get('StartTime', '')
            if st:
                # Format: "2026-04-20 23:29:26.225 -0700"
                for fmt in ('%Y-%m-%d %H:%M:%S.%f %z', '%Y-%m-%d %H:%M:%S %z',
                            '%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%d %H:%M:%S'):
                    try:
                        dt = datetime.strptime(st, fmt)
                        return dt.timestamp() * 1000
                    except ValueError:
                        continue
    return None


def read_frame_times(tif_path, meta):
    """Read per-frame timestamps (in ms) from TIF metadata.

    Returns elapsed times in ms relative to acquisition start.
    """
    import tifffile
    times = []
    with tifffile.TiffFile(tif_path) as t:
        for i in range(0, len(t.pages), meta.n_channels * meta.n_slices):
            tag = t.pages[i].tags.get('MicroManagerMetadata') if i < len(t.pages) else None
            if tag:
                v = tag.value
                pm = json.loads(v) if isinstance(v, (bytes, str)) else v
                if isinstance(pm, dict):
                    elapsed = pm.get('ElapsedTime-ms')
                    if elapsed is not None:
                        times.append(float(elapsed))
                        continue
            # Fallback: estimate from interval
            times.append(len(times) * (meta.interval_ms or 20000))
    return times


def draw_ablation_marker(frame_rgb, x_px, y_px, roi, pixel_size_um=0.062,
                         color=(0, 0, 255), thickness=2):
    """Draw a circle at the ablation point on an RGB frame.

    Circle diameter = 1 µm. x_px, y_px are in full-image coordinates.
    """
    # 1 µm diameter -> 0.5 µm radius -> radius in pixels.
    # Guard against missing pixel-size metadata (use default ~0.062 µm/px).
    if not pixel_size_um or pixel_size_um <= 0:
        pixel_size_um = 0.062
    radius = max(3, int(round(0.5 / pixel_size_um)))

    cx = int(x_px - roi.x)
    cy = int(y_px - roi.y)

    if 0 <= cx < frame_rgb.shape[1] and 0 <= cy < frame_rgb.shape[0]:
        h, w = frame_rgb.shape[:2]
        yy, xx = np.ogrid[:h, :w]
        dist = (xx - cx) ** 2 + (yy - cy) ** 2
        outer = dist <= (radius + thickness) ** 2
        inner = dist <= radius ** 2
        ring = outer & ~inner
        frame_rgb[ring] = color
    return frame_rgb


def draw_timestamp(frame_rgb, text, position=(10, 30)):
    """Draw timestamp text on frame."""
    try:
        import cv2
        # Black outline for readability
        cv2.putText(frame_rgb, text, position, cv2.FONT_HERSHEY_SIMPLEX,
                    0.9, (0, 0, 0), 3, cv2.LINE_AA)
        cv2.putText(frame_rgb, text, position, cv2.FONT_HERSHEY_SIMPLEX,
                    0.9, (255, 255, 255), 2, cv2.LINE_AA)
    except ImportError:
        pass
    return frame_rgb


def draw_scale_bar(frame_rgb, pixel_size_um, bar_um=10, position='bottom_right'):
    """Draw a scale bar on the frame."""
    if not pixel_size_um or pixel_size_um <= 0:
        return frame_rgb
    bar_px = int(bar_um / pixel_size_um)
    h, w = frame_rgb.shape[:2]
    margin = 15
    bar_thickness = 5
    y = h - margin - bar_thickness
    x_end = w - margin
    x_start = x_end - bar_px
    if x_start < 0:
        return frame_rgb
    frame_rgb[y:y + bar_thickness, x_start:x_end] = (255, 255, 255)
    # Label
    try:
        import cv2
        label = f"{bar_um} um"
        cv2.putText(frame_rgb, label, (x_start, y - 6),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 3, cv2.LINE_AA)
        cv2.putText(frame_rgb, label, (x_start, y - 6),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2, cv2.LINE_AA)
    except ImportError:
        pass
    return frame_rgb


def colorize_green(frame_8bit):
    """Convert grayscale to green RGB."""
    rgb = np.zeros((*frame_8bit.shape, 3), dtype=np.uint8)
    rgb[:, :, 1] = frame_8bit
    return rgb


def make_overlay(phase_8bit, fluor_rgb):
    """Phase as grey base + additive fluor overlay."""
    phase_rgb = np.stack([phase_8bit] * 3, axis=-1)
    # Additive blend, clamped
    combined = np.clip(phase_rgb.astype(np.int16) + fluor_rgb.astype(np.int16), 0, 255)
    return combined.astype(np.uint8)


def process_batch(batch, output_dir):
    """Process a single batch: read all TIFs, crop, write output.

    Ablation file comes first, then monitoring files are stitched after.
    """
    import tifffile
    import cv2

    meta = batch.meta
    if meta is None:
        print(f"  ERROR: No metadata for batch {batch.name}")
        return {'status': 'ERROR: no metadata'}

    roi = compute_mid_crop(meta.width, meta.height)

    # All ablation acquisitions for this cell (a cell may be ablated more than once).
    abl_acqs = batch.ablations if getattr(batch, 'ablations', None) else (
        [batch.ablation] if batch.ablation else [])

    # Collect all TIF files ordered chronologically by acquisition folder number, so a
    # twice-ablated cell renders as one continuous timeline: pre -> abl1 -> mon -> abl2 -> mon.
    ordered_acqs = ([('pre', a) for a in batch.pre_monitoring]
                    + [('ablation', a) for a in abl_acqs]
                    + [('monitoring', a) for a in batch.monitoring])
    ordered_acqs.sort(key=lambda ra: _folder_number(os.path.basename(ra[1].folder_path)))
    # Single-timepoint z-stack snapshots are NOT monitoring time-lapses: render them into their own
    # _Zstack outputs (role='zstack') AFTER the timeline, so their z-slices never masquerade as
    # monitoring frames (bug 2026-07-15, e.g. 20251021 coverslip3_14). Empty for most batches.
    ordered_acqs += [('zstack', a) for a in getattr(batch, 'zstacks', [])]
    all_files = []
    for role, acq in ordered_acqs:
        for tif in acq.tif_files:
            all_files.append((role, os.path.join(acq.folder_path, tif)))

    if not all_files:
        print(f"  ERROR: No TIF files for batch {batch.name}")
        return {'status': 'ERROR: no TIF files'}

    # Per-file channel detection: a batch can mix files with different channel
    # layouts (e.g., single-channel ablation file paired with 2-channel pre-monitoring).
    # Each file's TifMeta has its own phase_ch / fluor_ch detected by name.
    file_metas = {}
    has_phase = False
    has_fluor = False
    last_read_error = None
    for _, path in all_files:
        try:
            fm = read_tif_meta(path)
            if fm is not None:
                file_metas[path] = fm
                if fm.phase_ch is not None: has_phase = True
                if fm.fluor_ch is not None: has_fluor = True
        except Exception as e:
            last_read_error = e

    # Distinguish: no files readable (I/O error, drive flake) vs channels not named
    if not file_metas:
        print(f"  ERROR: Could not read metadata from any file in {batch.name}")
        print(f"    last error: {last_read_error}")
        return {'status': f'ERROR: read metadata failed ({last_read_error})'}

    if not has_fluor and not has_phase:
        print(f"  ERROR: Could not detect channels for {batch.name}")
        print(f"    ChNames: {meta.ch_names}")
        return {'status': 'ERROR: channel detection failed'}

    mode = "single-channel" if not (has_fluor and has_phase) else "dual-channel"
    print(f"  Channels [{mode}]: per-file (any phase={has_phase}, any fluor={has_fluor})")
    print(f"  Crop: {roi.w}x{roi.h} at ({roi.x},{roi.y}), pixel size: {meta.pixel_size_um} µm/px")

    # Compute contrast from sample across all files, using each file's own indices
    print(f"  Computing contrast from {len(all_files)} files...")
    fluor_samples = []
    phase_samples = []
    for _, path in all_files[:5]:
        try:
            fm = file_metas.get(path) or meta
            if fm.fluor_ch is not None:
                fluor_samples.extend(sample_frames_from_tif(path, fm, fm.fluor_ch, 5))
            if fm.phase_ch is not None:
                phase_samples.extend(sample_frames_from_tif(path, fm, fm.phase_ch, 5))
        except Exception:
            pass
    fluor_low, fluor_high = compute_contrast(fluor_samples, percentile_low=0.5, percentile_high=99.5) if has_fluor else (0, 65535)
    # Brightfield/phase often has a tighter dynamic range; use slightly wider percentiles
    phase_low, phase_high = compute_contrast(phase_samples, percentile_low=2.0, percentile_high=98.0) if has_phase else (0, 65535)
    print(f"  Contrast: fluor=[{fluor_low:.0f}, {fluor_high:.0f}], phase=[{phase_low:.0f}, {phase_high:.0f}]")

    # Multi-channel: discover ALL fluor channel names across the batch (deduped).
    # The "primary" fluor goes into the existing _Fluor_*.mp4. Any EXTRA fluors get
    # their own _<channel_name>_<role>.mp4 videos so 3+ channel batches don't lose data.
    from metadata import _FLUOR as _FLUOR_KW
    all_ch_names = []
    for fm in file_metas.values():
        for ch in fm.ch_names:
            if ch not in all_ch_names:
                all_ch_names.append(ch)
    all_fluor_ch_names = [c for c in all_ch_names if any(kw in c.lower() for kw in _FLUOR_KW)]
    # Primary fluor = first per-file detected fluor channel name (whichever file).
    primary_fluor_name = None
    for fm in file_metas.values():
        if fm.fluor_ch is not None and fm.fluor_ch < len(fm.ch_names):
            primary_fluor_name = fm.ch_names[fm.fluor_ch]
            break
    extra_fluor_names = [c for c in all_fluor_ch_names if c != primary_fluor_name]
    if extra_fluor_names:
        print(f"  Extra fluor channels: {extra_fluor_names} (will emit additional videos)")

    # Per-extra-channel contrast (sample from any file that has the channel)
    extra_contrast = {}  # ch_name -> (low, high)
    for ch_name in extra_fluor_names:
        samples = []
        for _, path in all_files[:5]:
            fm = file_metas.get(path)
            if fm and ch_name in fm.ch_names:
                idx = fm.ch_names.index(ch_name)
                try:
                    samples.extend(sample_frames_from_tif(path, fm, idx, 5))
                except Exception:
                    pass
        extra_contrast[ch_name] = compute_contrast(samples, 0.5, 99.5) if samples else (0, 65535)
        lo, hi = extra_contrast[ch_name]
        print(f"  Contrast: {ch_name}=[{lo:.0f}, {hi:.0f}]")

    # Parse ablation log(s) — one per ablation acquisition (a cell may be ablated twice).
    # Keep a per-folder map so each acquisition's events are matched to its OWN frames,
    # and a combined epoch-sorted list for the global anchor / sidecar.
    events_by_folder = {}
    ablation_events = []
    for acq in abl_acqs:
        evs = parse_log(os.path.join(acq.folder_path, 'PointAndShoot.log'))
        events_by_folder[acq.folder_path] = evs
        ablation_events.extend(evs)
    ablation_events.sort(key=lambda e: e.epoch_ms)
    if ablation_events:
        print(f"  Ablation log(s): {len(ablation_events)} events across {len(abl_acqs)} ablation(s)")

    # Set up output writers
    os.makedirs(output_dir, exist_ok=True)
    # Estimate total frames to target ~20s video duration
    est_frames = 0
    for _, path in all_files:
        try:
            fm = read_tif_meta(path) or meta
            est_frames += fm.n_frames
        except Exception:
            est_frames += 50  # rough guess
    fps = max(1, min(60, int(round(est_frames / 20.0))))
    print(f"  Estimated {est_frames} frames, fps={fps} for ~20s video")

    size = (roi.w, roi.h)

    # Separate pre-monitoring, ablation, and monitoring MP4s (H.264 direct)
    phase_pre_writer = FFmpegVideoWriter(
        os.path.join(output_dir, f'{batch.name}_Phase_Pre.mp4'), size, fps)
    fluor_pre_writer = FFmpegVideoWriter(
        os.path.join(output_dir, f'{batch.name}_Fluor_Pre.mp4'), size, fps)
    phase_abl_writer = FFmpegVideoWriter(
        os.path.join(output_dir, f'{batch.name}_Phase_Ablation.mp4'), size, fps)
    fluor_abl_writer = FFmpegVideoWriter(
        os.path.join(output_dir, f'{batch.name}_Fluor_Ablation.mp4'), size, fps)
    phase_mon_writer = FFmpegVideoWriter(
        os.path.join(output_dir, f'{batch.name}_Phase_Monitoring.mp4'), size, fps)
    fluor_mon_writer = FFmpegVideoWriter(
        os.path.join(output_dir, f'{batch.name}_Fluor_Monitoring.mp4'), size, fps)
    # z-stack snapshot writers (only when the batch actually has z-stacks — no empty stubs otherwise)
    _has_zstacks = bool(getattr(batch, 'zstacks', []))
    phase_zstack_writer = fluor_zstack_writer = None
    if _has_zstacks:
        phase_zstack_writer = FFmpegVideoWriter(
            os.path.join(output_dir, f'{batch.name}_Phase_Zstack.mp4'), size, fps)
        fluor_zstack_writer = FFmpegVideoWriter(
            os.path.join(output_dir, f'{batch.name}_Fluor_Zstack.mp4'), size, fps)

    # TIF stacks (raw cropped, no annotations)
    phase_tif = tifffile.TiffWriter(
        os.path.join(output_dir, f'{batch.name}_Phase_Cropped.tif'), bigtiff=True)
    fluor_tif = tifffile.TiffWriter(
        os.path.join(output_dir, f'{batch.name}_Fluor_Cropped.tif'), bigtiff=True)

    # Extra-fluor writers + cropped TIFs (one set per additional fluor channel)
    extra_writers = {}   # (ch_name, role_cap) -> FFmpegVideoWriter
    extra_tifs = {}      # ch_name -> tifffile.TiffWriter
    extra_tif_idx = {}   # ch_name -> running TIF page index
    for ch_name in extra_fluor_names:
        safe = sanitize_channel_name(ch_name)
        for r in ('Pre', 'Ablation', 'Monitoring') + (('Zstack',) if _has_zstacks else ()):
            p = os.path.join(output_dir, f'{batch.name}_{safe}_{r}.mp4')
            extra_writers[(ch_name, r)] = FFmpegVideoWriter(p, size, fps)
        p = os.path.join(output_dir, f'{batch.name}_{safe}_Cropped.tif')
        extra_tifs[ch_name] = tifffile.TiffWriter(p, bigtiff=True)
        extra_tif_idx[ch_name] = 0

    # Process all files — collect frame times and fluor intensities for stats
    # Get ablation start time as reference for global timestamps
    abl_start_ms = None
    if abl_acqs and abl_acqs[0].tif_files:
        abl_start_ms = read_start_time_ms(
            os.path.join(abl_acqs[0].folder_path, abl_acqs[0].tif_files[0]))

    # Anchor displayed timestamps at the first ablation event when available,
    # so frames before the event show negative time. Otherwise anchor at the
    # ablation acquisition start (or stay raw for non-ablation batches).
    timestamp_anchor_ms = 0
    if ablation_events and abl_start_ms is not None:
        # file_frame_times are stored relative to abl_start_ms, so the first
        # event's offset within that frame-time space is its epoch minus abl_start_ms
        timestamp_anchor_ms = ablation_events[0].epoch_ms - abl_start_ms

    total_frames = 0
    pre_frames = 0
    abl_frames = 0
    mon_frames = 0
    zstack_frames = 0
    all_frame_times_ms = []
    all_fluor_means = []
    marker_frames = 0
    source_filenames = []
    # Per-frame metadata for the frames.json sidecar (lets us re-render videos
    # from the cached cropped TIFs without re-reading source TIFs).
    frames_meta = []
    # Per-source-file summary for slideshow captions ("interval 3s, z=9 slices...")
    source_file_summaries = []
    phase_tif_idx = 0
    fluor_tif_idx = 0

    for file_idx, (role, tif_path) in enumerate(all_files):
        fname = os.path.basename(tif_path)
        source_filenames.append(fname)
        print(f"  [{file_idx+1}/{len(all_files)}] {role}: {fname}")

        # Per-source crop ROI: supports a registration crop-shift so a monitoring
        # sweep at a re-registered stage position stays centered on the SAME cell.
        # batch.crop_shifts = {source_filename: (dx_px, dy_px)}  (applied to this file only)
        _shift = getattr(batch, 'crop_shifts', None)
        _shift = _shift.get(fname) if _shift else None
        file_roi = CropROI(roi.x + int(round(_shift[0])), roi.y + int(round(_shift[1])),
                           roi.w, roi.h) if _shift else roi

        try:
            # Read per-file metadata for correct n_slices (may differ from ablation)
            file_meta = read_tif_meta(tif_path) or meta
            # Capture per-file summary for slideshow captions
            source_file_summaries.append({
                'source': fname,
                'role': role,
                'n_frames': file_meta.n_frames,
                'n_slices': file_meta.n_slices,
                'n_channels': file_meta.n_channels,
                'interval_ms': file_meta.interval_ms,
                'channels': list(file_meta.ch_names),
                'phase_ch': file_meta.phase_ch,
                'fluor_ch': file_meta.fluor_ch,
                'is_z_stack': (file_meta.n_frames <= 1 and file_meta.n_slices > 1),
                'channel_settings': read_channel_settings(tif_path, file_meta.ch_names),
            })
            with tifffile.TiffFile(tif_path) as t:
                n_pages = len(t.pages)
                n_ch = file_meta.n_channels
                n_sl = file_meta.n_slices

                # Compute global frame times relative to ablation start
                file_frame_times = read_frame_times(tif_path, file_meta)
                file_start_ms = read_start_time_ms(tif_path)
                if abl_start_ms and file_start_ms and file_frame_times:
                    # Convert to global time: file_start offset + per-frame elapsed
                    global_offset = file_start_ms - abl_start_ms
                    file_frame_times = [ft + global_offset for ft in file_frame_times]
                elif all_frame_times_ms and file_frame_times:
                    # Fallback: cumulative from last file
                    time_offset = all_frame_times_ms[-1] + (meta.interval_ms or 20000)
                    if file_frame_times[0] < all_frame_times_ms[-1]:
                        file_frame_times = [ft + time_offset - file_frame_times[0] for ft in file_frame_times]
                all_frame_times_ms.extend(file_frame_times)

                # Ablation event assignment: match THIS acquisition's own events to
                # its frames (a twice-ablated cell has two ablation files, each with
                # its own log — don't cross-assign).
                file_events = events_by_folder.get(os.path.dirname(tif_path), [])
                if role == 'ablation' and file_events and file_frame_times:
                    # Use per-file elapsed times for event matching
                    local_times = read_frame_times(tif_path, file_meta)
                    start_ms = read_start_time_ms(tif_path)
                    if start_ms is not None:
                        relative_events = []
                        for ev in file_events:
                            relative_events.append(AblationEvent(
                                epoch_ms=ev.epoch_ms - start_ms,
                                x_px=ev.x_px, y_px=ev.y_px))
                        event_map = assign_events_to_frames(relative_events, local_times)
                    else:
                        event_map = assign_events_to_frames(file_events, local_times)
                else:
                    event_map = {}

                # Build per-page index from metadata tags
                page_info = []  # list of (ch_idx, sl_idx, frame_idx) per page
                for pi in range(n_pages):
                    tag = t.pages[pi].tags.get('MicroManagerMetadata')
                    if tag:
                        pm = json.loads(tag.value) if isinstance(tag.value, (bytes, str)) else tag.value
                        if isinstance(pm, dict):
                            page_info.append((
                                pm.get('ChannelIndex', 0),
                                pm.get('SliceIndex', 0),
                                pm.get('FrameIndex', pi // (n_ch * n_sl)),
                            ))
                            continue
                    # Fallback: assume CZ order
                    stride = n_ch * n_sl
                    fi = pi // stride
                    rem = pi % stride
                    ci = rem // n_sl
                    si = rem % n_sl
                    page_info.append((ci, si, fi))

                # Detect z-stack acquisition (single time point, many z-slices):
                # render as a scrub-through-z movie where each z-slice is a frame.
                is_z_stack = (file_meta.n_frames <= 1 and file_meta.n_slices > 1)

                from collections import defaultdict as _dd
                if is_z_stack:
                    # Group pages by SliceIndex so each output frame = one z-slice
                    iter_groups = _dd(list)
                    for pi, (ci, si, fi) in enumerate(page_info):
                        iter_groups[si].append((pi, ci, fi))
                    iter_keys = sorted(iter_groups.keys())
                    # Pre-pick a fallback page per channel for slices that lack that channel
                    # (common case: phase is a single "reference snapshot" at the middle z
                    # while fluor sweeps every slice — without this, phase video would be
                    # 1 frame and out of sync with the multi-slice fluor video).
                    zstack_fallback = {}
                    if file_meta.phase_ch is not None:
                        for pi, (ci, _, _) in enumerate(page_info):
                            if ci == file_meta.phase_ch:
                                zstack_fallback['phase'] = pi
                                break
                    if file_meta.fluor_ch is not None:
                        for pi, (ci, _, _) in enumerate(page_info):
                            if ci == file_meta.fluor_ch:
                                zstack_fallback['fluor'] = pi
                                break
                    print(f"    z-stack: {len(iter_keys)} slices (fallback pages: {zstack_fallback})")
                else:
                    iter_groups = _dd(list)
                    for pi, (ci, si, fi) in enumerate(page_info):
                        iter_groups[fi].append((pi, ci, si))
                    iter_keys = sorted(iter_groups.keys())
                    zstack_fallback = {}

                frame_in_file = 0
                for key in iter_keys:
                    pages = iter_groups[key]
                    # pages = (pi, ci, si)  for time-series; (pi, ci, fi) for z-stack

                    # Find phase
                    phase_raw = None
                    if file_meta.phase_ch is not None:
                        phase_pages = [(pi, sub_idx) for pi, ci, sub_idx in pages if ci == file_meta.phase_ch]
                        if phase_pages:
                            if is_z_stack:
                                phase_raw = t.pages[phase_pages[0][0]].asarray()
                            else:
                                phase_pages.sort(key=lambda x: x[1])
                                phase_mid = phase_pages[len(phase_pages) // 2]
                                phase_raw = t.pages[phase_mid[0]].asarray()
                        elif is_z_stack and 'phase' in zstack_fallback:
                            # z-stack slice lacking phase → reuse file's phase reference
                            # (common: 1 phase snapshot at middle z, many fluor slices)
                            phase_raw = t.pages[zstack_fallback['phase']].asarray()

                    # Find fluor: max projection across z (time-series) or single slice (z-stack)
                    fluor_raw = None
                    if file_meta.fluor_ch is not None:
                        fluor_pages = [(pi, sub_idx) for pi, ci, sub_idx in pages if ci == file_meta.fluor_ch]
                        if fluor_pages:
                            if is_z_stack:
                                fluor_raw = t.pages[fluor_pages[0][0]].asarray()
                            elif len(fluor_pages) > 1:
                                fluor_raw = np.max(
                                    np.stack([t.pages[pi].asarray() for pi, _ in fluor_pages]),
                                    axis=0)
                            else:
                                fluor_raw = t.pages[fluor_pages[0][0]].asarray()
                        elif is_z_stack and 'fluor' in zstack_fallback:
                            fluor_raw = t.pages[zstack_fallback['fluor']].asarray()

                    # Need at least one channel's data to make a frame
                    if phase_raw is None and fluor_raw is None:
                        continue

                    # Crop (use whichever channel exists as fallback for video frame shape)
                    fluor_crop = crop_frame(fluor_raw, file_roi) if fluor_raw is not None else None
                    phase_crop = crop_frame(phase_raw, file_roi) if phase_raw is not None else None

                    # Track fluor intensity for spreadsheet stats
                    if fluor_crop is not None:
                        all_fluor_means.append(float(np.mean(fluor_crop)))

                    # Write raw cropped TIFs (only for present channels);
                    # record per-frame metadata so we can re-render later from cache.
                    frame_phase_idx = None
                    frame_fluor_idx = None
                    if fluor_crop is not None:
                        fluor_tif.write(fluor_crop)
                        frame_fluor_idx = fluor_tif_idx
                        fluor_tif_idx += 1
                    if phase_crop is not None:
                        phase_tif.write(phase_crop)
                        frame_phase_idx = phase_tif_idx
                        phase_tif_idx += 1

                    # Normalize for video — emit black frame for missing channel so video shape matches
                    if fluor_crop is not None:
                        fluor_8 = normalize_uint8(fluor_crop, fluor_low, fluor_high)
                        fluor_rgb = colorize_green(fluor_8)
                    else:
                        fluor_rgb = None
                    if phase_crop is not None:
                        phase_8 = normalize_uint8(phase_crop, phase_low, phase_high)
                        phase_rgb = np.stack([phase_8] * 3, axis=-1)
                    else:
                        phase_rgb = None

                    # Compute the frame's wall-clock time relative to the first
                    # ablation event (or to acquisition start if no events).
                    # For z-stacks all slices share the file's single time point;
                    # display shows "z=NN" but the recorded t_sec stays real.
                    if file_frame_times:
                        # z-stack uses the single file-level time point; time-series uses per-frame
                        t_index = 0 if is_z_stack else min(frame_in_file, len(file_frame_times) - 1)
                        t_sec = (file_frame_times[t_index] - timestamp_anchor_ms) / 1000
                    else:
                        t_sec = (total_frames * (meta.interval_ms or 20000) - timestamp_anchor_ms) / 1000

                    if is_z_stack:
                        ts_text = f"z={key:02d}"
                        fmt_label = "z-slice"
                    else:
                        sign = "-" if t_sec < 0 else ""
                        abs_t = abs(t_sec)
                        t_hr = int(abs_t // 3600)
                        t_min = int((abs_t % 3600) // 60)
                        t_s = int(abs_t % 60)
                        ts_text = f"{sign}{t_hr:02d}:{t_min:02d}:{t_s:02d}"
                        fmt_label = "HH:MM:SS"

                    # Use the file's own channel names in the overlay
                    phase_label = (
                        file_meta.ch_names[file_meta.phase_ch]
                        if file_meta.phase_ch is not None and file_meta.phase_ch < len(file_meta.ch_names)
                        else "PHASE"
                    )
                    fluor_label = (
                        file_meta.ch_names[file_meta.fluor_ch]
                        if file_meta.fluor_ch is not None and file_meta.fluor_ch < len(file_meta.ch_names)
                        else "FLUOR"
                    )
                    if phase_rgb is not None:
                        draw_timestamp(phase_rgb, ts_text)
                        draw_timestamp(phase_rgb, fmt_label, position=(10, 60))
                        draw_scale_bar(phase_rgb, meta.pixel_size_um)
                        draw_timestamp(phase_rgb, phase_label.upper(), position=(roi.w - 260, 30))
                    if fluor_rgb is not None:
                        draw_timestamp(fluor_rgb, ts_text)
                        draw_timestamp(fluor_rgb, fmt_label, position=(10, 60))
                        draw_scale_bar(fluor_rgb, meta.pixel_size_um)
                        draw_timestamp(fluor_rgb, fluor_label.upper(), position=(roi.w - 260, 30))

                    # Multi-channel: extract and write any EXTRA fluor channels for
                    # this frame (3+ channel batches — e.g. 561 mCherry alongside 488 GFP).
                    extra_frame_idx = {}  # ch_name -> tif idx for this frame
                    role_cap = {'pre': 'Pre', 'ablation': 'Ablation', 'monitoring': 'Monitoring', 'zstack': 'Zstack'}[role]
                    for ch_name in extra_fluor_names:
                        if ch_name not in file_meta.ch_names:
                            continue
                        file_ch_idx = file_meta.ch_names.index(ch_name)
                        ch_pages = [(pi, sub_idx) for pi, ci, sub_idx in pages if ci == file_ch_idx]
                        if not ch_pages:
                            continue
                        if is_z_stack:
                            ex_raw = t.pages[ch_pages[0][0]].asarray()
                        elif len(ch_pages) > 1:
                            ex_raw = np.max(np.stack([t.pages[pi].asarray() for pi, _ in ch_pages]), axis=0)
                        else:
                            ex_raw = t.pages[ch_pages[0][0]].asarray()
                        ex_crop = crop_frame(ex_raw, file_roi)
                        extra_tifs[ch_name].write(ex_crop)
                        extra_frame_idx[ch_name] = extra_tif_idx[ch_name]
                        extra_tif_idx[ch_name] += 1
                        lo, hi = extra_contrast.get(ch_name, (0, 65535))
                        ex_8 = normalize_uint8(ex_crop, lo, hi)
                        ex_rgb = colorize_green(ex_8)
                        # Overlays
                        draw_timestamp(ex_rgb, ts_text)
                        draw_timestamp(ex_rgb, fmt_label, position=(10, 60))
                        draw_scale_bar(ex_rgb, meta.pixel_size_um)
                        draw_timestamp(ex_rgb, ch_name.upper(), position=(roi.w - 260, 30))
                        if role == 'ablation' and frame_in_file in event_map:
                            for ev in event_map[frame_in_file]:
                                draw_ablation_marker(ex_rgb, ev.x_px, ev.y_px, roi, meta.pixel_size_um)
                        extra_writers[(ch_name, role_cap)].write(ex_rgb)

                    # Write primary phase/fluor pair to the existing _Phase_/_Fluor_ videos.
                    # If a channel image is missing for this frame but the batch HAS that
                    # channel overall, write a blank frame so each movie stays index-aligned
                    # with frames_meta. (Dropping the frame would shift every later frame and
                    # offset the HTML's per-frame t_sec lookup vs the burned timestamp.)
                    # No-op for batches where both channels are present every frame.
                    if role == 'pre':
                        if phase_rgb is not None: phase_pre_writer.write(phase_rgb)
                        elif has_phase: phase_pre_writer.write(np.zeros((roi.h, roi.w, 3), np.uint8))
                        if fluor_rgb is not None: fluor_pre_writer.write(fluor_rgb)
                        elif has_fluor: fluor_pre_writer.write(np.zeros((roi.h, roi.w, 3), np.uint8))
                        pre_frames += 1
                    elif role == 'ablation':
                        if frame_in_file in event_map:
                            marker_frames += 1
                            for ev in event_map[frame_in_file]:
                                if phase_rgb is not None:
                                    draw_ablation_marker(phase_rgb, ev.x_px, ev.y_px, roi, meta.pixel_size_um)
                                if fluor_rgb is not None:
                                    draw_ablation_marker(fluor_rgb, ev.x_px, ev.y_px, roi, meta.pixel_size_um)
                        if phase_rgb is not None: phase_abl_writer.write(phase_rgb)
                        elif has_phase: phase_abl_writer.write(np.zeros((roi.h, roi.w, 3), np.uint8))
                        if fluor_rgb is not None: fluor_abl_writer.write(fluor_rgb)
                        elif has_fluor: fluor_abl_writer.write(np.zeros((roi.h, roi.w, 3), np.uint8))
                        abl_frames += 1
                    elif role == 'zstack':
                        if phase_rgb is not None: phase_zstack_writer.write(phase_rgb)
                        elif has_phase: phase_zstack_writer.write(np.zeros((roi.h, roi.w, 3), np.uint8))
                        if fluor_rgb is not None: fluor_zstack_writer.write(fluor_rgb)
                        elif has_fluor: fluor_zstack_writer.write(np.zeros((roi.h, roi.w, 3), np.uint8))
                        zstack_frames += 1
                    else:
                        if phase_rgb is not None: phase_mon_writer.write(phase_rgb)
                        elif has_phase: phase_mon_writer.write(np.zeros((roi.h, roi.w, 3), np.uint8))
                        if fluor_rgb is not None: fluor_mon_writer.write(fluor_rgb)
                        elif has_fluor: fluor_mon_writer.write(np.zeros((roi.h, roi.w, 3), np.uint8))
                        mon_frames += 1

                    frames_meta.append({
                        'idx': total_frames,
                        'role': role,
                        't_sec': round(t_sec, 3),
                        'phase_tif_idx': frame_phase_idx,
                        'fluor_tif_idx': frame_fluor_idx,
                        'extra_tif_idx': extra_frame_idx,
                        'source': fname,
                        'frame_in_file': frame_in_file,
                    })
                    total_frames += 1
                    frame_in_file += 1

        except Exception as e:
            print(f"    ERROR processing {fname}: {e}")
            continue

        print(f"    {frame_in_file} frames processed")

    # Close extra-fluor writers first (they're per-channel)
    for (ch_name, _), w in extra_writers.items():
        w.release()
    for tif in extra_tifs.values():
        tif.close()

    # Close writers and transcode
    mp4_paths = []
    _close_list = [
        (phase_pre_writer, '_Phase_Pre.mp4'),
        (fluor_pre_writer, '_Fluor_Pre.mp4'),
        (phase_abl_writer, '_Phase_Ablation.mp4'),
        (fluor_abl_writer, '_Fluor_Ablation.mp4'),
        (phase_mon_writer, '_Phase_Monitoring.mp4'),
        (fluor_mon_writer, '_Fluor_Monitoring.mp4'),
    ]
    if _has_zstacks:
        _close_list += [(phase_zstack_writer, '_Phase_Zstack.mp4'),
                        (fluor_zstack_writer, '_Fluor_Zstack.mp4')]
    for writer, suffix in _close_list:
        writer.release()
        mp4_paths.append(os.path.join(output_dir, f'{batch.name}{suffix}'))
    phase_tif.close()
    fluor_tif.close()

    # Sidecar metadata for fast video-only re-renders (consumed by rerender_from_cropped.py)
    frames_json = {
        'batch_name': batch.name,
        'fps': fps,
        'pixel_size_um': meta.pixel_size_um,
        'roi': {'x': roi.x, 'y': roi.y, 'w': roi.w, 'h': roi.h},
        'ch_names': list(meta.ch_names),
        'phase_ch': meta.phase_ch,
        'fluor_ch': meta.fluor_ch,
        'has_phase': has_phase,
        'has_fluor': has_fluor,
        'fluor_contrast': [fluor_low, fluor_high],
        'phase_contrast': [phase_low, phase_high],
        'timestamp_anchor_ms': timestamp_anchor_ms,
        'ablation_events_local': [
            {'epoch_ms': ev.epoch_ms, 'x_px': ev.x_px, 'y_px': ev.y_px}
            for ev in ablation_events
        ],
        'frames': frames_meta,
        'source_files': source_file_summaries,
        'extra_fluor_channels': [
            {'name': c, 'sanitized': sanitize_channel_name(c),
             'contrast': list(extra_contrast.get(c, [0, 65535]))}
            for c in extra_fluor_names
        ],
    }
    with open(os.path.join(output_dir, f'{batch.name}_frames.json'), 'w') as f:
        json.dump(frames_json, f)

    # FFmpegVideoWriter already emits H.264; no transcode step needed.

    # Compute pre/post ablation fluor stats
    pre_fluor = ''
    post_fluor = ''
    baseline_fluor = ''
    if ablation_events and all_frame_times_ms and all_fluor_means:
        first_event_ms = ablation_events[0].epoch_ms
        n_fluor = len(all_fluor_means)
        pre_indices = [i for i, t in enumerate(all_frame_times_ms) if t < first_event_ms and i < n_fluor]
        post_indices = [i for i, t in enumerate(all_frame_times_ms) if t >= first_event_ms and i < n_fluor]
        if pre_indices:
            pre_fluor = float(np.mean([all_fluor_means[i] for i in pre_indices]))
            baseline_fluor = pre_fluor
        if post_indices:
            post_subset = post_indices[:min(10, len(post_indices))]
            post_fluor = float(np.mean([all_fluor_means[i] for i in post_subset]))

    print(f"  Done: {total_frames} total frames ({pre_frames} pre, {abl_frames} ablation, {mon_frames} monitoring"
          + (f", {zstack_frames} z-stack" if zstack_frames else "") + f") -> {output_dir}")
    return {
        'status': 'OK',
        'total_frames': total_frames,
        'total_files': len(all_files),
        'ablation_events_list': ablation_events,
        'frame_times_ms': all_frame_times_ms,
        'marker_frames': marker_frames,
        'pre_ablation_fluor': pre_fluor,
        'post_ablation_fluor': post_fluor,
        'baseline_fluor': baseline_fluor,
        'roi': roi,
        'source_files': source_filenames,
        'output_dir': output_dir,
    }
