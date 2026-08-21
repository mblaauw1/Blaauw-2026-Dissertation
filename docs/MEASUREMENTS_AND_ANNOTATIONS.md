# Methods — everything that was annotated, how, and with what code
*Built 2026-08-18. Every count, clip and channel below was measured from the annotation stores
themselves (`/Volumes/4 MB/annotations/*.csv`), not recalled.*

## How annotation worked, in one paragraph
Movies are processed by the pipeline (`~/movie_processing/`) into per-batch clips — an **ablation clip**
(fast, 3 s frames, fluorescence only) and a **monitoring clip** (20 s frames, phase + fluorescence) — plus
a 16-bit ROI-cropped TIF stack per channel. Annotation is done in a browser: a per-batch HTML page built
by `make_annotation_html.py` / `make_outline_html.py` displays the clip frame-by-frame and each tool
records either a **point click**, a **two-point line**, or a **traced polygon** in movie-pixel coordinates.
A small local server, `serve_annotation.py`, receives each save, routes the row to the per-type CSV by its
`type` field, allocates the row id server-side, and mirrors the id back into the master spreadsheet
(`<thing>_ids` columns). Packages are served on ports **8811** (KT tracing) · **8812** (MUGs) · **8813**
(Mad1) · **8814** (IF) · **8815** (IF paired) · **8816** (cdc20 2/3-sisterless on-target) · **8817**
(lagging count) · **8820** (figure batches); the per-chromosome pairing tool and the event-scoring review
deck run on **8781** (`pairing_server.py`, `range_server.py`).
**No geometry is stored as a number by the annotator** — marks are stored as coordinates and every
quantity is computed from them afterwards, so a measurement can always be recomputed from her marks.

**Code to cite / upload to GitHub**
| role | file |
|---|---|
| annotation page builder | `~/ablation-pipeline/analysis_slides_package/make_annotation_html.py`, `make_outline_html.py` |
| annotation server (routing, id allocation, master mirror) | `~/ablation-pipeline/analysis_slides_package/serve_annotation.py` |
| per-chromosome pairing tool + event scoring | `pairing_server.py`, `range_server.py` (now in `_ARCHIVE/one_off_scripts/`) |
| slide/package builders | `kt_outline/build_*_slides.py`, `dataops/make_timestrip_setup_v2_20260809.py` |
| shared measurement library | `ablation_figures_20260625/lib.py` |
| kinetochore shape metrics | `ablation_figures_20260625/kt_shape_metrics.py` |
| kinetochore tracking from her outlines | `ablation_figures_20260625/kt_tracks.py` |
| k-k distance | `ablation_figures_20260625/group2_kk.py` |
| automated spot tracking (secondary) | TrackMate in Fiji, indexed by `annotations/KT_TRACKING_MASTER.csv` |
| integrity checks | `dataops/checks.py` |

⚠ **The annotation server code lives on the laptop, not on the drive** (`~/ablation-pipeline/`), which is
the one part of this toolchain that is not on 4 MB. Copy it to the drive before relying on it long-term.

## The annotations themselves

