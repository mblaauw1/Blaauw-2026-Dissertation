#!/usr/bin/env python3
"""Apply the user's 2026-07-22 Mad1-slide notes to ABLATION_MASTER.csv.

Her notes are observations made while reviewing the 8813 Mad1 slides.  Each one is written verbatim
into `annotation_notes` (appended, never overwriting what is there) so it survives outside the chat,
plus the two factual corrections they contain:
  * 20260303 Mad1_Ptk_Eyfpcdc2_ablation_1metaphase_13 -- Cell Type said "eYFP mad1"; the batch is a
    cdc20 cell ("this opened with mad1 batches but is actually cdc20").  The other five she flagged
    already read "eYFP cdc20".
  * the four 20260304 Mad1_timelapse cells she wants used for a timestrip -> timestrip_candidate = yes.

Run with --apply.  Backs up first, writes atomically, verifies by re-reading.
"""
import csv, os, sys, shutil, datetime

MP = "/Volumes/4 MB/ABLATION_MASTER.csv"
APPLY = "--apply" in sys.argv

NOTES = {
 "20260303 Mad1_Ptk_Eyfpmad1_ablation_4":
   "[2026-07-22 user] shown on slides WITHOUT an ablation marker; ablation marker to be added (3 PAS events exist).",
 "20260304 Mad1_ablation_20":
   "[2026-07-22 user] different marks, still interesting: polar and plate marked in prometaphase, then one "
   "timepoint during metaphase with a polar chromosome / sisterless kinetochore marked.",
 "20260304 Mad1_timelapse_1_xy2":
   "[2026-07-22 user] no ablation; beautiful movie of a Mad1 cell through mitosis starting at prophase. USE FOR "
   "TIMESTRIP. Crop box defined (rounded to the standard crop box). Mad1-localizing kinetochores marked from past "
   "NEBD until anaphase onset -- can quantify as the metaphase plate forms. Background, crop region and metaphase "
   "plate marked.",
 "20260304 Mad1_timelapse_1_xy6":
   "[2026-07-22 user] same as 20260304 Mad1_timelapse_1_xy2: no ablation, prophase->anaphase Mad1 movie, use for "
   "timestrip, crop box + background + plate + Mad1 kinetochores marked.",
 "20260304 Mad1_timelapse_1_xy7":
   "[2026-07-22 user] same as 20260304 Mad1_timelapse_1_xy2: no ablation, prophase->anaphase Mad1 movie, use for "
   "timestrip, background + plate + Mad1 kinetochores marked.",
 "20260304 Mad1_timelapse_2_xy1":
   "[2026-07-22 user] same as 20260304 Mad1_timelapse_1_xy2: no ablation, prophase->anaphase Mad1 movie, use for "
   "timestrip, background + plate + Mad1 kinetochores marked.",
 "20260310 ptk2_eyfp_mad1_14":
   "[2026-07-22 user] ablation of ONE of a pair of Mad1-localizing kinetochores on a chromosome at a pole while the "
   "rest of the chromosomes are near the metaphase plate. The chromosome stays at the pole with the remaining "
   "kinetochore Mad1-active. Cell outline, metaphase plate, cytosol background, sisterless kinetochore and the "
   "kinetochore pair before/after ablation are all marked, to show that as cell roundness increases and the "
   "kinetochore is forced closer to the plate, Mad1 delocalizes. Chromosome length and crop region also marked.",
 "20260313 ptk_eyfp_mad1_Hec1halo_640_4_xy5":
   "[2026-07-22 user] crop box + cytosol background markers added (the cytosol marker positions give background in "
   "EITHER channel). For 640 use the display shown in the video in the second row to the right -- it looks better "
   "than the version to the left.",
 "20260313 ptk_eyfp_mad1_Hec1halo_640_4_xy6":
   "[2026-07-22 user] falls out of focus before anaphase; not the best to use.",
 "20260313 ptk_eyfp_mad1_Hec1halo_640_4_xy8":
   "[2026-07-22 user] crop box defined. The second-row-right 640 display is better than the left EXCEPT for two "
   "quirks to fix: a constant dark burn-in splotch in the same spot on every frame (darker than the rest of the "
   "background), and frames after frame 5 are completely black in that channel version -- possibly from the "
   "processing that removed the purple vertical stripes.",
 "20260303 Mad1_Ptk_Eyfpcdc2_ablation_1metaphase_13":
   "[2026-07-22 user] opened with the Mad1 batches but is actually a cdc20 cell -- Cell Type corrected to eYFP cdc20.",
 "20260303 Mad1_Ptk_Eyfpcdc2_ablation_1metaphase_22":
   "[2026-07-22 user] opened with the Mad1 batches but is actually a cdc20 cell.",
 "20260303 Mad1_Ptk_Eyfpcdc2_ablation_1metaphase_24":
   "[2026-07-22 user] opened with the Mad1 batches but is actually a cdc20 cell.",
 "20260303 Mad1_Ptk_Eyfpcdc2_ablation_1metaphase_26":
   "[2026-07-22 user] opened with the Mad1 batches but is actually a cdc20 cell.",
 "20260303 Mad1_Ptk_Eyfpcdc2_ablation_1metaphase_52":
   "[2026-07-22 user] opened with the Mad1 batches but is actually a cdc20 cell.",
 "20260303 Mad1_Ptk_Eyfpcdc2_ablation_1metaphase_54":
   "[2026-07-22 user] opened with the Mad1 batches but is actually a cdc20 cell. Checked for an ablation movie: "
   "a *_Phase_Ablation.mp4 / *_Fluor_Ablation.mp4 DOES exist, but frames.json records ZERO ablation events for it "
   "(no PointAndShoot entries), so nothing was actually ablated in that clip.",
}
CELLTYPE_FIX = {"20260303 Mad1_Ptk_Eyfpcdc2_ablation_1metaphase_13": "eYFP cdc20"}
TIMESTRIP = ["20260304 Mad1_timelapse_1_xy2", "20260304 Mad1_timelapse_1_xy6",
             "20260304 Mad1_timelapse_1_xy7", "20260304 Mad1_timelapse_2_xy1"]

