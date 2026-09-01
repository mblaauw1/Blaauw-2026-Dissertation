# Blaauw 2026 — dissertation analysis code

Source code for the laser-ablation kinetochore project: everything that **gathers the data** from
raw microscope acquisitions and everything that **makes the figures** currently placed in the five
live Adobe Illustrator decks.

## Layout

Two folders, added 2026-08-31:

* **`analysis_code/`** — everything this repository already held, unmoved: the pipeline, the annotation
  tools, the figure library, the deck automation and the data-integrity tools. Nothing inside it changed.
* **`figure_code/`** — the Python behind each figure piece in the dissertation, one file per piece,
  named for the piece: `Figure 2A.py`, `Figure 4 - Supplement 1B.py`. See `figure_code/README.md`.

This repository is **source only**. No image data, no annotation tables, no rendered figures and no
`.ai` documents are tracked here — those live on the analysis drive (`/Volumes/4 MB`). Paths inside
the scripts are absolute to that drive; the code is published as a record of method, not as a
turnkey package.

---

## What the project measures

PtK2 cells expressing eYFP-Cdc20, eYFP-Mad1 or Hec1-Halo + Mad1 are imaged through mitosis while
individual kinetochores are destroyed by laser ablation (1, 2 or 3 sisterless kinetochores per cell,
plus off-target and unmanipulated controls). The analysis asks how a cell with unattachable
kinetochores progresses through metaphase — metaphase duration, chromosome congression, sister
kinetochore–kinetochore (k–k) distance and oscillation, kinetochore shape and distortion, lagging
chromosomes at anaphase, and Mad1/SAC signal at the ablated kinetochore.

## The decks these figures live in

Figure placement is tracked in `analysis_code/config/DECKS.json`, which is the single place the deck paths are
written down.

| tag | role | file |
|---|---|---|
| `0814` | main working | `META_FIGURES_20260814.ai` |
| `0813supp` | supplemental working | `META_FIGURES_20260813_supplemental.ai` |
| `newfig` | new figures | `NEW_FIGURES_20260804.ai` |
| `supp` | other | `other_20260820.ai` |
| `newts` | timestrips | `NEW_TIMESTRIPS_20260804.ai` |
| `pub0814` | main, publication copy | `META_FIGURES_20260814_PUBLICATION_20260820.ai` |
| `pub0813` | supplemental, publication copy | `META_FIGURES_20260813_supplemental_PUBLICATION_20260820.ai` |

**`analysis_code/docs/DECK_FIGURE_BUILDER_MAP.csv` maps every placed figure to the script in this repository that
generates it** — 828 distinct figures, 1,135 placements, 123 builder scripts, resolved from the
Illustrator geometry dumps of 2026-08-21 together with `PLOT_SETTINGS.json`, which records the
generating script for every registered figure.

---

## Repository layout

```
analysis_code/          the toolchain, unchanged -- every folder this repository already had
  pipeline/            raw acquisition -> processed batch
  annotation_tools/    the browser tools the manual marks are made in
  kt_outline/          per-cell annotation packages + the slide servers (ports 8810-8820)
  kt_tracking/         TrackMate detection/tracking (`fiji/`) + the scoring harness that tuned it
  figures/             the figure library: lib.py, the shared measurement modules, every builder
  deck/                Illustrator automation (ExtendScript) that places and audits the decks
  dataops/             integrity checks, data repairs, audits, figure addressing, provenance tools
  tools/               small CLIs used while working (background jobs, deck freeze, task list)
  docs/                methods and provenance documentation
  config/              small registries the code reads (deck paths, accepted-loss registers)

figure_code/            one Python file per figure piece, named for the piece it makes
```

### `analysis_code/pipeline/` — data gathering

`main.py` is the entry point. `discover.py` groups raw MicroManager `.ome.tif` acquisitions into
**batches** (one batch = one cell), reads channel/exposure/pixel-size/stage metadata
(`metadata.py`), and `process.py` renders each batch into the working products every later stage
reads:

* `<batch>_Phase_Cropped.tif` / `<batch>_Fluor_Cropped.tif` — the 16-bit stacks **all quantification
  is measured from** (never the mp4s, which are 8-bit and contrast-stretched);
* `<batch>_{Pre,Ablation,Monitoring}.mp4` per channel — the clips the manual annotation is done on,
  with the acquisition timestamp burned onto every frame;
* `<batch>_frames.json` — the per-frame sidecar: role (pre/ablation/monitoring), channel, `t_sec`,
  the tif page each frame maps to, and the ablation events with their epoch and pixel coordinates.

`t_sec = 0` is the **first ablation event**, so pre-ablation times are negative. The acquisition
interval is not constant — it ranges from 10 s to 503 s between batches, so a timestamp is always
read from the frame's own record.

### `analysis_code/annotation_tools/` — where the measurements come from

Nearly every quantity in this project is computed from **hand-drawn marks**, not from an automatic
detector. `make_annotation_html.py` generates the browser annotation interface (frame-accurate
re-encoded clips, freehand tracing, point marking, per-kinetochore grouping, zoom); `serve_annotation.py`
serves it and writes the marks; `pairing_server.py` and `range_server.py` serve the review and
chromosome-pairing decks.