| what she marked | store (rows / cells) | geometry | clip | frames used | what it becomes |
|---|---|---|---|---|---|
| cell outline, per frame | `cell_outlines.csv` (1,444 / 189) | traced polygon | monitoring 88%, ablation 12% | **phase 97%** | cell area, roundness, centroid movement (G1 family); every timestrip crop |
| kinetochore points | `kt_points.csv` (5,624 / 144) | point click | monitoring 61%, ablation 39% (of rows carrying a clip tag) | **fluorescence** | k-k distance, KT intensity, polar/lagging/sisterless positions |
| kinetochore outlines | `kt_outlines.csv` (10,360 / 66) | traced polygon | monitoring (10,355 of 10,360) | **fluorescence** | KT shape/size over time (G6 family), distortion along the spindle axis |
| metaphase plate | `meta_plates.csv` (4,490 / 82) | two-point line | monitoring | phase 458 / fluorescence 176 (3,856 older rows untagged) | plate axis and normal, plate width, distance-to-plate, plate rotation |
| chromosome length | `chromo_lines.csv` (732 / 104) | two-point line | monitoring 77%, ablation 23% | **phase 93%** | chromosome length (G3 family), length↔behaviour pairing |
| lagging chromosome length/width | `lagging_lengths.csv` (749 / 6) | two-point line | monitoring | fluorescence | lagging stretch |
| spindle poles | `poles.csv` (2,765 / 20) | point click | monitoring | fluorescence | pole–pole axis, distance from pole |
| congression / behaviour per chromosome | `CHROMOSOME_MASTER.csv` (188), `SISTERLESS_PLATE_JOIN_TIMES.csv` (65), `PREABL_CHROMOSOME_ASSIGNMENT.csv` (189), `CHROMO_LENGTH_BEHAVIOR_PAIRING.csv` (46) | structured table entry | — | — | congression time, at-plate/polar outcome |
| mitotic event times | master columns `NEB Time`, `Metaphase Start`, `Anaphase Onset`, `Cytokinesis Onset` | timestamp scored on the movie | monitoring | phase | every duration in the paper |
| automated KT tracks | `KT_TRACKING_MASTER.csv` (316) | TrackMate detection + LAP tracking | monitoring | fluorescence | oscillation/velocity where no manual track exists |

**Labels within `kt_points`** (n rows): `sisterless` 2,658 · `polar` 853 · `cytosol_bg` 656 ·
`paired_kt` 372 · `lagging` 326 · `pre_abl` 205 · `pre_abl_pair` 193 · `post_abl` 180.
**Labels within `kt_outlines`**: `paired` 6,261 · `polar` 2,531 · `lagging` 1,511.

**Manual always wins.** Where a manual mark and a TrackMate track both exist for the same object, the
manual mark is used and the two are never mixed on one plot (NOTES §1 rule 1). TrackMate is used only
where no manual equivalent exists.

## How each measurement is computed

| measurement | definition as implemented | code | package |
|---|---|---|---|
| **k-k distance** | ‖`pre_abl` − `pre_abl_pair`‖ × pixel size, nearest-neighbour matched per frame; the ablation-target pair (`pre_abl`) and the untargeted control pair (`paired_kt` / `paired`) are **never pooled** | `group2_kk.py`, `kt_tracks.py` | numpy |
| **kinetochore point localisation** | `snap_to_peak`: 10-px search radius, Gaussian smoothing σ = 1.5, **area centroid** of the peak region (not brightest pixel) — median move 3.00 → 2.21 px | `lib.snap_to_peak` | numpy, scipy.ndimage |
| **kinetochore intensity** | Σ over a disk (r = 8–9 px) on the **raw 16-bit** `*_Cropped.tif`, minus either the same-frame `cytosol_bg` disk or a local annulus background (`disk_local_bg`, r+3 to r+9, 40th percentile); floored at 0; saturated disks excluded | `lib.disk_sum`, `lib.disk_local_bg`, `lib.FluorTif` | tifffile, numpy |
| **kinetochore shape** | traced polygons rasterised into one boolean mask (PIL polygon fill, so the traced line itself is inside the object — her rule); area, perimeter, convex hull, solidity, convexity, circularity all read off **that one mask**; several traces of one `grp` on one frame are one kinetochore | `kt_shape_metrics._raster`, `_combined_metrics` | Pillow, OpenCV |
| **kinetochore extent / stretch** | **rotating calipers on the convex hull** — max Feret (end-to-end) and min Feret (narrowest width over all rotations). The ellipse fit was retired on 2026-08-03: an ellipse is a 5-parameter model and a fractured lagging kinetochore is not an ellipse | `kt_shape_metrics._calipers` | OpenCV, numpy |
| **metaphase plate** | her two-point line per frame defines the plate axis; the plate normal is its perpendicular; distances are signed projections onto that normal | `lib`, `kt_tracks.py` | numpy |
| **plate width** | length of her drawn plate line: **median 23.0 µm per cell** (IQR 20.1–26.4, range 14.4–32.9, 82 cells, 4,490 lines) | computed 2026-08-18 | numpy |
| **plate thickness** | SD of paired-kinetochore distances to the plate, per frame, median per cell: **1.02 µm** (IQR 0.86–1.46, 21 cells) — the same definition as Jaqaman et al. 2010 | computed 2026-08-18 | numpy |
| **chromosome length** | length of her drawn line × pixel size, on the phase frame | `group3_*`, pairing tool | numpy |
| **distortion along the spindle axis** | KT extent measured **along one axis, the per-frame plate normal** — never converted to a k-k distance and never compared across cells without normalising | `KT_LOADING_AXIS_20260805.csv` builder | numpy |
| **mitotic timing** | `t_sec = 0` at the first ablation event; every duration is a difference of her scored event times, recomputed rather than stored | `lib`, master | — |
| **statistics** | Mann-Whitney U (two-sided) or Kruskal-Wallis, Fisher exact for proportions, Wilcoxon signed-rank for paired within-cell tests; **one value per cell before any test** | builders + `dataops/pseudoreplication_scan_20260818.py` | scipy.stats |

