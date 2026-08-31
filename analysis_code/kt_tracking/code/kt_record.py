"""Record a completed tracking run into the master + KT_TRACKING_MASTER (both on 4 MB).
Usage: python3 kt_record.py <manifest_label>   e.g. kt_record.py all_bottomup
Reads /Volumes/4 MB/kt_tracking/stacks/manifest_<label>.json, computes n_tracks/n_spots/median
from each batch's results, appends/updates KT_TRACKING_MASTER, and writes kt_tracking_id + kt_n_tracks
to the master. Batches with 0 tracks are recorded but reported (usually dim / untrackable)."""
import csv, json, os, statistics, shutil, sys
OUT = "/Volumes/4 MB/kt_tracking"; RES = os.path.join(OUT, "results")
MASTER = "/Volumes/4 MB/ABLATION_MASTER.csv"
KTM = "/Volumes/4 MB/annotations/KT_TRACKING_MASTER.csv"
label = sys.argv[1] if len(sys.argv) > 1 else "all_bottomup"
manifest = json.load(open(os.path.join(OUT, "stacks", f"manifest_{label}.json")))
def stats(base):
    tp = os.path.join(RES, base + ".tracks_timed.csv"); sp = os.path.join(RES, base + ".spots_timed.csv")
    ns = sum(1 for _ in open(sp)) - 1 if os.path.exists(sp) else 0
    nt = 0; spd = []
    if os.path.exists(tp):
        rr = list(csv.DictReader(open(tp))); nt = len(rr)
        for row in rr:
            try:
                v = float(row.get("median_speed_um_per_min", "") or "nan")
                if v == v: spd.append(v)
            except Exception: pass
    return nt, ns, (round(statistics.median(spd), 2) if spd else "")
shutil.copy2(MASTER, MASTER + ".bak_pre_kt_record")
shutil.copy2(KTM, KTM + ".bak_pre_kt_record")
ktm = list(csv.reader(open(KTM))); byb = {r[0]: i for i, r in enumerate(ktm) if i > 0}
mupd = {}; zero = []
for e in manifest:
    batch = e["batch"]; base = os.path.basename(e["tif"]).replace("_KTmon.tif", "")
    if not os.path.exists(os.path.join(RES, base + ".trackmate.xml")):
        continue                       # tracking didn't produce output for this one
    nt, ns, md = stats(base)
    if nt == 0: zero.append(batch)
    row = [batch, base, nt, ns, md, base + ".spots_timed.csv", base + ".tracks_timed.csv",
           base + "_KToverlay.mp4", base + ".trackmate.xml", RES]
    if batch in byb: ktm[byb[batch]] = row
    else: ktm.append(row); byb[batch] = len(ktm) - 1
    mupd[batch] = (base, nt)
with open(KTM, "w", newline="") as f: csv.writer(f).writerows(ktm)
rows = list(csv.reader(open(MASTER))); h = rows[1]
bi = h.index("Batch Name"); kti = h.index("kt_tracking_id"); knt = h.index("kt_n_tracks")
mu = 0
for r in rows[2:]:
    if len(r) > knt and r[bi].strip() in mupd:
        kid, nt = mupd[r[bi].strip()]; r[kti] = kid; r[knt] = str(nt); mu += 1
with open(MASTER, "w", newline="") as f: csv.writer(f).writerows(rows)
print(f"recorded {len(mupd)} batches | master +{mu} | KT_TRACKING_MASTER now {len(ktm)-1} rows")
if zero:
    print(f"  {len(zero)} had 0 tracks (likely dim/untrackable — review): {zero[:8]}")
