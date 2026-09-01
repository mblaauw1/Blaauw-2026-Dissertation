# `figure_code/` — the Python behind each figure piece

One file per figure piece placed in the dissertation, **named for the piece it makes**:

```
Figure 2A.py
Figure 4 - Supplement 1B.py
Figure 5B (3) G7_prometa_single_vs_meta_triple__p4.py
```

149 files, all Python, every one checked to parse. `INDEX.csv` lists them all with the figure, the
panel letter, the internal plot id and which builder each came from.

## Where the names come from

The figure and panel come from the **legend title on each artboard**, matched by
`dataops/thesis_figure_pairing_20260826.py` — never from the artboard name, because the boards run
M1–M8 in an order that does not follow the figure numbers (main M5 is Figure 3, M4 is Figure 6, M3 is
Figure 8).

**A panel letter is not always one plot.** 46 of the 70 panels hold exactly one and are named plainly.
The other 24 hold several — Figure 3 – Supplement 2 (B) holds 28 — so those carry an ordinal in reading
order on the board (top row first, then left to right) followed by the plot id, and the ordinal is
zero-padded where a panel has ten or more.

## ⚠ One script often makes a whole figure, not one panel

These 149 files are only **59 distinct scripts**. A builder that emits many panels is copied into each
panel's file, so opening `Figure 3 - Supplement 2B (07) ….py` gives you the script that made that panel
*and its 32 siblings*. `custom_lagging_examples_outlines_20260729.py` alone backs 33 of them.

To find the part that made one specific panel, search the file for that row's `plot_id` from `INDEX.csv`
— that is the string the builder passes to `lib.record_plot`.

## These are snapshots, not live scripts

Each file is the **archived copy** of the builder as it stood when that figure was last rendered, taken
from `ablation_plots/code/` on the analysis drive. 143 of the 149 are such copies; the other 6 had no
archived copy and carry the live builder from `ablation_figures_20260625/` instead (`code_kind` in
`INDEX.csv` says which).

They are a record of method. Paths inside them are absolute to `/Volumes/4 MB`, and they import `lib.py`
from the figure library — which is in this repository at `analysis_code/figures/lib.py`, not alongside
them. Nothing here runs as-is without the analysis drive.

## The data behind each one

Every figure piece also has a recorded data spreadsheet — the table the plot was actually drawn from,
written by `lib.record_plot` at render time — plus the list of cells behind it and their movies. Those
are not tracked here (this repository is source only); they live on the analysis drive under
`PLOT_SOURCE_PACKAGES_20260831/`, in folders with these same names.

The movies sit in two pools there, holding the same 2,089 clips under identical paths: `_MOVIES/` is the
H.264 working pool (40 GB) that every manifest points at, and `_MOVIES_COMPRESSED_FOR_SHARING/` is an
H.265 CRF 35 copy (8.4 GB) that exists only so they can be sent to someone. Neither is a measurement
surface — `lib.FluorTif` reads the 16-bit TIFs, never the mp4s.
