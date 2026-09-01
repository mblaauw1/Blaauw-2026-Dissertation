# ⛔ STOP — READ THIS BEFORE TOUCHING ANY FILE ON `/Volumes/4 MB`

**Any person or agent (Claude included) accessing this drive MUST read this file IN FULL first, then
`/Volumes/4 MB/NOTES.md` in full, BEFORE reading, editing, plotting from, or deleting anything here.**
Skipping this step has caused real errors (see §0). This file is the map of WHERE data lives and HOW it is
kept current. It is short on purpose.

---

## §0. THE MISTAKE THIS FILE EXISTS TO PREVENT (2026-07-19)
Measured **geometry is NOT stored as numbers in the master spreadsheet.** It is stored as **manual POINT/LINE
marks in `annotations/*.csv` and COMPUTED on the fly.** A Claude read the master column `KK_Dist (um)` (only 16
rows filled) and concluded N=13, when the real k-k data is **~100 pairs** computed from `kt_points.csv`
`pre_abl`/`pre_abl_pair` points. Correct N was 53 (with timing) / 93 batches. **If a quantity looks
suspiciously sparse in the master, it is almost certainly computed from an annotation file instead.**

## §1. AUTHORITATIVE MASTER (the one and only)
- `/Volumes/4 MB/ABLATION_MASTER.csv` — TWO-row header (row 0 = Auto/UserInput group labels, **row 1 = column
  names**; data starts row 2). ~1620 data rows. Read via `lib.load_master()` (path hard-coded in
  `ablation_figures_20260625/lib.py:5`). **Never** treat any `*backup*`, `_reviews_and_reference/cdc20_analysis_2026-06-13/`, or
  `_backup_merge*/` copy as source — they are stale 800-row snapshots. Edits go here, atomically (`.tmp`+replace).

## §2. MANUAL ANNOTATION SOURCES — `annotations/` (marks live here; geometry is COMPUTED from them)
| file | holds | derived quantity / builder |
|---|---|---|
| `kt_points.csv` (5624) | KT point marks by `label`: `pre_abl`+`pre_abl_pair` (k-k pre), `post_abl`+`post_abl_pair` (k-k post), `paired_kt` (control k-k), `polar`, `sisterless`, `lagging`, `cytosol_bg` | **k-k distance = ‖pre_abl − pre_abl_pair‖·pixel_size**, nearest-neighbour per frame → `group2_kk.py` (v2 rebinning + KK_LOWKK/near-zero/>20µm excl). intensity → group4_* |
| `chromo_lines.csv` (732) | chromosome length line marks | `G3_chromo_length*.csv` (derived); pairing lengths |
| `lagging_lengths.csv` (749) | `lagging_length` / `lagging_width` line marks (was `misc.csv`, renamed 2026-07-20) | lagging length plots |
| `meta_plates.csv` (4490) | metaphase-plate line | plate-distance |
| `poles.csv` (2765) | spindle-pole points — **NO LONGER EMPTY: 2765 rows over 20 cells as of 2026-08-18** (the "0 rows" warning below is retired; coverage is still only 20% of 1-sisterless and 18% of 3-sisterless cells, so check the cell before assuming a pole exists) | Sisterless/Paired Dist from Pole |
| `cell_outlines.csv` (1444) | per-frame cell outlines | timestrip crops |
| `SISTERLESS_PLATE_JOIN_TIMES.csv` (65) | per-chromosome congression time / at-plate / polar (structured) | sisterless behavior + congression plots |
| `CHROMO_LENGTH_BEHAVIOR_PAIRING.csv` (46) | **8781 tool output**: chrN_length_um, chrN_movement, pairing_notes | length↔behavior pairing |
| `KT_TRACKING_MASTER.csv` (316) | TrackMate track index | oscillation/velocity/plate-control |
| `kt_outlines.csv` (NEW 2026-07-22) | per-frame KINETOCHORE outline traces from the KT-outline slides. Grouping lives in `notes` as `grp:N;kttype:X;trace:M`: **`grp` = her "+ New KT" identity = ONE kinetochore** (across frames AND against other KTs on the same frame); `kttype` = polar/lagging/paired/…; `trace` lets ONE kinetochore have SEVERAL traces on ONE frame (odd/fractured shapes); `z_slice`>0 flags a frame that is a z-slice, not a timepoint. **NEVER merge polar/lagging across different `grp` — a double/triple-ablation cell can have two polar or two lagging KTs at once (NOTES §1 rule 28, 2026-08-03). Parse it with `kt_shape_metrics.grp_of`.** | KT shape/size over time; master ref `kt_outline_ids` |

**Rule:** manual marks (polar, sisterless, paired_kt, k-k, chromo length, plate) are PREFERRED over TrackMate;
geometry is computed from the point/line files, **never read from a master column** (master geometry columns are
sparse/legacy). Pixel size = master `Pixel Size (um)` (default 0.062); mp4 native res == frames.json `roi` w/h.

