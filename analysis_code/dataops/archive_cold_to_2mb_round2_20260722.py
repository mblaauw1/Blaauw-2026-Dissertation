"""archive_cold_to_2mb_20260722.py — move cold, dependency-free folders from /Volumes/4 MB to /Volumes/2 MB.

WHY (user, 2026-07-22): 4 MB is at 99% (23 GB free). 2 MB is a keep-just-in-case archive for big outdated
files that have NO ties to the current versions or their dependencies.

WHAT IS MOVED — and the evidence each one is safe
  Every candidate was checked against the four things that actually reference files on 4 MB:
    * ABLATION_MASTER 'Drive Path'  -> points ONLY into pipeline_session_output (all 1610 batches)
    * copy.ai's 433 links           -> point ONLY into ablation_figures_20260625
    * the annotation stores          -> reference ONLY kt_tracking (312 rows of KT_TRACKING_MASTER)
    * the live HTTP servers          -> serve pipeline_session_output, _annotation_packages/annotation_pkgs_20260722,
                                        the five *_annot_pkgs_20260722, _reviews_and_reference/washout_event_review, and
                                        collagen_outline_pkg / lagging_measure_pkg / polar_paired_pkg /
                                        sisterless_platejoin_pkg  (those four are SERVED — never move them)
  Plus a code grep: none of the folders below appears in any .py/.sh/.jsx under ablation_figures_20260625,
  dataops, kt_outline, ablation-pipeline or movie_processing.
  Plus recency: everything below was last touched 11-27 days ago.

DELIBERATELY NOT MOVED
  ontarget_ablation_review (117 GB) and mad1_timelapse_review (65 GB) — no code references them, but the
  user opened them 2.5 days ago. Recent use outranks a dependency scan; they wait for an explicit go.
  ablation_timestrips_wide_20260710 and pipeline_correct — 7 code references each.
  Today's .ai backups — they are the rollback path for today's deck work.

SAFETY
  copy -> VERIFY (file count AND total bytes must match exactly) -> only then delete the source.
  Nothing is deleted that has not been byte-counted at the destination first. A manifest is written to
  BOTH drives so the archive is self-describing if 4 MB is ever not attached.
"""
import os, sys, shutil, subprocess, json, time

SRC = "/Volumes/4 MB"
DST = "/Volumes/2 MB/_4mb_archive_20260722"
APPLY = "--apply" in sys.argv

FOLDERS = [
    # ROUND 2, 2026-07-22 evening. Every entry passed all four tests:
    #   no file written OR read since 2026-07-15 · no master Drive Path points into it ·
    #   holds no sole-copy *_Cropped.tif or *_Monitoring.mp4 · nothing placed on copy.ai links into it.
    "ablation_timestrips_wide_20260710",   # 10.6 GB, last touched 07-14 — the finished 1,184-strip deliverable
    "pipeline_correct",                    # 8.9 GB,  last touched 06-23 — old pipeline output tree, 0 sole copies
    "mad1_zstack_render",                  # 1.0 GB,  last touched 07-06
    "analysis_hec1_640_3ch_20260704",      # 0.4 GB,  last touched 07-04
    "notable_timestrips_20260623",         # 0.4 GB,  last touched 06-25
]

# exhaustion_annotation_pkg still holds the ONLY copy of the movie for one batch that was never scored
# (no metaphase duration, no exclude flag). Recorded here so it is findable in the archive.
NOTES = {
    "exhaustion_annotation_pkg":
        "Annotation media only (136 mp4, 69 html) — creates NO figures. All 68 batches are in "
        "ABLATION_MASTER; 51 are in G4_exhaustion_violin and 16 are explicitly excluded with reasons. "
        "STILL UNSCORED: '20251021 no_ablations_nocodazole_1_xy14' — its movie is in here.",
    "rerender_3ch_20260703": "3-channel re-render index of 2077 acquisitions from the 2026-07-06 batching fix.",
    "reprocess_staging": "Staging leftovers from supervised reprocessing runs.",
}


def measure(path):
    """(file count, total bytes) — the verification currency."""
    n = b = 0
    for root, dirs, files in os.walk(path):
        for f in files:
            try:
                b += os.lstat(os.path.join(root, f)).st_size
                n += 1
            except OSError:
                pass
    return n, b


