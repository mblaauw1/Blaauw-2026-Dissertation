"""Read metadata from MicroManager OME-TIFF files.

Single source of truth. No CSV, no filename parsing, no sidecar files.
Everything comes from the TIF's embedded MicroManager metadata.
"""
import json
from dataclasses import dataclass, field


@dataclass
class TifMeta:
    ch_names: list = field(default_factory=list)
    n_channels: int = 1
    n_frames: int = 1
    n_slices: int = 1
    width: int = 0
    height: int = 0
    pixel_size_um: float | None = None
    interval_ms: float | None = None
    x_um: float | None = None
    y_um: float | None = None
    fluor_ch: int | None = None
    phase_ch: int | None = None


# Keywords for channel role detection
_PHASE = ('brightfield', 'phase', 'dic', 'trans', 'bf')
_FLUOR = ('488', '561', '640', 'gfp', 'rfp', 'cfp', 'yfp',
          'mcherry', 'cherry', 'alexa', 'cy', 'fitc', 'dapi',
          'eyfp', 'egfp', 'tdtomato', 'halotag', 'halo')


def detect_channels(ch_names):
    """Return (fluor_ch_index, phase_ch_index) from channel name list."""
    fluor = None
    phase = None
    for i, name in enumerate(ch_names):
        low = name.lower()
        if any(kw in low for kw in _PHASE):
            phase = i
        elif any(kw in low for kw in _FLUOR):
            if fluor is None:
                fluor = i
    return fluor, phase


def read_tif_meta(tif_path):
    """Read all metadata from a MicroManager OME-TIFF.

    Returns TifMeta. Raises ValueError if critical metadata is missing.
    """
    import tifffile

    meta = TifMeta()

    with tifffile.TiffFile(tif_path) as t:
        # MicroManager Summary (from the MM metadata block)
        mm = getattr(t, 'micromanager_metadata', None) or {}
        summary = mm.get('Summary', {}) if isinstance(mm, dict) else {}

        # Channel info
        meta.ch_names = summary.get('ChNames', [])
        meta.n_channels = int(summary.get('Channels', 1))
        meta.n_frames = int(summary.get('Frames', 1))
        meta.n_slices = int(summary.get('Slices', 1))
        meta.width = int(summary.get('Width', 0))
        meta.height = int(summary.get('Height', 0))

        # Pixel size
        ps = summary.get('PixelSizeUm') or summary.get('PixelSize_um')
        if ps and float(ps) > 0:
            meta.pixel_size_um = float(ps)

        # Time interval
        iv = summary.get('Interval_ms')
        if iv and float(iv) > 0:
            meta.interval_ms = float(iv)

        # Stage position from first page's per-frame metadata
        _ttl = None          # TriggerScope excitation-trigger state (for channel fallback)
        _condenser = None
        if t.pages:
            tag = t.pages[0].tags.get('MicroManagerMetadata')
            if tag:
                v = tag.value
                pm = json.loads(v) if isinstance(v, (bytes, str)) else v
                if isinstance(pm, dict):
                    _ttl = pm.get('TS_TTL1-8-State')
                    _condenser = pm.get('TICondenserCassette-State')
                    x = pm.get('XPositionUm')
                    y = pm.get('YPositionUm')
                    if x is not None:
                        meta.x_um = float(x)
                    if y is not None:
                        meta.y_um = float(y)
                    # Backup pixel size from per-frame metadata
                    if meta.pixel_size_um is None:
                        ps2 = pm.get('PixelSizeUm')
                        if ps2 and float(ps2) > 0:
                            meta.pixel_size_um = float(ps2)

        # Dimensions from actual page count if Summary was incomplete
        if meta.width == 0 and t.pages:
            meta.width = t.pages[0].shape[-1] if len(t.pages[0].shape) >= 2 else 0
            meta.height = t.pages[0].shape[-2] if len(t.pages[0].shape) >= 2 else 0
        n_pages = len(t.pages)
        expected = meta.n_channels * meta.n_frames * meta.n_slices
        if expected == 0 or abs(n_pages - expected) > expected * 0.1:
            # Summary counts don't match actual pages — recalculate
            if meta.n_channels > 0 and meta.n_slices > 0:
                meta.n_frames = n_pages // (meta.n_channels * meta.n_slices)

    # Detect channel roles
    meta.fluor_ch, meta.phase_ch = detect_channels(meta.ch_names)

    # Metadata-grounded fallback when the channel NAME is unrecognized (e.g. ChNames=['Default']).
    # Do NOT assume — read the real channel from the per-frame excitation-trigger device state:
    #   TS_TTL1-8-State != 0  -> excitation light source firing -> fluorescence
    #   TS_TTL1-8-State == 0  -> transmitted light only        -> brightfield/phase
    # (cube/filter-block are shared by GFP & Brightfield on this scope, so they can't distinguish;
    #  the TTL excitation trigger is decisive. Validated against named 2-channel acquisitions.)
    if meta.fluor_ch is None and meta.phase_ch is None and meta.n_channels == 1 and _ttl is not None:
        try:
            if int(_ttl) != 0:
                meta.fluor_ch = 0
                if not meta.ch_names: meta.ch_names = ['Fluor (from TS_TTL)']
            else:
                meta.phase_ch = 0
                if not meta.ch_names: meta.ch_names = ['Brightfield (from TS_TTL)']
        except (TypeError, ValueError):
            pass

    return meta