## §2g. COUNTS ARE REFRESHED, NOT REMEMBERED  [added 2026-08-18]
The row counts in the §2 table were 3-6x stale (kt_points 2,619 -> 5,624; meta_plates 701 -> 4,490;
kt_outlines 10,360; poles 0 -> 2,765). They are refreshed above. **Before quoting a count from this file,
re-count the store** — `dataops/annotation_headroom_20260818.py` prints coverage per store per cohort and
is the maintained version of this question.

## §2b. ⚠ TIME (`t_sec`) — READ BEFORE USING ANY TIMESTAMP  [added 2026-07-22]
- **The definition** (`~/movie_processing/process.py:863`):
  `t_sec = (file_frame_times[t_index] - timestamp_anchor_ms) / 1000`, where
  `timestamp_anchor_ms = ablation_events[0].epoch_ms - abl_start_ms`.
  **`t_sec = 0` at the FIRST ABLATION EVENT**, negative before it. Per-frame times come from the
  TIFF/MicroManager metadata. Line 865 is a FALLBACK that fabricates a flat 20 000 ms interval when
  metadata is missing.
- **THE ACQUISITION INTERVAL IS NOT 20 s.** It ranges **10 s to 503 s per batch**. Never assume it, and never
  validate a timestamp by "it lands on a 20 s multiple".
- **The pipeline BURNS the timestamp onto every movie frame** (HH:MM:SS, `int()` truncation). That is the
  ground truth of last resort — read it off the frame when anything disagrees.
- **`meta_plates.csv` t_sec was REPAIRED 2026-07-22** (3856 of 4183 rows had the browser's clip clock and a
  blank `t_hms`). `kt_points.csv` was repaired earlier the same day. `cell_outlines.csv` was never affected.
- **TWO SEPARATE BUGS EXIST — do not confuse them:**
  | symptom | what is wrong | what is right |
  |---|---|---|
  | blank `t_hms`, tiny `t_sec` | the TIME is the video clip clock | the FRAME is correct |
  | has `t_hms`, times look sane | the FRAME is stale from an older render | the TIME is correct |
  Validating a time repair against the second group is what made the first attempt fail.
- **5 batches have a `frames.json` that disagrees with their own movie** —
  `20260420 ptk2 eyfp cdc20 1 ablation_{11,13,18,20,43}`, re-rendered after the sidecar was written.
  Affects roles and event mapping too, not just times.

## §2c. ⚠ DUPLICATE IDS — LIVE BUG  [added 2026-07-22]
`kt_points` **119**, `meta_plates` **89**, `cell_outlines` 13, `chromo_lines` 2 duplicate ids, and the counts
GREW during one afternoon of annotation. `serve_annotation._autosave_replace_batch` is still minting them.
**The geometry is intact — only ids collide**, but every consumer keyed on `id` is unsafe:
**key `dataops.apply_edits` on `(id, frame)`, not `id`.** Fix the allocator before renumbering.

## §2d. FLUORESCENCE STACKS — where they actually come from  [added 2026-07-22]
`lib.FluorTif` measures the 16-bit `<batch>_Fluor_Cropped.tif` (never the mp4 — 8-bit, contrast-stretched,
clips bright KTs). **`lib._fcrop_index()` globs ALL of `/Volumes/4 MB` and keeps the FIRST hit**, so a stack
anywhere on the drive can silently become a batch's source. Of 1729 batches with a stack, 518 have more than
one copy. **`rerender_3ch_20260703` holds the ONLY copy for 13 batches — never archive or move it.**
Map fluorescence by the annotation's `frame` via `plane_by_frame`, **never by `t_sec`**.

## §2e. NEW DERIVED GEOMETRY STORES  [added 2026-07-22]
Computed FROM the primary stores by `ablation_figures_20260625/custom_primary_geometry_20260722.py`:
- `_scratch/primary_geometry_cell.json` — 188 batches × 1723 cell-level features (plate axis/centroid/length,
  cell area/perimeter/roundness, all on a shared mitotic-progress grid)
- `_scratch/primary_geometry_chrom.csv` — 119 kinetochore trajectories (distance to plate, signed position
  along the plate normal, lateral position along the plate axis, distance from cell centre)
- `_scratch/primary_chromosome_ranks.csv` — 179 chromosomes with WITHIN-CELL rank features
These are DERIVED and regenerable; the marks in `annotations/` remain the source of truth.

## §2f. TIME + ID STATUS AS OF 2026-07-22 EVENING
- **All 13 mark stores audited** (`dataops/audit_tsec_all_stores_20260722.py`). The last store still writing the
  browser clip clock was **`chromo_measure_lines.csv`** (t_sec == frame/17); `pairing_server` now derives t_sec
  from the frames.json map for the clip's OWN role (its lines are drawn on the ABLATION clip, not monitoring).
- **A row that HAS a `t_hms` must never have its `t_sec` rewritten** — for those the FRAME is the broken field.
  416 kt_points (326 polar) + 69 meta_plates rows were corrected this way and re-anchored to the right frame.