def free(path):
    st = os.statvfs(path)
    return st.f_bavail * st.f_frsize


LOCK = "/Volumes/4 MB/_logs/.archive_2mb.lock"


def acquire_lock():
    """Refuse to start if another copy is already running.

    Killing this script does NOT kill its rsync children — they get re-parented to init and keep writing.
    Restarting then put THREE rsyncs on the same source->dest pair at once, which halved throughput and
    made the destination untrustworthy (that copy was discarded). A lock plus a child-kill on exit stops
    that from happening again."""
    if os.path.exists(LOCK):
        try:
            pid = int(open(LOCK).read().strip())
            os.kill(pid, 0)
            print(f"ABORT: already running as pid {pid} (lock {LOCK})")
            return False
        except (ValueError, ProcessLookupError, PermissionError):
            pass                                  # stale lock
    open(LOCK, "w").write(str(os.getpid()))
    import atexit, signal, subprocess as _sp
    def cleanup(*a):
        _sp.run(["pkill", "-P", str(os.getpid()), "rsync"], capture_output=True)
        try: os.remove(LOCK)
        except OSError: pass
    atexit.register(cleanup)
    for sg in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sg, lambda *a: (cleanup(), sys.exit(1)))
    return True


def main():
    if APPLY and not acquire_lock():
        return
    os.makedirs(DST, exist_ok=True)
    plan = []
    for f in FOLDERS:
        p = os.path.join(SRC, f)
        if not os.path.isdir(p):
            print(f"  SKIP (missing): {f}")
            continue
        n, b = measure(p)
        plan.append((f, n, b))
    total = sum(b for _, _, b in plan)
    print(f"{len(plan)} folders, {sum(n for _,n,_ in plan):,} files, {total/1e9:.1f} GB")
    print(f"4 MB free now: {free(SRC)/1e9:.1f} GB   ->  after: {(free(SRC)+total)/1e9:.1f} GB")
    print(f"2 MB free now: {free('/Volumes/2 MB')/1e9:.1f} GB")
    if free("/Volumes/2 MB") < total * 1.05:
        print("ABORT: not enough room on 2 MB"); return
    if not APPLY:
        for f, n, b in plan:
            print(f"   {b/1e9:7.1f} GB  {n:6d} files  {f}")
        print("\nDRY RUN — nothing copied. Re-run with --apply.")
        return

    manifest = {"moved_on": time.strftime("%Y-%m-%d %H:%M"), "source": SRC, "dest": DST, "folders": []}
    for f, n, b in plan:
        s, dpath = os.path.join(SRC, f), os.path.join(DST, f)
        print(f"\n=== {f}  ({b/1e9:.1f} GB, {n} files)")
        t0 = time.time()
        r = subprocess.run(["rsync", "-a", "--no-perms", "--no-owner", "--no-group",
                            s + "/", dpath + "/"], capture_output=True, text=True)
        if r.returncode != 0:
            print(f"   rsync FAILED rc={r.returncode}: {r.stderr[:300]}"); continue
        n2, b2 = measure(dpath)
        ok = (n2 == n and b2 == b)
        print(f"   copied in {time.time()-t0:.0f}s -> dest {n2} files, {b2/1e9:.1f} GB   "
              f"{'VERIFIED' if ok else 'MISMATCH'}")
        if not ok:
            print("   NOT deleting the source — destination does not match."); continue
        shutil.rmtree(s)
        print(f"   source removed. 4 MB free: {free(SRC)/1e9:.1f} GB")
        manifest["folders"].append({"name": f, "files": n, "bytes": b,
                                    "note": NOTES.get(f, ""), "verified": True})
        for path in (os.path.join(DST, "ARCHIVE_MANIFEST.json"),
                     os.path.join(SRC, "ARCHIVED_TO_2MB_20260722.json")):
            json.dump(manifest, open(path, "w"), indent=1)
    print(f"\nDONE. moved {len(manifest['folders'])} folders. 4 MB free: {free(SRC)/1e9:.1f} GB")


if __name__ == "__main__":
    main()
