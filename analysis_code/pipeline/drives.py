"""Drive detection and classification for Windows.

Identifies all mounted drives and classifies each as:
  internal  - fixed local disk (SSD/HDD inside the computer)
  removable - USB hard drive, flash drive
  server    - network-mapped drive (SMB/CIFS)
  cdrom     - optical drive

No hardcoded drive letters. Works on any Windows machine.
"""
import os
import sys


def classify_drives():
    """Return dict mapping drive root (e.g. 'C:') to info dict.

    Info dict keys: type, total_gb, free_gb, unc
    """
    if sys.platform != 'win32':
        return {'/': {'type': 'internal', 'total_gb': 0, 'free_gb': 0, 'unc': None}}

    import ctypes
    import ctypes.wintypes

    mpr = None
    try:
        mpr = ctypes.WinDLL('mpr', use_last_error=True)
    except Exception:
        pass

    result = {}
    for letter in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
        root = f'{letter}:\\'
        dtype = ctypes.windll.kernel32.GetDriveTypeW(root)
        if dtype <= 1:
            continue

        drive = f'{letter}:'

        # Check if this maps to a UNC network path
        unc = None
        if mpr is not None:
            try:
                buf = ctypes.create_unicode_buffer(512)
                length = ctypes.wintypes.DWORD(512)
                rc = mpr.WNetGetConnectionW(drive, buf, ctypes.byref(length))
                if rc == 0 and buf.value.startswith('\\\\'):
                    unc = buf.value
            except Exception:
                pass

        # Classify
        if dtype == 5:
            drive_type = 'cdrom'
        elif dtype == 4 or unc is not None:
            drive_type = 'server'
        elif dtype == 2:
            drive_type = 'removable'
        elif dtype == 3:
            drive_type = 'internal'
        else:
            drive_type = 'unknown'

        # Disk space
        total_gb = 0
        free_gb = 0
        try:
            free_bytes = ctypes.c_ulonglong(0)
            total_bytes = ctypes.c_ulonglong(0)
            ctypes.windll.kernel32.GetDiskFreeSpaceExW(
                root, None, ctypes.byref(total_bytes), ctypes.byref(free_bytes))
            total_gb = round(total_bytes.value / (1024 ** 3))
            free_gb = round(free_bytes.value / (1024 ** 3))
        except Exception:
            pass

        result[drive] = {
            'type': drive_type,
            'total_gb': total_gb,
            'free_gb': free_gb,
            'unc': unc,
        }
    return result


def local_drives():
    """Return list of local drive roots (internal + removable)."""
    return [d for d, info in classify_drives().items()
            if info['type'] in ('internal', 'removable')]


def find_server_root():
    """Find the lab server root path, or None if not mounted.

    Searches all server-type drives for the known directory structure.
    """
    suffix = os.path.join('LabShare', 'Microscope Users', 'Maddie Blaauw 2023-on')
    for drive, info in classify_drives().items():
        if info['type'] == 'server':
            candidate = os.path.join(drive + '\\', suffix)
            if os.path.isdir(candidate):
                return candidate
    return None


def pick_output_drive(min_free_gb=50):
    """Pick the best drive for pipeline output.

    Prefers removable, falls back to internal with most free space.
    Returns drive root like 'G:' or None.
    """
    drives = classify_drives()
    candidates = []
    for drive, info in drives.items():
        if info['type'] not in ('internal', 'removable'):
            continue
        if info['free_gb'] < min_free_gb:
            continue
        # Prefer removable (priority 0), then internal (priority 1)
        priority = 0 if info['type'] == 'removable' else 1
        candidates.append((priority, -info['free_gb'], drive))
    candidates.sort()
    return candidates[0][2] if candidates else None


def pick_cache_drive(min_free_gb=50):
    """Pick the best internal drive for download cache (fastest I/O).

    Returns drive root like 'F:' or None.
    """
    drives = classify_drives()
    candidates = []
    for drive, info in drives.items():
        if info['type'] != 'internal':
            continue
        if info['free_gb'] < min_free_gb:
            continue
        candidates.append((-info['free_gb'], drive))
    candidates.sort()
    return candidates[0][1] if candidates else None
