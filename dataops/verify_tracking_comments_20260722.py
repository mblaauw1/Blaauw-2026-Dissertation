"""verify_tracking_comments_20260722.py — check the master against EVERY line of
`~/Documents/comments from tracking.rtf`, not just the subset asserted earlier.

Each entry: (batch, what the note says, a callable returning (ok, detail)).
Where the note asks for something only she can do (remeasure, re-review), we check that it is RECORDED
as pending rather than silently dropped.
"""
import csv, sys, os

ROOT = "/Volumes/4 MB"
sys.path.insert(0, f"{ROOT}/dataops")
import dataops

CH = f"{ROOT}/annotations/CHROMOSOME_MASTER.csv"
REVIEW = f"{ROOT}/BATCHES_TO_REVIEW_AFTER_FIX_20260717.csv"

chromo = {}
for r in csv.DictReader(open(CH, encoding="utf-8", errors="replace")):
    chromo[(r["batch"].strip(), r["chr_num"].strip())] = r

_m = dataops.read(f"{ROOT}/ABLATION_MASTER.csv")
_hdr = [c.strip() for c in _m[1]]
master = {}
for r in _m[2:]:
    if r and r[0].strip():
        master[r[0].strip()] = {c: (r[i].strip() if i < len(r) else "") for i, c in enumerate(_hdr)}

review_txt = open(REVIEW, encoding="utf-8", errors="replace").read() if os.path.isfile(REVIEW) else ""


def beh(b, n):
    r = chromo.get((b, str(n)))
    return (r or {}).get("behavior", "").strip()


def cong(b, n):
    r = chromo.get((b, str(n)))
    return (r or {}).get("congression_hms", "").strip()


def length(b, n):
    r = chromo.get((b, str(n)))
    return (r or {}).get("length_um", "").strip()


def mval(b, c):
    return (master.get(b, {}) or {}).get(c, "").strip()


def hm(s):
    """compare H:MM:SS loosely (0:19:16 == 00:19:16)"""
    p = [int(x) for x in str(s).split(":")] if s else []
    while len(p) < 3: p.insert(0, 0)
    return tuple(p) if p else None


CHECKS = []
def chk(batch, note, fn):
    # bind `batch` NOW; a lambda closing over the module-level B sees only its final value
    CHECKS.append((batch, note, fn))


B = "20250909 triple_ablation_collagen_3"
chk(B, "chr1 2.142um congressed 22:55", lambda B=B: (beh(B,1)=="congressed" and hm(cong(B,1))==hm("0:22:55"), f"{length(B,1)} {beh(B,1)} {cong(B,1)}"))
chk(B, "chr3 11.173 noncongression", lambda B=B: (beh(B,3)=="noncongression", f"{length(B,3)} {beh(B,3)}"))

B = "20250909 triple_ablation_collagen_9"
chk(B, "chr2 congression 27:20 len 3.682", lambda B=B: (hm(cong(B,2))==hm("0:27:20"), f"{length(B,2)} {beh(B,2)} {cong(B,2)}"))
chk(B, "chr1 6.623 at pole until anaphase", lambda B=B: (beh(B,1)=="noncongression", f"{length(B,1)} {beh(B,1)}"))

B = "20250910 triple_ablation_collagen_14"
chk(B, "chr1+chr2 polar until anaphase", lambda B=B: (beh(B,1)=="noncongression" and beh(B,2)=="noncongression", f"c1={beh(B,1)} c2={beh(B,2)}"))
chk(B, "chr3 congress 15:00", lambda B=B: (hm(cong(B,3))==hm("0:15:00"), f"{beh(B,3)} {cong(B,3)}"))
chk(B, "remeasure recorded as pending", lambda B=B: (B.split()[-1] in review_txt or B in review_txt, "in review list" if B in review_txt else "NOT in review list"))

B = "20250918 triple_ablation_15"
chk(B, "chr1 congression 35:46", lambda B=B: (hm(cong(B,1))==hm("0:35:46"), cong(B,1)))