Python 3.14 with numpy, scipy, OpenCV (`cv2`), Pillow, tifffile and matplotlib; Fiji/TrackMate for the
automated tracks. Nothing is measured in ImageJ by hand.

## Published precedent for each approach (for the Methods citation list)

| our approach | precedent |
|---|---|
| manual, frame-by-frame tracking of kinetochores/poles in custom code rather than an automated tracker | Elting MW, Hueschen CL, Udy DB, Dumont S. *J Cell Biol* 2014;206:245 — and Elting MW, Prakash M, Udy DB, Dumont S. *Curr Biol* 2017;27:2112, which states "manual tracking in home-written MATLAB programs" |
| laser ablation of a spindle target, with success judged from the response rather than from the laser log | Elting et al. 2017 (551 nm, 3 ns pulses, 20 Hz, MicroPoint/MetaMorph, ~1 µm spot; ablation verified by loss of centromere tension and/or depolymerization) |
| drawing measurement ROIs/lines by hand in FIJI and measuring from them | Richter M, Neahring L, Tao J, Sutanto R, Cho NH, Dumont S. *eLife* 2023;12:e85208 — line-profile ROIs with a spline fit, drawn per k-fiber |
| **the metaphase plate as a line fitted through kinetochore positions** | Richter et al. 2023: "a line of best fit was drawn through kinetochore positions in a cell" |
| **plate thickness = SD along the plate normal**, plate plane from the kinetochore position covariance, aligned = within 2.5σ | Jaqaman K, King EM, Amaro AC, et al. *J Cell Biol* 2010;188:665 (plate thickness 0.1–1.2 µm in HeLa; ours 1.02 µm) |
| reporting both the measurement count and the cell count | Richter et al. 2023 use exactly this convention: *n* = individual measurements, *N* = cells |
| brightness/contrast adjusted only linearly and over the whole image, for display | *J Cell Biol* editorial policy (Rossner & Yamada, *J Cell Biol* 2004;166:11) — linear adjustments to the whole image are acceptable; any nonlinear/gamma adjustment must be disclosed in the legend |

*(Author lists for the two Elting papers should be checked against the PDFs before submission; the
methods statements quoted above were read from the papers themselves.)*

---

## Which of these actually feed the active decks
`ANNOTATION_TYPES_IN_ACTIVE_DECKS.md` (this folder) narrows the table above to the mark types that
feed a figure placed on one of the five live `.ai` files, and adds, per type: the cell types it was
gathered on, whether it was marked on the **ablation** or **monitoring** clip (or both), the channel it
was **annotated** on, and the channel the measurement is **gathered** from — which differ for the
Hec1-Halo/Mad1 `paired_kt` marks (placed on 640, measured on 488 **and** 640).
