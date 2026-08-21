"""Data discovery: find TIF files, cluster by stage position, build batches.

Always checks local drives first, then server. No exceptions.
"""
import os
import re
from dataclasses import dataclass, field
from collections import defaultdict, Counter

from metadata import read_tif_meta, TifMeta
from drives import local_drives, find_server_root


@dataclass
class Acquisition:
    folder_path: str
    tif_files: list = field(default_factory=list)  # sorted filenames
    has_ablation_log: bool = False
    meta: TifMeta | None = None  # from first TIF


@dataclass
class Batch:
    name: str
    date_str: str
    ablation: Acquisition | None = None  # FIRST ablation (== ablations[0]); kept for compat
    ablations: list = field(default_factory=list)  # ALL ablations of this cell, in order
    pre_monitoring: list = field(default_factory=list)  # ordered Acquisitions before first ablation
    monitoring: list = field(default_factory=list)  # ordered Acquisitions after first ablation
    zstacks: list = field(default_factory=list)  # single-timepoint z-stacks (NOT monitoring time-lapses)
    meta: TifMeta | None = None  # from ablation or first acquisition


def _is_zstack(a):
    """A single-timepoint z-stack (1 time point, many z-slices) is NOT a monitoring time-lapse.
    Routing it to 'monitoring' makes the pipeline flatten its z-slices into fake monitoring frames
    (bug 2026-07-15, e.g. 20251021 coverslip3_14). Detect it so it gets its own 'zstack' role."""
    m = a.meta
    return bool(m and (m.n_frames or 1) <= 1 and (m.n_slices or 1) > 1)


# Folders to skip during recursive search
_SKIP_DIRS = {
    '$Recycle.Bin', 'System Volume Information', 'Windows',
    'Program Files', 'Program Files (x86)', 'ProgramData',
    'Recovery', 'PerfLogs', 'Python314', 'Python', 'msys64',
    'pipeline_output', 'Pipeline Output', 'Pipeline_output',
    'Pipeline_Output', 'downloaded_movies', 'raw_tifs', 'temp',
}
_SKIP_PREFIXES = ('.', 'pipeline', 'output_', 'image analysis', 'image_analysis', 'image processing', 'image_processing',
                  'imaging')  # 'imaging analysis' / 'Imaging data ...' subfolders hold processed COPIES (own PAS logs) that else cluster as false duplicate ablations
_DATE_RE = re.compile(r'^20\d{6}')


def _has_tifs(folder):
    """Quick check if folder or its immediate children have .ome.tif files."""
    try:
        for item in os.listdir(folder):
            if item.endswith('.ome.tif'):
                return True
            sub = os.path.join(folder, item)
            if os.path.isdir(sub):
                try:
                    for f in os.listdir(sub):
                        if f.endswith('.ome.tif'):
                            return True
                except (OSError, PermissionError):
                    pass
    except (OSError, PermissionError):
        pass
    return False