rows = list(csv.reader(open(MP)))
hi = next(i for i, r in enumerate(rows) if r and r[0].strip() == "Batch Name")
hdr = [c.strip() for c in rows[hi]]
bi = hdr.index("Batch Name")


def col(name):
    return hdr.index(name) if name in hdr else None


ci_note = col("annotation_notes")
ci_ct = col("Cell Type")
ci_ts = col("timestrip_candidate")
print("columns:", {"annotation_notes": ci_note, "Cell Type": ci_ct, "timestrip_candidate": ci_ts})

n_note = n_ct = n_ts = miss = 0
for r in rows[hi + 1:]:
    if not r or len(r) <= bi:
        continue
    b = r[bi].strip()
    if b not in NOTES:
        continue
    while len(r) < len(hdr):
        r.append("")
    if ci_note is not None:
        cur = r[ci_note].strip()
        if NOTES[b] not in cur:
            r[ci_note] = (cur + " | " if cur else "") + NOTES[b]; n_note += 1
    if b in CELLTYPE_FIX and ci_ct is not None and r[ci_ct].strip() != CELLTYPE_FIX[b]:
        r[ci_ct] = CELLTYPE_FIX[b]; n_ct += 1
    if b in TIMESTRIP and ci_ts is not None and r[ci_ts].strip().lower() not in ("yes", "true", "1"):
        r[ci_ts] = "yes"; n_ts += 1
seen = {r[bi].strip() for r in rows[hi + 1:] if r and len(r) > bi}
miss = [b for b in NOTES if b not in seen]

print(f"notes written={n_note}  cell_type_fixed={n_ct}  timestrip_flagged={n_ts}  not_in_master={miss}")
if APPLY:
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    shutil.copy(MP, f"/Volumes/4 MB/_master_backups/ABLATION_MASTER_pre_mad1notes_{ts}.csv")
    tmp = MP + ".tmp"
    with open(tmp, "w", newline="") as f:
        csv.writer(f).writerows(rows)
    os.replace(tmp, MP)
    chk = list(csv.reader(open(MP)))
    print("WROTE", MP, "rows", len(chk), "verified", chk == rows)
else:
    print("(dry run -- pass --apply)")
