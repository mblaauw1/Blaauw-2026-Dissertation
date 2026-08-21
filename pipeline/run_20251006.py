#!/usr/bin/env python3
"""Drive the movie_processing pipeline on 20251006 as ONE set, even though the
raw data is split across 5 MB (triple_ablation_1-25) and 3 MB (26-50).
Output -> /Volumes/4 MB/pipeline_correct. Headless (no slideshow/browser)."""
import os, sys
os.environ.setdefault("MINIMAL_OUTPUT", "1")
os.environ.setdefault("SKIP_TIGHT_CROPS", "1")
os.environ.setdefault("PIPELINE_PARALLEL", "4")
sys.path.insert(0, "/Users/mblaauw/movie_processing")
# Discovery walks the combined dir of symlinks (data split across 5 MB + 3 MB);
# os.walk skips symlinked dirs by default, so make it follow them. Discovery runs
# in the parent process only, so this parent-side patch is sufficient.
_ow = os.walk
os.walk = lambda *a, **k: _ow(*a, **{**k, "followlinks": True})
import main

COMBINED = "/Users/mblaauw/movie_processing/_combined_20251006/20251006"
OUT = "/Volumes/6 MB/pipeline_correct"  # 4 MB filled up (hub consolidation); fall back to 6 MB

# IMPORTANT: guard so spawned pool workers (macOS = spawn start method) that
# re-import this module do NOT re-run main.main() (that crashed every worker).
if __name__ == "__main__":
    # All 50 acquisitions live under COMBINED (symlinks to both drives) -> one set.
    main.find_date_folder = lambda d: COMBINED if d == "20251006" else None
    # Headless: no slideshow server / browser popups during the unattended run.
    main.generate_slideshow = lambda *a, **k: None
    extra = sys.argv[1:]
    sys.argv = ["main.py", "20251006", "--output-root", OUT] + extra
    main.main()
