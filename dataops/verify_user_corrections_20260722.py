"""verify_user_corrections_20260722.py — re-prove that EVERY correction the user gave on 2026-07-22 is still
present in the masters. Run this after any bulk operation, restore, or rebuild.

    python3 "/Volumes/4 MB/dataops/verify_user_corrections_20260722.py"

Exit 0 = all 35 assertions hold. Exit 1 = something regressed; the failing line names the batch and field.
Source of the assertions: the user's message of 2026-07-22 (also transcribed in BATCH_CORRECTIONS_20260722.md).
"""
import sys, csv, io, re
sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import lib

A = "/Volumes/4 MB/annotations"


def rd(p):
    t = open(p, encoding="utf-8", errors="replace").read().replace("\r\n", "\n").replace("\r", "\n")
    return list(csv.DictReader(io.StringIO(t)))


CM = {(r["batch"].strip(), r["chr_num"]): r for r in rd(f"{A}/CHROMOSOME_MASTER.csv")}
mrows = list(csv.reader(open("/Volumes/4 MB/ABLATION_MASTER.csv")))
h = [c.strip() for c in mrows[1]]
M = {r[0].strip(): {h[i]: (r[i] if i < len(r) else "") for i in range(len(h))}
     for r in mrows[2:] if r and r[0].strip()}
KT = [r for r in rd(f"{A}/kt_points.csv") if r["label"] == "sisterless"]

ok = bad = 0


def C(label, cond, detail=""):
    global ok, bad
    ok += bool(cond); bad += (not cond)
    print(f"  [{'OK ' if cond else 'BAD'}] {label}" + ("" if cond else f"   <-- {detail}"))


def ch(b, cn):
    r = CM.get((b, cn))
    return (r["length_um"], r["behavior"], r["congression_hms"]) if r else ("MISSING", "", "")


def mv(b, c):
    return (M.get(b, {}).get(c, "") or "").strip()


C("20250925 triple_ablation_7 chr2 at_plate, no 0:00:00", ch("20250925 triple_ablation_7", "2") == ("5.591", "at_plate", ""), ch("20250925 triple_ablation_7", "2"))
C("20250929 four_ablation_23 chr1 congress 0:28:11", ch("20250929 four_ablation_23", "1") == ("3.911", "congressed", "0:28:11"), ch("20250929 four_ablation_23", "1"))
C("20250929 four_ablation_6 behavior still BLANK (user said reassess)", ch("20250929 four_ablation_6", "1")[1] == "", ch("20250929 four_ablation_6", "1"))
C("20251006 triple_ablation_15 chr1+chr2 zeros cleared", all(ch("20251006 triple_ablation_15", c)[2] == "" for c in "12"))
C("20251006 triple_ablation_18 anaphase 0:29:04", mv("20251006 triple_ablation_18", "Anaphase Onset (s)") == "0:29:04")
C("20251006 triple_ablation_18 chr1 noncongression", ch("20251006 triple_ablation_18", "1")[1] == "noncongression")
C("20251006 triple_ablation_21 all KT marks removed", not any(r["batch"].strip() == "20251006 triple_ablation_21" for r in KT))
C("20251029 triple_ablation_12 excluded from plots", lib.plot_excluded("20251029 triple_ablation_12"))
C("20251029 triple_ablation_23 meta 00:33:52", mv("20251029 triple_ablation_23", "Metaphase Start (s)") == "00:33:52")
C("20251029 triple_ablation_23 ana 01:24:25", mv("20251029 triple_ablation_23", "Anaphase Onset (s)") == "01:24:25")
for c, t in [("1", "1:03:04"), ("2", "0:51:48"), ("3", "0:44:08")]:
    C(f"20251029 triple_ablation_23 chr{c} {t}", ch("20251029 triple_ablation_23", c)[2] == t, ch("20251029 triple_ablation_23", c))
for c, t in [("1", "0:40:03"), ("3", "0:36:43")]:
    C(f"20251029 triple_ablation_68 chr{c} {t}", ch("20251029 triple_ablation_68", c)[2] == t, ch("20251029 triple_ablation_68", c))
C("20251029 triple_ablation_68 chr2 noncongression", ch("20251029 triple_ablation_68", "2")[1] == "noncongression")
C("20251029 triple_ablation_68 meta 0:31:03", mv("20251029 triple_ablation_68", "Metaphase Start (s)") == "0:31:03")
C("20251029 triple_ablation_68 polar yes", mv("20251029 triple_ablation_68", "Polar Chromosomes").lower() == "yes")
C("20251104 ablations_5 meta 00:26:50", mv("20251104 ablations_5", "Metaphase Start (s)") == "00:26:50")
C("20251104 ablations_5 chr1 noncongression", ch("20251104 ablations_5", "1")[1] == "noncongression")
C("20251104 ablations_5 chr2 at_plate", ch("20251104 ablations_5", "2")[1] == "at_plate")
B13 = "20260113 snigle_ablation_visualize chromosome with sisterless kinetochore_14"
C("20260113 ..._14 chr2 at_plate", ch(B13, "2")[1] == "at_plate")
C("20260113 ..._14 kt:2 points removed", not any(re.search(r"kt:2", r.get("notes") or "") for r in KT if r["batch"].strip() == B13))
C("20260416 single ablation_13 chr1 at_plate", ch("20260416 single ablation_13", "1")[1] == "at_plate")
C("20260417 ablation_14 meta 00:15:58", mv("20260417 ptk2 eyfp cdc20 ablation_14", "Metaphase Start (s)") == "00:15:58")
C("20260417 ablation_18 chr1 congress 0:17:24", ch("20260417 ptk2 eyfp cdc20 ablation_18", "1")[2] == "0:17:24")
C("20260417 ablation_18 chr2 at_plate", ch("20260417 ptk2 eyfp cdc20 ablation_18", "2")[1] == "at_plate")
C("20260417 ablation_18 chr3 noncongression", ch("20260417 ptk2 eyfp cdc20 ablation_18", "3")[1] == "noncongression")
C("20260417 ablation_18 meta 00:10:39", mv("20260417 ptk2 eyfp cdc20 ablation_18", "Metaphase Start (s)") == "00:10:39")
C("20250918 triple_ablation_15 chr1 congress 0:35:46", ch("20250918 triple_ablation_15", "1")[2] == "0:35:46")
C("20250925 triple_ablation_13 chr1 congressed 0:19:16", ch("20250925 triple_ablation_13", "1")[2] == "0:19:16")
C("20250925 triple_ablation_13 chr2 noncongression", ch("20250925 triple_ablation_13", "2")[1] == "noncongression")
C("20250925 triple_ablation_13 Lagging = No", mv("20250925 triple_ablation_13", "Lagging Chromosomes").lower() == "no")
C("20250923 collagen_25 chr2 noncongression", ch("20250923 triple_ablation_collagen_25", "2")[1] == "noncongression")
C("20250923 collagen_25 chr2 plate-join MEASUREMENT preserved",
  any(r["batch"].strip() == "20250923 triple_ablation_collagen_25" and r.get("chromosome_2_plate_join") == "0:13:21"
      for r in rd(f"{A}/SISTERLESS_PLATE_JOIN_TIMES.csv")))
C("20250923 collagen_31 meta 00:13:51", mv("20250923 triple_ablation_collagen_31", "Metaphase Start (s)") == "00:13:51")

print(f"\n==== {ok} OK / {bad} BAD ====")
sys.exit(1 if bad else 0)
