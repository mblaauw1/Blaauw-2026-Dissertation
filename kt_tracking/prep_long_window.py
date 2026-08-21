"""prep_long_window.py — rebuild the benchmark KTmon stacks with a LONGER post-anaphase window.

WHY: 473 manual KT marks fall outside the tracked window entirely, because `kt_track_prep.build_stack`
stops at anaphase + 3 min. No amount of detector tuning can recover those — the frames are not in the
stack. This rebuilds the benchmark stacks with a bigger tail so the gain can be measured.

Writes to `kt_tracking/stacks_long/` — the live `stacks/` dir is NOT touched.
NB the original module still points at the removed /Volumes/5 MB, so the paths are overridden here.

Usage: python3 prep_long_window.py [post_anaphase_seconds]   (default 900 = 15 min)
"""
import os, sys, csv, importlib.util

BASE = "/Volumes/4 MB/kt_tracking"
POST = float(sys.argv[1]) if len(sys.argv) > 1 else 900.0

spec = importlib.util.spec_from_file_location(
    "ktp", os.path.expanduser("~/ablation-pipeline/kt_tracking/kt_track_prep.py"))
ktp = importlib.util.module_from_spec(spec)
sys.argv = ["kt_track_prep.py"]          # stop its main() from parsing our args
spec.loader.exec_module(ktp)

# the module was written when output lived on /Volumes/5 MB
ktp.OUT_BASE = BASE
ktp.STACKS = os.path.join(BASE, "stacks_long")
ktp.POST_ANAPHASE_S = POST
ktp.RENDER_ROOTS = ["/Volumes/4 MB/pipeline_session_output"]
os.makedirs(ktp.STACKS, exist_ok=True)


def anaphase_s(batch):
    rows = list(csv.reader(open("/Volumes/4 MB/ABLATION_MASTER.csv", encoding="utf-8", errors="replace")))
    hdr = [c.strip() for c in rows[1]]
    ai = hdr.index("Anaphase Onset (s)")
    for r in rows[2:]:
        if r and r[0].strip() == batch and len(r) > ai:
            s = r[ai].strip()
            if not s:
                return None
            p = [float(x) for x in s.split(":")]
            while len(p) < 3:
                p.insert(0, 0)
            return p[0] * 3600 + p[1] * 60 + p[2]
    return None


LIST = os.environ.get("KT_BATCH_LIST", f"{BASE}/bench_batches.txt")
batches = [l.strip() for l in open(LIST) if l.strip()]
print(f"rebuilding {len(batches)} stacks with anaphase+{POST/60:.0f}min -> {ktp.STACKS}", flush=True)
ok = 0
for i, b in enumerate(batches, 1):
    a = anaphase_s(b)
    if a is None:
        print(f"[{i}] SKIP {b} — no anaphase time", flush=True); continue
    try:
        path, msg = ktp.build_stack(b, a)
    except Exception as e:
        print(f"[{i}] ERR {b}: {type(e).__name__}: {e}", flush=True); continue
    if path:
        ok += 1; print(f"[{i}/{len(batches)}] OK {b}: {msg}", flush=True)
    else:
        print(f"[{i}/{len(batches)}] FAIL {b}: {msg}", flush=True)
print(f"DONE — {ok}/{len(batches)} stacks rebuilt", flush=True)