- **Duplicate ids are GONE and cannot drift back**: the id allocator moved server-side, then every store was
  renumbered. 0 ids are shared between batches in kt_points / meta_plates / cell_outlines / chromo_lines /
  kt_outlines, and the master `*_ids` columns were re-mirrored.
- **Figure numbers**: every placed figure now carries a plot number (`PLOT_SETTINGS[fig]["plot_number"]`,
  listed in `ablation_plots/PLOT_NUMBERS_20260722.csv`) and its caption on copy.ai starts with it.
- **Her hand-arranged paper-figure copies live in `1_DECKS/arranged_into_paper_figures_2.ai`**, not in
  copy.ai. Both documents link the SAME `_ai_relink/pdf/*.pdf`, so re-rendering a figure updates both.

## §3. DERIVED / PLOT DATA
- `ablation_plots/data/*.csv` (293) — one "plot spreadsheet" per figure, written by `lib.record_plot`. These are
  DERIVED from the sources in §1–§2 (source paths + mtimes + content-hash stamped in `PLOT_SETTINGS.json`). A plot
  is BUILT FROM its data CSV but DERIVED FROM the master/annotation sources — regenerate the builder if a source changed.
- `ablation_plots/ablation_figures_grouped copy.ai` — the working deck (edit BACKGROUNDED: `open -g`, no `activate`;
  one JSX; `pdfCompatible=false`; verify by mtime). "Make a plot" ALWAYS includes placing it here.

## §3b. STALENESS CHECK (run this after ANY master/annotation edit)
`PLOT_SETTINGS.json` stamps each plot's source files + mtimes + content-hash at build time. Compare current
source mtime/hash to `mtimes_at_build`/`hashes_at_build` to find plots whose source changed since last render.
**As of 2026-07-20, 116 master-derived plots were STALE** after a session of master edits — a plot on copy.ai is
NOT necessarily current. Re-render stale builders, then relink copy.ai. `poles.csv` now holds 2765 rows over 20 cells (2026-08-18; it WAS empty when this line was written) —
`kt_points.csv` `polar` label (854) is the polar-KT marks, distinct from spindle-pole points; verify pole source
before any dist-from-pole work.

## §3c. ID-KEY LINKING CONVENTION (keep it consistent — user rule)
Each annotation CSV tags its rows/sets with a unique **`id`** column. The master ablation CSV carries a matching
**`<thing>_ids`** reference column per batch, holding the id(s) of that batch's rows in the annotation file. This
makes every value locatable both ways and has worked well — KEEP redundant join keys even though batch-name joins
also work. Established pairs: `cell_outline_ids`↔cell_outlines, `kt_point_ids`↔kt_points, `chromo_line_ids`↔chromo_lines,
`meta_plate_ids`↔meta_plates, `polar_track_ids`↔polar_tracks, `pole_ids`↔poles, `timestrip_frame_ids`↔timestrip_frames,
`crop_box_ids`↔crop_boxes, `sisterless_plate_join_ids`↔SISTERLESS_PLATE_JOIN_TIMES, `kt_tracking_id`↔KT_TRACKING_MASTER,
`kt_outline_ids`↔kt_outlines,
`lagging_ids`↔lagging_lengths, `chromo_pairing_ids`↔CHROMO_LENGTH_BEHAVIOR_PAIRING.
**When you create a new annotation CSV, give it an `id` column AND add a `<name>_ids` ref column to the master.**
(2026-07-20: the two former gaps — pairing file `id` + lagging master-ref — are now closed. `misc.csv` remains
an EMPTY catch-all default in serve_annotation for genuinely-unknown future types; lagging now has its own file.)

## §4. KEEPING CURRENT / MOST-RECENT
- After editing the master or an annotation file, **regenerate the affected derived CSV + re-render the plot +
  re-place on copy.ai.** Derived files can lag their source (e.g. `G3_chromo_length.csv` was 3 days stale on
  2026-07-16). Check mtime of the derived file vs its source before trusting it.
- The 8781 slides have TWO save streams: `/save_pairing`→`CHROMO_LENGTH_BEHAVIOR_PAIRING.csv` and the `.af` panel
  `/save_annotation`→master. Verify BOTH when a user reports slide annotation work.

## §5. WHERE THE DETAIL LIVES
- Living project log + freshest facts: **`/Volumes/4 MB/NOTES.md`** (read next, in full; §14 update log at the bottom).
- Figure to-dos: `4_TABLES_AND_REPORTS/FIGURES_TODO_20260710.md`. Deferred list: `RESOLVE_LATER_*.md`.
- Claude memory index: `~/.claude/projects/-Users-mblaauw/memory/MEMORY.md`
  (esp. `reference_kk_and_point_measurements_source`, `reference_8781_pairing_server_save_streams`).

*Last verified by full data-storage scan: 2026-07-20.*  ·  *kt_outlines `grp` rule added 2026-08-03.*
