# Methods — acquisition and imaging settings
*Built 2026-08-18 from the microscope's own metadata, not from memory.*

**Where these numbers come from.** Every value below was scraped from the MicroManager `*_metadata.txt`
sidecars harvested from the acquisition drives on 2026-08-09
(`_working/_reviews_and_reference/raw_metadata_harvest/sidecars/`, 4,374 real sidecar files; the other
1,973 files there are macOS `._` resource forks, not data). The scraper is
`dataops/../_claude_tmp/methods_20260818/scrape_exposures.py`; per-file rows are in
`EXPOSURES_BY_CELLTYPE.csv` and the summary in `EXPOSURES_SUMMARY.csv`, both in this folder.
**10,817 (file × channel × exposure) records over 57 imaging dates.**
Files are joined to a cell line through `RAW_FILE_MAP_20260818.csv`; rows whose raw file is not in that
map are reported as `(unmapped)` rather than dropped.

## Hardware, as recorded by the acquisition software
| item | value | note |
|---|---|---|
| acquisition software | MicroManager 2.0.1 (build 20221211) | `MicroManagerVersion` |
| acquisition computer | `DUMONT-NIKON2-PC` | `ComputerName` |
| camera | Hamamatsu ORCA (`HamamatsuHam_DCAM`) on 10,509 of 10,817 records; Andor sCMOS on 109 | `Core-Camera` |
| binning | 2 on 9,810 records, 1 on 808 | `Binning` |
| pixel size | **0.062 µm/px** on 9,474 records; 0.031 µm/px on 662 (bin 1); 0.058 µm/px on 14 | `PixelSizeUm` |
| bit depth | 16-bit | `HamamatsuHam_DCAM-Bits per Channel` |
| channels configured | `488 (GFP)`, `Brightfield`, `561 (mCherry)`, `640 (Cy5)`, `405 (DAPI)`, `Confocal 488nm 525-50` | `ChNames` |

⚠ **The pixel size is per-acquisition, not a project constant** — read it from the batch
(master column `Pixel Size (um)`, default 0.062), never assume it.

## Exposure and frame interval, per cell line and channel
| cell line | channel | files | exposure (ms) median | exposure range | interval (s) median | interval range |
|---|---|---:|---:|---|---:|---|
| (unmapped) | 405 (DAPI) | 85 | 100.0 | 100.0–5000.0 | 20.0 | 3.0–20.0 |
| (unmapped) | 488 (GFP) | 1231 | 200.0 | 75.0–500.0 | 20.0 | 3.0–320.0 |
| (unmapped) | 561(mCherry) | 134 | 200.0 | 100.0–5000.0 | 20.0 | 3.0–20.0 |
| (unmapped) | 640 (Cy5) | 89 | 50.0 | 50.0–5000.0 | 20.0 | 3.0–20.0 |
| (unmapped) | Brightfield | 1151 | 200.0 | 200.0–500.0 | 20.0 | 3.0–320.0 |
| eYFP cdc20 | 488 (GFP) | 1807 | 200.0 | 75.0–5000.0 | 20.0 | 1.0–3600.0 |
| eYFP cdc20 | Brightfield | 1806 | 200.0 | 100.0–500.0 | 20.0 | 1.0–3600.0 |
| eYFP cdc20 | Confocal 488nm 525-50 | 36 | 200.0 | 200.0–200.0 | 30.0 | 3.0–60.0 |
| eYFP cdc20 | Default | 2 | 300.0 | 200.0–300.0 | 11.5 | 3.0–20.0 |
| eYFP mad1 | 488 (GFP) | 139 | 200.0 | 100.0–300.0 | 30.0 | 3.0–180.0 |
| eYFP mad1 | 561(mCherry) | 20 | 100.0 | 100.0–200.0 | 3.0 | 3.0–20.0 |
| eYFP mad1 | Brightfield | 150 | 300.0 | 200.0–500.0 | 30.0 | 3.0–180.0 |
| hec1-halo + eYFP mad1 | 488 (GFP) | 127 | 200.0 | 200.0–200.0 | 20.0 | 3.0–20.0 |
| hec1-halo + eYFP mad1 | 561(mCherry) | 64 | 200.0 | 200.0–200.0 | 20.0 | 3.0–20.0 |
| hec1-halo + eYFP mad1 | 640 (Cy5) | 41 | 300.0 | 300.0–300.0 | 20.0 | 3.0–20.0 |
| hec1-halo + eYFP mad1 | Brightfield | 135 | 200.0 | 200.0–300.0 | 20.0 | 3.0–20.0 |

**Reading this table.** Exposure is genuinely different per line and channel, which is why it cannot be
stated once for the whole paper:
* **eYFP-Cdc20** — 200 ms on both 488 and brightfield is the working setting.
* **eYFP-Mad1** — 200 ms on 488 but **300 ms on brightfield**, and a longer typical interval (30 s).
* **Hec1-Halo + eYFP-Mad1** — 200 ms on 488/561, **300 ms on 640 (Cy5)**, 200 ms brightfield.
* The 5,000 ms values in the `(unmapped)` rows are single-frame snaps/z-stacks, not time-lapse frames.

**Frame interval is bimodal by design, not by drift:** 3 s (4,682 records) for the ablation portion and
20 s (4,684 records) for the monitoring portion, with 15/30/40/60/120/300 s used for specific
acquisitions. **Never assume 20 s** — NOTES §1 rule 16, and the per-batch interval ranges 10–503 s.

## What still has to come from the lab notebook, not from metadata
The sidecars do not record any of these, so they must be written from her records:
* objective, NA and immersion; any additional magnification lens
* the ablation laser: wavelength, pulse duration, repetition rate, energy at the sample, and how the
  targeting coordinate was set (the sidecars log only that an ablation happened, via the PAS log)
* temperature, medium, and the imaging chamber
* the fluorophore/label chemistry (Janelia Fluor dye used for the HaloTag, transfection or line origin)
* nocodazole dose for the exhaustion arm — **still unrecorded anywhere on the drive** (3.3 µM is an inference)

For the ablation parameters a directly comparable published setup is Elting et al. 2017
(*Current Biology* 27:2112, Dumont lab): 551 nm, 20–30 pulses of 3 ns at 20 Hz through a galvo-steered
MicroPoint system driven from MetaMorph, ~1 µm ablation spot, ablation verified by loss of centromere
tension and/or depolymerization.
