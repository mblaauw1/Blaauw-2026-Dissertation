"""Process a noc_ablations_washout session through the pipeline.
Usage: python run_noc.py 20251102   (or 20251104)
Raw folders are noc_washout_<date>/ on T7 1 (NOT date-named, so find_date_folder
is monkeypatched). Output FORCED to 4 MB. Headless."""
import os, sys
os.environ.setdefault("MINIMAL_OUTPUT", "1")
os.environ.setdefault("SKIP_TIGHT_CROPS", "1")
os.environ.setdefault("PIPELINE_PARALLEL", "4")
sys.path.insert(0, "/Users/mblaauw/movie_processing")
_ow = os.walk
os.walk = lambda *a, **k: _ow(*a, **{**k, "followlinks": True})
import main
SESSIONS = {"20251102": "/Volumes/T7 1/noc_washout_20251102",
            "20251104": "/Volumes/T7 1/noc_washout_20251104"}
OUT = "/Volumes/4 MB/pipeline_session_output"
if __name__ == "__main__":
    date = sys.argv[1]
    raw = SESSIONS[date]
    # SAFEGUARD: output root MUST be on an external /Volumes drive (never internal -> avoids the local-mon-save bug)
    assert OUT.startswith("/Volumes/"), f"output root not external: {OUT}"
    import shutil
    free_gb = shutil.disk_usage(OUT).free / 1e9
    assert free_gb > 100, f"only {free_gb:.0f} GB free on output drive"
    assert os.path.isdir(raw), f"raw missing: {raw}"
    print(f"[run_noc] date={date} raw={raw} OUT={OUT} ({free_gb:.0f} GB free)", flush=True)
    main.find_date_folder = lambda d: raw if d == date else None
    main.generate_slideshow = lambda *a, **k: None
    sys.argv = ["main.py", date, "--output-root", OUT]
    main.main()
