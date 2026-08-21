#!/usr/bin/env python3
# N-channel audit 2026-04-06: reviewed, no changes needed (utility/tool script, not in active pipeline path)
"""Generate a PowerPoint batch review slideshow.

One slide per batch from all_batches_enriched.csv showing:
- Poster frames from combined Phase/Fluor/Ablation MP4s
- Batch metadata (date, cell type, experiment type, etc.)
- Status badge: OK / NEEDS REPROCESSING / NO OUTPUT

Usage:
    python generate_batch_review.py
"""

import csv
import io
import os
import sys
import glob

# Fix Windows console encoding
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import cv2
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.enum.text import PP_ALIGN
from pptx.dml.color import RGBColor

# ── Paths ──────────────────────────────────────────────────────────────
ENRICHED_CSV = os.path.join(os.path.dirname(__file__), "all_batches_enriched.csv")
V3_CSV = os.path.join(os.path.dirname(__file__), "260303_batches_v3.csv")
OUTPUT_PPTX = os.path.join(os.path.dirname(__file__), "batch_review.pptx")

OUTPUT_ROOTS = [
    r"D:\Pipeline Output",
    r"E:\Pipeline Output",
    r"Z:\LabShare\Microscope Users\Maddie Blaauw 2023-on\Pipeline_output",
]
# This one has {processing_date} subfolders
OUTPUT_ROOT_WITH_DATES = r"Z:\LabShare\Microscope Users\Maddie Blaauw 2023-on\Pipeline Output"

# Combined MP4 suffixes we want poster frames from
COMBINED_SUFFIXES = [
    "_Phase_Cropped_Arrow.mp4",
    "_Fluor_Cropped_Arrow.mp4",
    "_Ablation_Marked_Arrow.mp4",
]

# Slide dimensions (widescreen 16:9)
SLIDE_W = Inches(13.333)
SLIDE_H = Inches(7.5)

# Colors
GREEN = RGBColor(0x27, 0xAE, 0x60)
RED = RGBColor(0xE7, 0x4C, 0x3C)
ORANGE = RGBColor(0xF3, 0x9C, 0x12)
GRAY = RGBColor(0x7F, 0x8C, 0x8D)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
BLACK = RGBColor(0x00, 0x00, 0x00)


def build_output_index():
    """Build a dict mapping folder_name -> full_path for all pipeline output dirs."""
    index = {}

    # Flat roots (E:, Z: Pipeline_output)
    for root in OUTPUT_ROOTS:
        if not os.path.isdir(root):
            continue
        for name in os.listdir(root):
            full = os.path.join(root, name)
            if os.path.isdir(full):
                # Prefer local (E:) over network
                if name not in index:
                    index[name] = full

    # Z: Pipeline Output with date subfolders
    if os.path.isdir(OUTPUT_ROOT_WITH_DATES):
        for date_folder in os.listdir(OUTPUT_ROOT_WITH_DATES):
            date_path = os.path.join(OUTPUT_ROOT_WITH_DATES, date_folder)
            if not os.path.isdir(date_path):
                continue
            for name in os.listdir(date_path):
                full = os.path.join(date_path, name)
                if os.path.isdir(full):
                    if name not in index:
                        index[name] = full

    return index


