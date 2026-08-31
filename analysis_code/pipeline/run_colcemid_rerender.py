#!/usr/bin/env python3
"""Re-render specific colcemid dates from a combined symlink dir.
Usage: run_colcemid_rerender.py <DATE> <COMBINED_ROOT> <OUTPUT_ROOT>
  COMBINED_ROOT/<DATE>/ holds symlinks to the raw acquisition folders.
"""
import os, sys
os.environ.setdefault("MINIMAL_OUTPUT", "1")
os.environ.setdefault("SKIP_TIGHT_CROPS", "1")
os.environ.setdefault("PIPELINE_PARALLEL", "4")
sys.path.insert(0, "/Users/mblaauw/movie_processing")
# discovery must follow symlinked dirs (os.walk skips them by default)
_ow = os.walk
os.walk = lambda *a, **k: _ow(*a, **{**k, "followlinks": True})
import main

if __name__ == "__main__":
    DATE = sys.argv[1]
    COMBINED = os.path.join(sys.argv[2], DATE)
    OUT = sys.argv[3]
    main.find_date_folder = lambda d: COMBINED if d == DATE else None
    main.generate_slideshow = lambda *a, **k: None
    sys.argv = ["main.py", DATE, "--output-root", OUT]
    main.main()