B = "20250923 triple_ablation_collagen_25"
chk(B, "chr2 noncongressing", lambda B=B: (beh(B,2)=="noncongression", beh(B,2)))

B = "20250923 triple_ablation_collagen_31"
chk(B, "metaphase 00:13:51 (her LATER correction supersedes 00:35:13)",
    lambda B=B: (hm(mval(B,"Metaphase Start (s)"))==hm("00:13:51"), mval(B,"Metaphase Start (s)")))

B = "20250925 triple_ablation_13"
chk(B, "chr1 congressed 0:19:16", lambda B=B: (beh(B,1)=="congressed" and hm(cong(B,1))==hm("0:19:16"), f"{beh(B,1)} {cong(B,1)}"))
chk(B, "chr2 noncongressed", lambda B=B: (beh(B,2)=="noncongression", beh(B,2)))
chk(B, "Lagging = No", lambda B=B: (mval(B,"Lagging Chromosomes").lower() in ("no","n","0",""), mval(B,"Lagging Chromosomes")))

B = "20250925 triple_ablation_7"
chk(B, "chr2 zero-sentinel cleared (no bogus 0:00:00)", lambda B=B: (cong(B,2)!="0:00:00", f"{beh(B,2)} {cong(B,2)!r}"))
chk(B, "3-merotelic re-review recorded", lambda B=B: (B in review_txt, "in review list" if B in review_txt else "NOT in review list"))

B = "20250929 four_ablation_23"
chk(B, "chr1 congress 0:28:11 (note filed under _7 but belongs here)", lambda B=B: (hm(cong(B,1))==hm("0:28:11"), f"{beh(B,1)} {cong(B,1)}"))

B = "20250929 four_ablation_6"
chk(B, "2-vs-4 sisterless reassessment recorded", lambda B=B: (B in review_txt, "in review list" if B in review_txt else "NOT in review list"))

B = "20251006 triple_ablation_15"
chk(B, "zero-sentinel congression times cleared", lambda B=B: (cong(B,1)!="0:00:00" and cong(B,2)!="0:00:00", f"c1={cong(B,1)!r} c2={cong(B,2)!r}"))

B = "20251006 triple_ablation_18"
chk(B, "anaphase 0:29:04", lambda B=B: (hm(mval(B,"Anaphase Onset (s)"))==hm("0:29:04"), mval(B,"Anaphase Onset (s)")))
chk(B, "chr1 at_plate -> noncongression", lambda B=B: (beh(B,1)=="noncongression", beh(B,1)))

B = "20251006 triple_ablation_21"
chk(B, "KT markings removed", lambda B=B: _no_kt(B))

B = "20251029 triple_ablation_12"
chk(B, "excluded from plots, kept as paired-polar example", lambda B=B: _excluded(B))

B = "20251029 triple_ablation_23"
chk(B, "metaphase 33:52 (later note wins over 25:20)", lambda B=B: (hm(mval(B,"Metaphase Start (s)"))==hm("0:33:52"), mval(B,"Metaphase Start (s)")))
chk(B, "anaphase 01:24:25", lambda B=B: (hm(mval(B,"Anaphase Onset (s)"))==hm("01:24:25"), mval(B,"Anaphase Onset (s)")))
chk(B, "chr1 congression 1:03:04", lambda B=B: (hm(cong(B,1))==hm("1:03:04"), cong(B,1)))
chk(B, "chr2 congression 51:48", lambda B=B: (hm(cong(B,2))==hm("0:51:48"), cong(B,2)))
chk(B, "chr3 congression 44:08", lambda B=B: (hm(cong(B,3))==hm("0:44:08"), cong(B,3)))

B = "20251029 triple_ablation_68"
chk(B, "chr2 -> polar until anaphase", lambda B=B: (beh(B,2)=="noncongression", f"{beh(B,2)} {cong(B,2)}"))
chk(B, "metaphase 0:31:03", lambda B=B: (hm(mval(B,"Metaphase Start (s)"))==hm("0:31:03"), mval(B,"Metaphase Start (s)")))
chk(B, "Polar = yes", lambda B=B: (mval(B,"Polar Chromosomes").lower().startswith("y"), mval(B,"Polar Chromosomes")))