def find_date_folder(date_str):
    """Find a date folder, checking local drives first, then server.

    Searches up to 3 levels deep on each local drive for a folder
    matching date_str. Falls back to server if not found locally.
    Returns the full path or None.
    """
    # Local drives first
    for drive in local_drives():
        try:
            for d1 in os.listdir(drive + '/'):
                if d1 in _SKIP_DIRS or d1.startswith('.') or d1.startswith('$'):
                    continue
                p1 = os.path.join(drive + '/', d1)
                if not os.path.isdir(p1):
                    continue
                if d1 == date_str or d1.startswith(date_str):
                    if _has_tifs(p1):
                        print(f"  Found {date_str} locally: {p1}")
                        return p1
                # Level 2
                try:
                    for d2 in os.listdir(p1):
                        if d2 in _SKIP_DIRS or d2.startswith('.'):
                            continue
                        p2 = os.path.join(p1, d2)
                        if not os.path.isdir(p2):
                            continue
                        if d2 == date_str or d2.startswith(date_str):
                            if _has_tifs(p2):
                                print(f"  Found {date_str} locally: {p2}")
                                return p2
                        # Level 3
                        try:
                            for d3 in os.listdir(p2):
                                if d3 in _SKIP_DIRS or d3.startswith('.'):
                                    continue
                                p3 = os.path.join(p2, d3)
                                if not os.path.isdir(p3):
                                    continue
                                if d3 == date_str or d3.startswith(date_str):
                                    if _has_tifs(p3):
                                        print(f"  Found {date_str} locally: {p3}")
                                        return p3
                        except (OSError, PermissionError):
                            pass
                except (OSError, PermissionError):
                    pass
        except (OSError, PermissionError):
            pass

    # Server fallback
    server = find_server_root()
    if server:
        # Direct child
        candidate = os.path.join(server, date_str)
        if os.path.isdir(candidate):
            print(f"  Found {date_str} on server: {candidate}")
            return candidate
        # Nested (e.g. 20260331/20260420)
        try:
            for parent in os.listdir(server):
                parent_path = os.path.join(server, parent)
                if os.path.isdir(parent_path):
                    nested = os.path.join(parent_path, date_str)
                    if os.path.isdir(nested):
                        print(f"  Found {date_str} on server (nested): {nested}")
                        return nested
        except (OSError, PermissionError):
            pass

    print(f"  WARNING: {date_str} not found on any local drive or server")
    return None


def _folder_number(name):
    """Extract trailing number from folder name for ordering.
    e.g. 'ablation_11' -> 11, 'ablation_2' -> 2
    """
    m = re.search(r'(\d+)\s*$', name)
    return int(m.group(1)) if m else 0


def _is_continuation(filename):
    """True if filename is a 4GB continuation split (e.g. _Pos0_1.ome.tif)."""
    return bool(re.search(r'_Pos\d+_\d+\.ome\.tif$', filename))


def _base_position(filename):
    """Extract base position identifier, stripping continuation suffix.
    'experiment_MMStack_Pos0.ome.tif'   -> 'Pos0'
    'experiment_MMStack_Pos0_1.ome.tif' -> 'Pos0'
    """
    m = re.search(r'(Pos\d+)(?:_\d+)?\.ome\.tif$', filename)
    return m.group(1) if m else filename


def scan_acquisitions(date_path):
    """Walk a date folder and find all acquisition folders with TIF files.

    Returns list of Acquisition objects, sorted by folder number.
    """
    acquisitions = []

    for dirpath, dirnames, filenames in os.walk(date_path):
        # Prune unwanted directories
        dirnames[:] = [
            d for d in sorted(dirnames)
            if d not in _SKIP_DIRS
            and not any(d.lower().startswith(pfx) for pfx in _SKIP_PREFIXES)
        ]

        tifs = sorted(f for f in filenames
                      if f.endswith('.ome.tif') and not f.startswith('.'))
        if not tifs:
            continue

        has_log = os.path.isfile(os.path.join(dirpath, 'PointAndShoot.log'))

        # Group TIF files by base position (e.g. Pos0, Pos10)
        positions = defaultdict(list)
        for tif in tifs:
            positions[_base_position(tif)].append(tif)

        # For single-position or ablation folders: one Acquisition
        # For multi-position non-ablation: split into per-position Acquisitions
        if has_log or len(positions) <= 1:
            meta = None
            for tif in tifs:
                if not _is_continuation(tif):
                    try:
                        meta = read_tif_meta(os.path.join(dirpath, tif))
                    except Exception as e:
                        print(f"  WARNING: Could not read metadata from {tif}: {e}")
                    break
            if meta is None and tifs:
                try:
                    meta = read_tif_meta(os.path.join(dirpath, tifs[0]))
                except Exception:
                    pass
            acquisitions.append(Acquisition(
                folder_path=dirpath,
                tif_files=tifs,
                has_ablation_log=has_log,
                meta=meta,
            ))
        else:
            # Multi-position monitoring: split per position
            for pos_name, pos_tifs in sorted(positions.items()):
                meta = None
                for tif in pos_tifs:
                    if not _is_continuation(tif):
                        try:
                            meta = read_tif_meta(os.path.join(dirpath, tif))
                        except Exception:
                            pass
                        break
                if meta is None and pos_tifs:
                    try:
                        meta = read_tif_meta(os.path.join(dirpath, pos_tifs[0]))
                    except Exception:
                        pass
                acquisitions.append(Acquisition(
                    folder_path=dirpath,
                    tif_files=pos_tifs,
                    has_ablation_log=False,
                    meta=meta,
                ))

    # Sort by folder number
    acquisitions.sort(key=lambda a: _folder_number(os.path.basename(a.folder_path)))
    return acquisitions