The marks are stored per type in `annotations/*.csv` on the drive — kinetochore points, kinetochore
outlines, cell outlines, metaphase-plate lines, chromosome-length lines, spindle poles, cytosol
background disks — and the master spreadsheet carries a matching `<thing>_ids` column per batch so
every value is locatable in both directions.

**Measured geometry is computed from those marks at analysis time; it is not stored as numbers in the
master spreadsheet.** `analysis_code/docs/DATA_MODEL_AND_SOURCES.md` states which file holds what and which
script derives each quantity.

### `analysis_code/figures/` — the figure library

`lib.py` is the shared base: it loads the master spreadsheet (two-row header), assigns cohorts and
applies the standing exclusions, reads the 16-bit stacks, holds the palette, the journal style, the
significance/violin conventions, and the `record_plot()` provenance recorder. It also installs a
`Figure.savefig` hook so a single save emits the PNG, an SVG, the working PDF the decks link, and
the title-free publication PDF the publication decks link.

Measurement modules that several builders share:

| module | what it computes |
|---|---|
| `kt_shape_metrics.py` | kinetochore shape from a traced outline — area, perimeter, circularity, solidity from one raster of the traced polygon; extent by **rotating calipers** (max/min Feret), not an ellipse fit; multi-piece handling for fractured kinetochores |
| `kt_tracks.py` | links outlines of one kinetochore across frames; carries the microscope's own recorded stage position alongside the traced coordinates |
| `kt_landmark_analysis.py` | plate-anchored geometry: distance to plate, position along the plate normal and axis |
| `kt_sisters.py`, `kt_tension.py` | sister pairing, k–k distance, spindle-axis distortion |
| `osclib.py` | metaphase-window oscillation: plate-relative position, amplitude (SD), period (zero crossings) |
| `ts_render.py`, `group_timestrips.py` | timestrip rendering: crop, clamp, scale bar, ablation marker, portion assembly |
| `trendlib.py`, `canon_labels.py`, `metaphase_medians.py` | trend + SEM-across-cells bands, canonical axis labels and cohort names, the canonical group median lines |

Builders are run directly (`python3 group1_roundness.py`) from inside the figures directory.
Environment flags change what a run emits rather than what it measures: `PUB=1` (publication
render), `PERCELL=1` (per-cell line variant), `KT_COHORT=mad1` (the Mad1 cohort instead of Cdc20),
and several builders take `*_ONLY=<batch>` to render one cell instead of the whole set.

`analysis_code/deck/archived_builders/` holds eleven generating scripts that exist **only** as the snapshot
`record_plot()` archived at build time — their original files are gone, and they are the sole source
for the figures they make.

### `analysis_code/dataops/` — keeping the data honest

`checks.py` runs 30 independent cross-checks over the master and every annotation store (row loss,
duplicate ids, impossible event orders, id-mirror consistency, deck-path validity, publication-twin
freshness). The rest are one-purpose tools: repairs that back up, write atomically and verify by
re-reading; audits (`pseudoreplication_scan`, `exclusion_consistency`, `audit_ellipse_residue`,
`stats_inventory`, `error_hunt`); and `figref.py`, which addresses any figure either by its
analysis_code/deck/artboard/panel letter or by matching a pasted image against the placed figures.

### `analysis_code/deck/` — Illustrator automation

ExtendScript passes that place figures, relink them, draw panel letters and legend bullets, dump
deck geometry read-only, and audit for overlaps, broken links and aspect drift. Deck geometry is
always read from a read-only dump, and figures are placed as **linked** PDFs so re-rendering a
builder updates every deck that carries it.

---

## Conventions that the code depends on

* The master spreadsheet has a **two-row header** (row 0 = category band, row 1 = column names,
  data from row 2). `lib.load_master()` handles it; a plain `csv.reader` does not.
* Annotation frame numbers index the **fluorescence clip**, not the tif page and not all frames of
  the phase movie. `FRAME_CALIBRATION.csv` maps between them, per role.
* Manual marks take precedence over TrackMate everywhere, and the two are never mixed on one figure
  without the figure saying so.
* Metaphase ablations, 4-sisterless cells and drug-treated cells are excluded from every figure by
  default; collagen is a plating substrate, not a drug.
* Cohort comparisons aggregate to the **cell** before testing — per-track p-values are
  pseudoreplication.
* Every figure registers its plotted values, its source files and their content hashes through
  `lib.record_plot()`, which is what makes staleness and provenance checkable.

## Dependencies

Python 3 with `numpy`, `scipy`, `matplotlib`, `opencv-python` (`cv2`), `tifffile`, `Pillow`,
`scikit-image`, `scikit-learn`, `python-pptx`, `reportlab`, `PyMuPDF` (`fitz`), `imageio`.
The Illustrator passes are ExtendScript (`.jsx`), driven through `osascript`.
Kinetochore detection and tracking run headless in Fiji/TrackMate via the Groovy scripts in
`analysis_code/kt_tracking/fiji/` — `kt_trackmate_v3.groovy` at `targetspf=20` is the operating point in use
(87% recall against the manual marks on the benchmark set, chosen with `run_iter.py` +
`score_vs_manual.py`).

## What is deliberately not here

Raw and processed image data, the annotation tables, the master spreadsheet, rendered figures, the
`.ai` decks, and the ~3,100 per-figure code snapshots that `record_plot()` archives at build time
(the eleven whose live builder no longer exists are included, in `analysis_code/deck/archived_builders/`).