def load_batches(csv_path):
    """Load enriched CSV and group rows by batch_number.

    Returns list of dicts, one per unique batch, with aggregated metadata.
    """
    with open(csv_path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    batches = {}
    for row in rows:
        bn = int(row["batch_number"])
        if bn not in batches:
            batches[bn] = {
                "batch_number": bn,
                "batch_id": row["batch_id"],
                "imaging_date": row.get("imaging_date", ""),
                "cell_type": row.get("cell_type", ""),
                "fluorescent_marker": row.get("fluorescent_marker", ""),
                "experiment_type": row.get("experiment_type", ""),
                "ablation_type": row.get("ablation_type_std", ""),
                "ablation_count": row.get("ablation_count_label", ""),
                "backup_folder": row.get("BackupFolderName", ""),
                "pipeline_output_dir": row.get("pipeline_output_dir", ""),
                "movies": [],
            }
        batches[bn]["movies"].append(row.get("original_filename", ""))

    # Sort by batch number
    return [batches[k] for k in sorted(batches)]


def load_v3_batch_ids(csv_path):
    """Load the 260303 v3 CSV and return set of BackupFolderName values."""
    if not os.path.isfile(csv_path):
        return set()
    with open(csv_path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return set(row.get("BackupFolderName", "") for row in rows if row.get("BackupFolderName"))


def find_output_dir(batch, output_index):
    """Find the pipeline output directory for a batch."""
    # Try BackupFolderName first, then batch_id
    candidates = []
    if batch["backup_folder"]:
        candidates.append(batch["backup_folder"])
    candidates.append(batch["batch_id"])

    for name in candidates:
        if name in output_index:
            return output_index[name]

    # Also check the pipeline_output_dir from CSV (convert Linux path to Windows)
    pdir = batch.get("pipeline_output_dir", "")
    if pdir:
        # Convert /Volumes/DumontLab... to Z:\ path
        for prefix in ["/Volumes/DumontLab-1/", "/Volumes/DumontLab/"]:
            if pdir.startswith(prefix):
                win_path = "Z:\\" + pdir[len(prefix):].replace("/", "\\")
                if os.path.isdir(win_path):
                    return win_path
    return None


def find_combined_mp4s(output_dir):
    """Find combined MP4s in the output directory.

    Returns dict: suffix_label -> path
    """
    combined_dir = os.path.join(output_dir, "combined")
    if not os.path.isdir(combined_dir):
        return {}

    found = {}
    for f in os.listdir(combined_dir):
        if not f.endswith(".mp4"):
            continue
        for suffix in COMBINED_SUFFIXES:
            if f.endswith(suffix):
                label = suffix.replace(".mp4", "").lstrip("_")
                found[label] = os.path.join(combined_dir, f)
                break
    return found


def extract_middle_frame(mp4_path):
    """Extract the middle frame from an MP4 as PNG bytes.

    Returns (BytesIO, (w,h), is_green) where is_green indicates
    the frame is green-tinted (fluorescence data).
    """
    cap = cv2.VideoCapture(mp4_path)
    if not cap.isOpened():
        return None, (0, 0), False

    n_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    vid_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    vid_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    mid = max(0, n_frames // 2)
    cap.set(cv2.CAP_PROP_POS_FRAMES, mid)
    ret, frame = cap.read()
    cap.release()

    if not ret:
        return None, (vid_w, vid_h), False

    # Detect if frame is green-tinted (fluorescence) vs greyscale (phase)
    bm = frame[:, :, 0].mean()
    gm = frame[:, :, 1].mean()
    rm = frame[:, :, 2].mean()
    is_green = gm > max(bm, rm) * 1.3 and gm > 10

    _, buf = cv2.imencode(".png", frame)
    return io.BytesIO(buf.tobytes()), (vid_w, vid_h), is_green


def assess_batch(batch, output_dir, mp4s, v3_folders):
    """Determine batch status and issues.

    Returns (status, issues) where status is one of:
      'OK', 'NEEDS REPROCESSING', 'NO OUTPUT'
    """
    issues = []

    if output_dir is None:
        return "NO OUTPUT", ["No output directory found on E: or Z:"]

    # Check for combined/ folder
    combined_dir = os.path.join(output_dir, "combined")
    if not os.path.isdir(combined_dir):
        issues.append("No combined/ folder (old pipeline version?)")
        return "NEEDS REPROCESSING", issues

    # Check for missing combined MP4s
    missing = []
    for suffix in COMBINED_SUFFIXES:
        label = suffix.replace(".mp4", "").lstrip("_")
        if label not in mp4s:
            missing.append(label)
    if missing:
        issues.append(f"Missing combined MP4s: {', '.join(missing)}")

    # Check if this is a 260303 batch that was rebuilt in v3
    batch_id = batch["batch_id"]
    folder = batch["backup_folder"] or batch_id
    if "260303" in batch_id or "260303" in folder:
        issues.append("260303 batch — rebuilt in v3, needs reprocessing")

    if issues:
        return "NEEDS REPROCESSING", issues

    return "OK", []


def add_batch_slide(prs, batch, output_dir, mp4s, status, issues):
    """Add a slide for one batch."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])  # blank layout

    # ── Title ──
    txBox = slide.shapes.add_textbox(Inches(0.3), Inches(0.15), Inches(10), Inches(0.5))
    tf = txBox.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = f"Batch {batch['batch_number']}: {batch['batch_id']}"
    p.font.size = Pt(18)
    p.font.bold = True

    # ── Subtitle (metadata) ──
    parts = []
    if batch["imaging_date"]:
        parts.append(batch["imaging_date"])
    if batch["cell_type"]:
        parts.append(batch["cell_type"])
    if batch["fluorescent_marker"]:
        parts.append(batch["fluorescent_marker"])
    if batch["experiment_type"]:
        parts.append(batch["experiment_type"])
    if batch["ablation_type"]:
        parts.append(batch["ablation_type"])
    if batch["ablation_count"]:
        parts.append(batch["ablation_count"])
    parts.append(f"{len(batch['movies'])} movies")

    sub = slide.shapes.add_textbox(Inches(0.3), Inches(0.55), Inches(10), Inches(0.4))
    stf = sub.text_frame
    stf.word_wrap = True
    sp = stf.paragraphs[0]
    sp.text = " | ".join(parts)
    sp.font.size = Pt(11)
    sp.font.color.rgb = GRAY

    # ── Original filenames ──
    files_text = ", ".join(batch["movies"][:6])
    if len(batch["movies"]) > 6:
        files_text += f" (+{len(batch['movies']) - 6} more)"
    ftx = slide.shapes.add_textbox(Inches(0.3), Inches(0.85), Inches(12.5), Inches(0.3))
    ftf = ftx.text_frame
    ftf.word_wrap = True
    fp = ftf.paragraphs[0]
    fp.text = f"Files: {files_text}"
    fp.font.size = Pt(8)
    fp.font.color.rgb = GRAY

    # ── Status badge ──
    badge_colors = {
        "OK": (GREEN, WHITE),
        "NEEDS REPROCESSING": (ORANGE, WHITE),
        "NO OUTPUT": (RED, WHITE),
    }
    bg_color, fg_color = badge_colors.get(status, (GRAY, WHITE))

    badge = slide.shapes.add_textbox(Inches(10.5), Inches(0.15), Inches(2.7), Inches(0.4))
    btf = badge.text_frame
    btf.word_wrap = False
    bp = btf.paragraphs[0]
    bp.text = status
    bp.font.size = Pt(14)
    bp.font.bold = True
    bp.font.color.rgb = fg_color
    bp.alignment = PP_ALIGN.CENTER
    # Background fill on the shape
    fill = badge.fill
    fill.solid()
    fill.fore_color.rgb = bg_color

    # ── Images (3 across) ──
    if mp4s:
        img_labels = ["Phase_Cropped_Arrow", "Fluor_Cropped_Arrow", "Ablation_Marked_Arrow"]
        display_names = ["Phase", "Fluorescence", "Ablation Marked"]
        img_top = Inches(1.2)
        img_max_w = Inches(4.1)
        img_max_h = Inches(4.3)
        label_top = img_top + img_max_h + Inches(0.05)

        # Auto-detect channel swap: if Phase file is green, swap Phase/Fluor
        channels_swapped = False
        phase_path = mp4s.get("Phase_Cropped_Arrow")
        fluor_path = mp4s.get("Fluor_Cropped_Arrow")
        if phase_path and fluor_path:
            _, _, phase_is_green = extract_middle_frame(phase_path)
            _, _, fluor_is_green = extract_middle_frame(fluor_path)
            if phase_is_green and not fluor_is_green:
                channels_swapped = True
                # Swap the paths so Phase displays grey and Fluor displays green
                mp4s["Phase_Cropped_Arrow"], mp4s["Fluor_Cropped_Arrow"] = (
                    mp4s["Fluor_Cropped_Arrow"], mp4s["Phase_Cropped_Arrow"]
                )

        if channels_swapped:
            issues.append("Channels auto-corrected (pipeline labels were swapped)")

        for i, label in enumerate(img_labels):
            left = Inches(0.3) + i * Inches(4.3)
            mp4_path = mp4s.get(label)
            if mp4_path is None:
                ph = slide.shapes.add_textbox(left, img_top + Inches(1.5), img_max_w, Inches(1))
                ph.text_frame.paragraphs[0].text = f"{display_names[i]}\n(not found)"
                ph.text_frame.paragraphs[0].font.size = Pt(12)
                ph.text_frame.paragraphs[0].font.color.rgb = GRAY
                ph.text_frame.paragraphs[0].alignment = PP_ALIGN.CENTER
                continue

            frame_data, (vid_w, vid_h), _ = extract_middle_frame(mp4_path)
            if frame_data is None:
                ph = slide.shapes.add_textbox(left, img_top + Inches(1.5), img_max_w, Inches(1))
                ph.text_frame.paragraphs[0].text = f"{display_names[i]}\n(could not read)"
                ph.text_frame.paragraphs[0].font.size = Pt(12)
                ph.text_frame.paragraphs[0].font.color.rgb = RED
                ph.text_frame.paragraphs[0].alignment = PP_ALIGN.CENTER
                continue

            # Scale image to fit slot
            if vid_w > 0 and vid_h > 0:
                aspect = vid_w / vid_h
                w = img_max_w
                h = int(w / aspect)
                if h > img_max_h:
                    h = img_max_h
                    w = int(h * aspect)
            else:
                w, h = img_max_w, img_max_h

            # Center horizontally in slot
            x_offset = (img_max_w - w) // 2
            slide.shapes.add_picture(frame_data, left + x_offset, img_top, w, h)

            # Label under image
            ltx = slide.shapes.add_textbox(left, label_top, img_max_w, Inches(0.3))
            ltf = ltx.text_frame
            lp = ltf.paragraphs[0]
            lp.text = display_names[i]
            lp.font.size = Pt(9)
            lp.font.color.rgb = GRAY
            lp.alignment = PP_ALIGN.CENTER
    else:
        # No images at all
        no_img = slide.shapes.add_textbox(Inches(2), Inches(3), Inches(9), Inches(1))
        nf = no_img.text_frame
        np_ = nf.paragraphs[0]
        np_.text = "No combined MP4s available"
        np_.font.size = Pt(20)
        np_.font.color.rgb = RED
        np_.alignment = PP_ALIGN.CENTER

    # ── Issues / notes at bottom ──
    notes_top = Inches(6.1)
    if issues:
        ntx = slide.shapes.add_textbox(Inches(0.3), notes_top, Inches(12.5), Inches(1.2))
        ntf = ntx.text_frame
        ntf.word_wrap = True
        for j, issue in enumerate(issues):
            if j == 0:
                p = ntf.paragraphs[0]
            else:
                p = ntf.add_paragraph()
            p.text = f"  {issue}"
            p.font.size = Pt(10)
            p.font.color.rgb = ORANGE

    # Output dir path
    if output_dir:
        otx = slide.shapes.add_textbox(Inches(0.3), Inches(7.0), Inches(12.5), Inches(0.3))
        otf = otx.text_frame
        op = otf.paragraphs[0]
        op.text = f"Output: {output_dir}"
        op.font.size = Pt(8)
        op.font.color.rgb = GRAY

    return slide


def main():
    print("Loading batch data...")
    batches = load_batches(ENRICHED_CSV)
    print(f"  {len(batches)} unique batches from {ENRICHED_CSV}")

    v3_folders = load_v3_batch_ids(V3_CSV)
    print(f"  {len(v3_folders)} v3 folder names from {V3_CSV}")

    print("Indexing pipeline output directories...")
    output_index = build_output_index()
    print(f"  {len(output_index)} output folders found")

    # Create presentation
    prs = Presentation()
    prs.slide_width = SLIDE_W
    prs.slide_height = SLIDE_H

    # Title slide
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    txBox = slide.shapes.add_textbox(Inches(1), Inches(2.0), Inches(11), Inches(2))
    tf = txBox.text_frame
    p = tf.paragraphs[0]
    p.text = "Batch Review Slideshow"
    p.font.size = Pt(36)
    p.font.bold = True
    p.alignment = PP_ALIGN.CENTER

    p2 = tf.add_paragraph()
    p2.text = f"{len(batches)} batches from all_batches_enriched.csv"
    p2.font.size = Pt(20)
    p2.alignment = PP_ALIGN.CENTER

    p3 = tf.add_paragraph()
    p3.text = "Pipeline output poster frames (middle frame of combined MP4s)"
    p3.font.size = Pt(14)
    p3.font.color.rgb = GRAY
    p3.alignment = PP_ALIGN.CENTER

    # Process each batch
    report_lines = []
    status_counts = {"OK": 0, "NEEDS REPROCESSING": 0, "NO OUTPUT": 0}

    # Track which output dirs have already been shown to avoid duplicates
    seen_output_dirs = {}  # output_dir -> first batch_number

    for i, batch in enumerate(batches):
        bn = batch["batch_number"]
        bid = batch["batch_id"]
        print(f"  [{i+1}/{len(batches)}] Batch {bn}: {bid}", end="")

        # Find output
        output_dir = find_output_dir(batch, output_index)
        mp4s = find_combined_mp4s(output_dir) if output_dir else {}

        # Detect duplicate output dirs — skip MP4s if already shown
        if output_dir and output_dir in seen_output_dirs:
            first_bn = seen_output_dirs[output_dir]
            mp4s = {}  # Don't show images again
            issues_extra = [f"Same output as Batch {first_bn} (shared pipeline output dir)"]
            status, issues = assess_batch(batch, output_dir, {}, v3_folders)
            issues = issues_extra + issues
        else:
            if output_dir:
                seen_output_dirs[output_dir] = bn
            # Assess status
            status, issues = assess_batch(batch, output_dir, mp4s, v3_folders)

        status_counts[status] += 1
        print(f"  -> {status}" + (f" ({len(mp4s)} MP4s)" if mp4s else ""))

        # Create slide
        add_batch_slide(prs, batch, output_dir, mp4s, status, issues)

        # Record for report
        if status != "OK":
            report_lines.append((bn, bid, status, issues))

    # Save
    prs.save(OUTPUT_PPTX)
    print(f"\nSaved: {OUTPUT_PPTX}")
    print(f"Total slides: {len(prs.slides)} (1 title + {len(batches)} batch slides)")

    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    for s, c in status_counts.items():
        print(f"  {s}: {c}")

    # Report of batches needing attention
    if report_lines:
        print(f"\n{'='*60}")
        print("BATCHES NEEDING ATTENTION")
        print(f"{'='*60}")
        for bn, bid, status, issues in report_lines:
            print(f"\n  Batch {bn}: {bid}")
            print(f"    Status: {status}")
            for issue in issues:
                print(f"    - {issue}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