def cluster_by_position(acquisitions, crop_px=(1248, 1056)):
    """Group acquisitions by stage XY position.

    Two acquisitions are at the "same position" if their stage XY
    is within the mid-crop physical extent of each other.
    Uses greedy union-find clustering.

    Returns list of lists of Acquisitions (each list = one cell).
    """
    clusters = []  # list of {'members': [acq], 'x': float, 'y': float, 'tol_x': float, 'tol_y': float}

    for acq in acquisitions:
        if acq.meta is None or acq.meta.x_um is None or acq.meta.y_um is None:
            # Can't cluster without position — put in its own cluster
            clusters.append({
                'members': [acq],
                'x': 0, 'y': 0,
                'tol_x': 0, 'tol_y': 0,
            })
            continue

        px = acq.meta.pixel_size_um or 0.062
        # Half-crop tolerance: positions ≥ ~38 µm X / ~33 µm Y apart are different cells
        tol_x = crop_px[0] * px / 2
        tol_y = crop_px[1] * px / 2

        placed = False
        for cl in clusters:
            effective_tol_x = max(cl['tol_x'], tol_x)
            effective_tol_y = max(cl['tol_y'], tol_y)
            if (abs(acq.meta.x_um - cl['x']) <= effective_tol_x
                    and abs(acq.meta.y_um - cl['y']) <= effective_tol_y):
                cl['members'].append(acq)
                # Update reference to median
                xs = [a.meta.x_um for a in cl['members'] if a.meta and a.meta.x_um is not None]
                ys = [a.meta.y_um for a in cl['members'] if a.meta and a.meta.y_um is not None]
                cl['x'] = sorted(xs)[len(xs) // 2]
                cl['y'] = sorted(ys)[len(ys) // 2]
                cl['tol_x'] = max(cl['tol_x'], tol_x)
                cl['tol_y'] = max(cl['tol_y'], tol_y)
                placed = True
                break

        if not placed:
            clusters.append({
                'members': [acq],
                'x': acq.meta.x_um,
                'y': acq.meta.y_um,
                'tol_x': tol_x,
                'tol_y': tol_y,
            })

    return [cl['members'] for cl in clusters]


def repair_degenerate_positions(acquisitions):
    """Some multi-position monitoring sweeps have corrupt per-position stage
    metadata: several positions report an IDENTICAL stage XY (e.g. 20260420
    sweeps 60/61 where Pos0/Pos2/Pos11 all read the same coordinates). Left
    uncorrected, XY clustering merges those distinct cells into one batch.

    Repair each corrupt sweep's colliding positions by copying the XY from a
    CLEAN reference sweep that shares the same position-index list (verified by
    agreement on the sweep's NON-colliding positions). The position INDEX (PosN)
    is reliable even when the recorded XY is not, so this restores the true
    per-position coordinates. Repairs in place; returns the count of fixes.
    """
    def pos(a):
        return _base_position(a.tif_files[0]) if a.tif_files else None

    def xy(a):
        return (round(a.meta.x_um, 1), round(a.meta.y_um, 1))

    # group per-position monitoring acquisitions by sweep folder
    by_sweep = defaultdict(dict)  # folder -> {pos_name: acq}
    for a in acquisitions:
        if a.has_ablation_log or not a.meta or a.meta.x_um is None:
            continue
        p = pos(a)
        if p:
            by_sweep[a.folder_path][p] = a

    def is_clean(pm):
        xys = [xy(a) for a in pm.values()]
        return len(set(xys)) == len(xys)

    clean = {f: pm for f, pm in by_sweep.items() if len(pm) > 1 and is_clean(pm)}

    fixes = 0
    for folder, pm in by_sweep.items():
        if len(pm) <= 1 or is_clean(pm):
            continue
        cnt = Counter(xy(a) for a in pm.values())
        # pick a clean donor sweep that agrees on this sweep's NON-colliding
        # positions (same index -> same XY) — proves they share a position list.
        donor = None
        for dpm in clean.values():
            shared = set(pm) & set(dpm)
            agree = sum(1 for p in shared if cnt[xy(pm[p])] == 1 and xy(pm[p]) == xy(dpm[p]))
            if agree >= 1:
                donor = dpm
                break
        if donor is None:
            print(f"    WARNING: corrupt sweep {os.path.basename(folder)} has no clean "
                  f"reference to repair from — leaving as-is")
            continue
        # overwrite ONLY the colliding positions, using the donor's per-index XY
        sweep_fixes = 0
        for p, a in pm.items():
            if cnt[xy(a)] > 1 and p in donor:
                a.meta.x_um = donor[p].meta.x_um
                a.meta.y_um = donor[p].meta.y_um
                fixes += 1
                sweep_fixes += 1
        print(f"    Repaired {os.path.basename(folder)}: fixed degenerate XY for "
              f"{sweep_fixes} position(s)")
    if fixes:
        print(f"  Repaired {fixes} corrupt-metadata position(s) via position-index matching")
    return fixes


# =============================================================================
# ALTERNATE PAIRING TOOL — CONSTELLATION REGISTRATION  (NOT used by build_batches)
# -----------------------------------------------------------------------------
# REACH FOR THIS when, AFTER looking at the movies, someone reports:
#   * "the batches weren't made correctly"
#   * "the monitoring shows a DIFFERENT cell than the one that was ablated"
#   * "the cell in the later part of the movie isn't the ablated cell"
#   * a big time-gap movie where the pre-gap and post-gap cells look different
#   ...on a date whose imaging positions were HAND-EDITED / the stage was
#   RE-REGISTERED between acquisition sweeps (classic pattern: a short "check"
#   sweep, then a long monitoring sweep, with positions re-clicked in between).
#
# WHY THE MAIN FLOW (cluster_by_position) FAILS HERE:
#   It pairs monitoring->ablation by ABSOLUTE stage XY (within ~1 FOV). If the
#   coordinate SYSTEM drifts between sweeps (seen: ~206,261 um on 20260422 Zm)
#   or the per-position metadata is degenerate (several positions reporting the
#   SAME XY -> see repair_degenerate_positions), absolute-XY clustering either
#   drops the monitoring (cell comes out with only the short pre-gap segment) or
#   attaches the WRONG position (a neighbor). Canonical case: 20260422
#   Zm_ablation_2um  (_14 short sweep + _15 long sweep, list edited between them).
#
# THE FIX (this tool): the RELATIVE geometry of the cells survives a coordinate
#   drift, so register the constellations. RANSAC-fit a translation from the
#   ablation-cell point set onto the sweep's position point set, then match
#   nearest-after-transform. The per-cell RESIDUAL grades trust:
#       <~15 um  same cell, centered            -> safe to stitch
#       ~15-40   same cell but off-center        -> VERIFY visually (crop may clip)
#       >~40     sweep position is on a NEIGHBOR  -> do NOT stitch
#   Residual magnitude ALONE is not enough (local cell density matters: on
#   20260422, _13 was clean at 41 um but _10 ambiguous at 24 um) — ALWAYS pull a
#   frame from the sweep segment and eyeball it against the ablation cell before
#   committing. Then re-render with monitoring=[short_sweep_pos, long_sweep_pos].
#
# COORDINATES: read from the MicroManager per-position '*_metadata.txt' sidecars
#   (XPositionUm/YPositionUm; the Summary 'StagePositions' also carries the
#   TIZDrive Z-focus, a per-cell signature). The .ome.tif TAGS are frequently
#   CORRUPT on these dates, but the sidecar .txt is clean — always prefer it.
#
# Deliberately NOT wired into build_batches: it requires per-cell visual
# confirmation, so it's a tool to run on purpose for a flagged date, not a
# silent default. Example:
#     m = register_sweep_to_ablations(date_path, [1,2,3,4,6,8,9,10,11,12,13],
#                                     "Zm_ablation_2um_14", "Zm_ablation_2um_15")
#     # m = {cell_num: (sweep_pos, residual_um)}  -> stitch the small-residual ones
# =============================================================================

def _read_stage_xy_sidecar(metadata_txt_path):
    """Stage XY (um) from a MicroManager per-position *_metadata.txt sidecar.

    Prefers a per-frame value over the first (Summary) occurrence, since the
    first can be a placeholder. Returns (x, y) or None. Clean even when the
    .ome.tif tags are corrupt.
    """
    try:
        with open(metadata_txt_path, errors="replace") as f:
            txt = f.read(300000)
    except OSError:
        return None
    xs = re.findall(r'"XPositionUm"\s*:\s*([-\d.]+)', txt)
    ys = re.findall(r'"YPositionUm"\s*:\s*([-\d.]+)', txt)
    if not xs or not ys:
        return None
    i = 1 if len(xs) >= 2 else 0
    return (float(xs[i]), float(ys[i]))


def register_sweep_to_ablations(date_path, ablation_nums, short_sweep_folder,
                                long_sweep_folder=None, tol_um=60,
                                exp_prefix="Zm_ablation_2um"):
    """Pair a monitoring sweep to ablation cells by CONSTELLATION REGISTRATION.

    See the big comment block above for when/why. Reads stage XY from the
    per-position metadata.txt sidecars, RANSAC-fits a translation from the
    ablation-cell constellation onto the sweep positions, and returns
    {ablation_num: (sweep_pos_index, residual_um)} for cells that matched within
    tol_um. Cells absent from the result have no reliable position in that sweep.

    Verify borderline (residual > ~15um) pairings visually before stitching.
    """
    import itertools
    import glob

    def sweep_positions(folder):
        out = {}
        pat = os.path.join(date_path, folder, "*_Pos*_metadata.txt")
        for md in glob.glob(pat):
            b = os.path.basename(md)
            if b.startswith("._") or re.search(r'_Pos\d+_\d+_meta', b):
                continue
            m = re.search(r'_Pos(\d+)_metadata', b)
            if m:
                out[int(m.group(1))] = _read_stage_xy_sidecar(md)
        return out

    abl = {}
    for n in ablation_nums:
        hits = glob.glob(os.path.join(date_path, f"{exp_prefix}_{n}", "*_Pos0_metadata.txt"))
        if hits:
            abl[n] = _read_stage_xy_sidecar(hits[0])
    sweep = sweep_positions(short_sweep_folder)
    if long_sweep_folder:  # register against the LONG sweep (that's the monitoring we want)
        sweep = sweep_positions(long_sweep_folder)

    def d(a, b):
        return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5 if a and b else 9e9

    # RANSAC: seed a translation from every (ablation, sweep-pos) pair, keep the
    # translation that maps the most ablation cells onto distinct sweep positions.
    best = (None, {})
    for an, sp in itertools.product(abl, sweep):
        if not abl[an] or not sweep[sp]:
            continue
        T = (sweep[sp][0] - abl[an][0], sweep[sp][1] - abl[an][1])
        match, used = {}, set()
        for a in abl:
            if not abl[a]:
                continue
            p = (abl[a][0] + T[0], abl[a][1] + T[1])
            cand = sorted(((d(p, sweep[s]), s) for s in sweep if sweep[s] and s not in used),
                          key=lambda x: x[0])
            if cand and cand[0][0] < tol_um:
                match[a] = cand[0][1]
                used.add(cand[0][1])
        if len(match) > len(best[1]):
            best = (T, match)
    T, match = best
    if T is None:
        return {}
    out = {}
    for a, sp in match.items():
        res = d((abl[a][0] + T[0], abl[a][1] + T[1]), sweep[sp])
        out[a] = (sp, round(res, 1))
    return out


def build_batches(date_str, date_path):
    """Full discovery: scan, cluster, pair ablation+monitoring.

    Returns list of Batch objects ready for processing.
    """
    print(f"  Scanning acquisitions in {date_path}...")
    acquisitions = scan_acquisitions(date_path)
    if not acquisitions:
        print(f"  No acquisitions found in {date_str}")
        return []

    # Repair corrupt per-position stage metadata before clustering (some sweeps
    # report identical XY for distinct positions — would over-merge cells).
    repair_degenerate_positions(acquisitions)

    print(f"  Found {len(acquisitions)} acquisition folders, clustering by position...")
    clusters = cluster_by_position(acquisitions)
    print(f"  {len(clusters)} cell positions found")

    batches = []
    for cell_acqs in clusters:
        # Find ALL ablation acquisitions at this position, sorted by folder number
        ablations = sorted(
            [a for a in cell_acqs if a.has_ablation_log],
            key=lambda a: _folder_number(os.path.basename(a.folder_path)))
        non_ablations = sorted(
            [a for a in cell_acqs if not a.has_ablation_log],
            key=lambda a: _folder_number(os.path.basename(a.folder_path)))

        if not ablations:
            # No ablation — single batch with all acquisitions as monitoring
            first = cell_acqs[0]
            folder_name = os.path.basename(first.folder_path)
            batches.append(Batch(
                name=f"{date_str} {folder_name}",
                date_str=date_str,
                monitoring=[a for a in non_ablations if not _is_zstack(a)],
                zstacks=[a for a in non_ablations if _is_zstack(a)],
                meta=first.meta,
            ))
            continue

        # ONE batch per CELL. A cell ablated more than once stays a SINGLE batch:
        # all its ablations + all its monitoring render on one continuous timeline
        # anchored at the first ablation. Clean partition is preserved — every
        # acquisition in this cell's cluster belongs to exactly this one batch:
        #   - acqs before the FIRST ablation -> pre-monitoring
        #   - acqs after the FIRST ablation  -> monitoring
        first_abl_num = _folder_number(os.path.basename(ablations[0].folder_path))
        pre_monitoring = []
        monitoring = []
        zstacks = []
        for a in non_ablations:
            if _is_zstack(a):
                # single-timepoint z-stack snapshot -> its own role, never a monitoring time-lapse
                zstacks.append(a)
                continue
            a_num = _folder_number(os.path.basename(a.folder_path))
            if a_num < first_abl_num:
                pre_monitoring.append(a)
            else:
                monitoring.append(a)

        folder_name = os.path.basename(ablations[0].folder_path)
        batches.append(Batch(
            name=f"{date_str} {folder_name}",
            date_str=date_str,
            ablation=ablations[0],
            ablations=ablations,
            pre_monitoring=pre_monitoring,
            monitoring=monitoring,
            zstacks=zstacks,
            meta=ablations[0].meta,
        ))

    # Handle duplicate names
    name_counts = defaultdict(int)
    for b in batches:
        name_counts[b.name] += 1
    seen = defaultdict(int)
    for b in batches:
        if name_counts[b.name] > 1:
            seen[b.name] += 1
            b.name = f"{b.name}_xy{seen[b.name]}"

    print(f"  Built {len(batches)} batches")
    return batches