B = "20251104 ablations_5"
chk(B, "metaphase 26:50", lambda B=B: (hm(mval(B,"Metaphase Start (s)"))==hm("0:26:50"), mval(B,"Metaphase Start (s)")))
chk(B, "chr1 -> polar until anaphase", lambda B=B: (beh(B,1)=="noncongression", f"{beh(B,1)} {cong(B,1)}"))
chk(B, "chr2 -> at plate from metaphase onset", lambda B=B: (beh(B,2)=="at_plate", f"{beh(B,2)} {cong(B,2)}"))

B = "20260107 two_sisterless_kinetochores_3"
chk(B, "remeasure recorded (chr1==chr3 length)", lambda B=B: (B in review_txt, "in review list" if B in review_txt else "NOT in review list"))

B = "20260108 two_sisterless_kinetochores_14"
chk(B, "remeasure recorded", lambda B=B: (B in review_txt, "in review list" if B in review_txt else "NOT in review list"))

B = "20260113 snigle_ablation_visualize chromosome with sisterless kinetochore_14"
chk(B, "chr2 -> at plate since metaphase onset", lambda B=B: (beh(B,2)=="at_plate", f"{beh(B,2)} {cong(B,2)}"))
chk(B, "accidental kt2 points removed", lambda B=B: _no_kt2(B))

B = "20260416 single ablation_13"
chk(B, "chr1 -> at plate since metaphase onset", lambda B=B: (beh(B,1)=="at_plate", f"{beh(B,1)} {cong(B,1)}"))

B = "20260417 ptk2 eyfp cdc20 ablation_14"
chk(B, "metaphase 00:15:58", lambda B=B: (hm(mval(B,"Metaphase Start (s)"))==hm("00:15:58"), mval(B,"Metaphase Start (s)")))

B = "20260417 ptk2 eyfp cdc20 ablation_18"
chk(B, "chr1 congresses at 17:24 (later note)", lambda B=B: (hm(cong(B,1))==hm("0:17:24"), cong(B,1)))
chk(B, "chr2 at_plate", lambda B=B: (beh(B,2)=="at_plate", beh(B,2)))
chk(B, "chr3 noncongression", lambda B=B: (beh(B,3)=="noncongression", beh(B,3)))
chk(B, "metaphase 10:39", lambda B=B: (hm(mval(B,"Metaphase Start (s)"))==hm("0:10:39"), mval(B,"Metaphase Start (s)")))


def _kt_rows(b, kt=None):
    n = 0
    for r in csv.DictReader(open(f"{ROOT}/annotations/kt_points.csv", encoding="utf-8", errors="replace")):
        if r["batch"].strip() != b: continue
        if kt and f"kt:{kt}" not in (r.get("notes") or ""): continue
        n += 1
    return n


def _no_kt(b):
    n = _kt_rows(b)
    return (n == 0, f"{n} kt_points rows remain")


def _no_kt2(b):
    n = _kt_rows(b, kt=2)
    return (n == 0, f"{n} kt:2 rows remain")


def _excluded(b):
    txt = open(f"{ROOT}/annotations/MANUAL_PLOT_EXCLUSIONS.csv", encoding="utf-8", errors="replace").read() \
        if os.path.isfile(f"{ROOT}/annotations/MANUAL_PLOT_EXCLUSIONS.csv") else ""
    return (b in txt, "in MANUAL_PLOT_EXCLUSIONS" if b in txt else "NOT in exclusions")


if __name__ == "__main__":
    ok = bad = 0
    for b, note, fn in CHECKS:
        try:
            good, detail = fn()
        except Exception as e:
            good, detail = False, f"{type(e).__name__}: {e}"
        print(f"  [{'OK ' if good else 'BAD'}] {b} — {note}   ({detail})")
        ok += bool(good); bad += (not good)
    print(f"\n==== {ok} OK / {bad} BAD  (of {len(CHECKS)} instructions in comments from tracking.rtf) ====")
