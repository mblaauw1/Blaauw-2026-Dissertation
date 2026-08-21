"""verify_consistency.py — enforce TYPE-LEVEL feedback rules across EVERY per-plot data CSV, so an exclusion
applied to some-but-not-all plots FAILS THE BOARD instead of relying on a human to spot it.

Built 2026-07-08 after the double-chromosome leak into pole_time + plate_join (group3_build got the guard, its
sibling scripts didn't). This is the durable fix for the recurring "applied to a subset, not all instances"
failure. Reads the per-plot CSVs in ablation_plots/data/ and checks each global invariant against ALL of them.

Exit code: non-zero if any HARD check fails (checks A + B + D). Check C is informational (report only).
Check D keeps the IMG_ONLY + sisterless/traced filter so genuinely image-only figures (timestrips, contact
sheets, stat grids, MIPs, IF montages, lagging examples) are not flagged; every OTHER placed plot must have a CSV.
"""
import sys, os, csv, glob, json
sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import lib

ROOT = "/Volumes/4 MB/ablation_figures_20260625"
DATA = "/Volumes/4 MB/ablation_plots/data"

def csv_batches(p):
    """The set of batch names appearing as DATA ROWS in a plot CSV (via the 'batch' column). Row-level, not
    substring — so a batch name used only as a caption/label elsewhere is not falsely flagged."""
    try:
        r = list(csv.reader(open(p, errors="ignore")))
    except Exception:
        return set()
    if not r:
        return set()
    h = r[0]
    bi = next((i for i, c in enumerate(h) if c.strip().lower() == "batch"), None)
    if bi is None:
        bi = next((i for i, c in enumerate(h) if "batch" in c.lower()), None)
    if bi is None:
        return set()
    return set(row[bi].strip() for row in r[1:] if len(row) > bi and row[bi].strip())

DBL = set(lib.double_chromosome_batches())
REV = set(getattr(lib, "REVIEW_EXCLUDE", set()))
CSVS = sorted(glob.glob(f"{DATA}/*.csv"))

# Double-chromosome cells ARE valid data in the per-ablation-event / per-KT MECHANISM plots (ablation works the
# same regardless of chromosome topology). They must NOT appear in PHENOTYPE/COHORT plots (which categorize by
# sisterless number — there a double-chromosome cell is miscounted). This allowlist names the mechanism plots
# where their presence is intentional; double-chromosome in ANY other plot is a leak and fails the board.
DBL_ALLOWED_SUBSTR = ("ablation_intensity", "cdc20_intensity", "frap", "prepost")
def dbl_allowed(plot_id):
    return any(s in plot_id for s in DBL_ALLOWED_SUBSTR)

fails = []
print("=== verify_consistency: type-level rules across all %d per-plot CSVs ===" % len(CSVS))

# ---- CHECK A (HARD): REVIEW_EXCLUDE outliers (e.g. the 80-min cell) must be absent from EVERY plot CSV ----
a = [(os.path.basename(p), sorted(REV & csv_batches(p))) for p in CSVS if REV & csv_batches(p)]
print(f"[A] REVIEW_EXCLUDE global outliers absent from every plot CSV: {'PASS' if not a else 'FAIL'}")
for f, l in a:
    print(f"      LEAK {f}: {l}")
if a:
    fails.append("A: REVIEW_EXCLUDE outlier leaked into a plot")

# ---- CHECK B (HARD): double-chromosome cells only in the allowlisted mechanism plots ----
b = []
for p in CSVS:
    pid = os.path.basename(p)[:-4]
    if dbl_allowed(pid):
        continue
    leak = DBL & csv_batches(p)
    if leak:
        b.append((pid, sorted(leak)))
print(f"[B] double-chromosome absent from all non-mechanism (phenotype/cohort) plots: {'PASS' if not b else 'FAIL'}")
for pid, l in b:
    print(f"      LEAK {pid}: {l}")
if b:
    fails.append("B: double-chromosome leaked into a phenotype/cohort plot")

# ---- CHECK C (REPORT): mad1/IF (fixed) batches should not mix into live-cell plots ----
c = []
for p in CSVS:
    pid = os.path.basename(p)[:-4]
    if any(k in pid.lower() for k in ("mad1", "if_", "if4", "g5")):
        continue
    leak = sorted(x for x in csv_batches(p) if lib.is_mad1(x))
    if leak:
        c.append((pid, leak[:4]))
print(f"[C] mad1/IF batches only in mad1/IF plots (live vs fixed separation): {'clean' if not c else str(len(c))+' to review'}")
for pid, l in c:
    print(f"      review {pid}: {l}")

# ---- CHECK D (HARD): every placed non-image plot in the reordered PDF has a direct data CSV ----
d = []
mani = f"{ROOT}/_ai_relink/reordered_manifest.json"
if os.path.isfile(mani):
    IMG_ONLY = ("timestrip", "timestrips2/", "frap_timestrips/", "_aligned", "contactsheet",
                "statgrid", "_mips", "montage", "g5_if", "zstack",
                "lagging_examples", "if_kt", "item2_if", "_examples", "sanitycheck")
    for img in json.load(open(mani)):
        pid = os.path.basename(img)[:-4]
        low = img.lower()
        if any(k in low for k in IMG_ONLY):
            continue
        if any(k in pid for k in ("1-sisterless", "2-sisterless", "3-sisterless", "off-target",
                                  "double-chromosome", "unmanipulated", "traced")):
            continue
        if not os.path.isfile(f"{DATA}/{pid}.csv"):
            d.append(pid)
print(f"[D] every placed data-plot has a direct CSV: {'yes — 0 without a CSV' if not d else str(len(d))+' without a CSV'}")
for pid in d[:20]:
    print(f"      no CSV: {pid}")
if d:
    fails.append("D: placed data-plot without a direct CSV")

print("\n" + ("=== ALL CONSISTENCY CHECKS PASS ===" if not fails
             else "*** CONSISTENCY FAILURES: " + "; ".join(fails) + " ***"))
sys.exit(1 if fails else 0)
