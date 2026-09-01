"""Output management: skip-if-done, directory setup, cache cleanup."""
import os
import shutil


def is_batch_done(batch_name, output_root, date_str):
    """Check if a batch has already been processed.

    Considered done when at least one of the six expected video files exists
    with real content (> 1 KB — stub mp4s from a failed run are 257 bytes).
    This covers single-channel batches (only Phase_* or only Fluor_* will have
    real content) and non-ablation batches (only Monitoring videos will).
    """
    output_dir = os.path.join(output_root, date_str, batch_name)
    if not os.path.isdir(output_dir):
        return False
    suffixes = (
        '_Phase_Ablation.mp4', '_Fluor_Ablation.mp4',
        '_Phase_Monitoring.mp4', '_Fluor_Monitoring.mp4',
        '_Phase_Pre.mp4', '_Fluor_Pre.mp4',
    )
    for s in suffixes:
        p = os.path.join(output_dir, f'{batch_name}{s}')
        if os.path.isfile(p) and os.path.getsize(p) > 1024:
            return True
    return False


def batch_output_dir(batch_name, output_root, date_str):
    """Create and return the output directory for a batch."""
    output_dir = os.path.join(output_root, date_str, batch_name)
    os.makedirs(output_dir, exist_ok=True)
    return output_dir


def cleanup_cache(tif_paths, cache_root):
    """Delete cached TIF files that are inside cache_root.

    Never deletes files outside of cache_root (local drive originals).
    """
    if not cache_root:
        return
    cache_norm = os.path.normpath(cache_root).lower()
    for path in tif_paths:
        path_norm = os.path.normpath(path).lower()
        if path_norm.startswith(cache_norm) and os.path.isfile(path):
            try:
                os.remove(path)
            except OSError:
                pass
