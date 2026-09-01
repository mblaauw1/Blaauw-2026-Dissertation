# Kinetochore tracking (Cdc20-eYFP, PtK2)

Tracks kinetochore puncta over each batch's **monitoring movie**, from the start
of monitoring to **anaphase onset + 3 min**, using TrackMate (LoG detector +
Sparse-LAP tracker) in headless Fiji.

The monitoring movie of a batch is several raw acquisitions stitched in time
order. We track on the pipeline's **cell-cropped, max-Z-projected, 16-bit GFP**
frames (`*_Fluor_Cropped.tif`), the kinetochore channel. Brightfield is unused.

## Components (code here; all OUTPUT on the 5 MB drive)

| file | role |
|------|------|
| `kt_track_prep.py`  | stitch each batch's monitoring window → `stacks/<base>_KTmon.tif` + `<base>_timing.csv` |
| `kt_trackmate.groovy` | headless TrackMate: detect KT-sized spots, track, persistence-filter → XML + `spots.csv` + `tracks.csv` |
| `kt_finalize.py`    | merge REAL acquisition time, compute seam-aware velocities → `spots_timed.csv`, `tracks_timed.csv`, `KT_tracking_summary.csv` |
| `kt_overlay.py`     | QC movie: KT circles + trails on the cell → `overlays/<base>_KToverlay.mp4` |
| `kt_detect_probe.groovy` | detection-only quality histogram (for choosing the threshold) |
| `run_kt_tracking_overnight.sh` | click-go runner: prep → track → overlay → finalize |

Output root: **`/Volumes/5 MB/kt_tracking/`** → `stacks/ results/ logs/ overlays/`

## Run

```bash
bash run_kt_tracking_overnight.sh 20260420   # one date
bash run_kt_tracking_overnight.sh all         # all trackable batches, newest cells first
```

A batch is *trackable* when it has Metaphase + Anaphase event times in the
master, is **not** Excluded, and has a rendered `*_Fluor_Cropped.tif`.

## Parameters (validated on 0420 data — `logs/probe_*.log`)

- **LoG diameter 0.5 µm** (~8 px @ 0.062 µm/px): diffraction-limited GFP KT punctum.
- **Quality threshold 2.0**: just above the noise floor (quality p99.9 ≈ 1.8–2.1
  across movies). Real KTs are the high-quality tail. Detecting at 0 finds
  ~13 000 spots/frame (all noise); thr 2.0 gives a biologically sensible
  ~3–24 KTs/frame.
- **Linking 0.8 µm**, **gap-closing 1.0 µm / 2 frames**: KTs move little frame to
  frame; brief detection dropouts are bridged.
- **Min track length 3 frames**: keep persistent tracks; KTs/frame are sparse
  (often 3–4, sometimes ~15). Spots are already high-confidence (> noise floor).
- **Sub-pixel localization + median filter ON**.

### Reading the output
- A **track is not a kinetochore.** One KT dropping out for longer than the
  gap-closing window ends its track and starts a new one when it reappears, so a
  cell with ~25 KTs can yield more tracks. Per-spot positions are correct.
- `t_sec` is real elapsed time from first ablation. **Velocity is blanked at
  acquisition seams** (multi-minute gaps between stitched acquisitions) so gaps
  don't inflate speed. Per-step distance is still recorded.
- `KT_tracking_summary.csv`: one row/batch — n_tracks, n_spots, median KT speed
  (µm/min). Sanity range for metaphase KT oscillation ≈ 0.5–2 µm/min.

## Re-tuning the threshold (e.g. a date with different brightness)

```bash
/Users/mblaauw/Downloads/Fiji/fiji --headless --run kt_detect_probe.groovy \
  "imgPath='/Volumes/5 MB/kt_tracking/stacks/<base>_KTmon.tif',diameter=0.5"
```
Pick a threshold just above the `p99.9` quality value, then set `QUALITY` in the
runner. To inspect/adjust interactively, open a `*_KTmon.tif` in Fiji →
Plugins ▸ Tracking ▸ TrackMate.
