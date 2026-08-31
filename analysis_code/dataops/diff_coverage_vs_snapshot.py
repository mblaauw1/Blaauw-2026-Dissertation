#!/usr/bin/env python3
"""Per-batch COVERAGE diff of CSV outputs against a snapshot (handoff-7 §3.7).

§3.7: "Always diff row counts AND per-batch coverage against the previous version; a success
message verifies the write, not the content." A sha256 diff only says a file CHANGED - it cannot
tell a legitimate re-measurement from a run that silently wrote 1,801 rows instead of 36,956, or
that dropped a whole clip role. That is the exact failure §3.7 was written about.

For every CSV in the snapshot manifest that still exists, this reports:
  * row count before -> after
  * distinct batch count before -> after
  * batches LOST (present before, absent now)   <- the dangerous case
  * batches GAINED
  * the largest per-batch row-count drops

  python3 diff_coverage_vs_snapshot.py <version> [path_substring ...]
"""
import csv, os, sys, collections

ROOT = "/Volumes/4 MB"
STORE = os.path.join(ROOT, "_retired/frame_offbyone_20260728")
csv.field_size_limit(10 ** 9)

BATCH_KEYS = ("batch", "Batch Name", "batch_name", "cell", "Batch")


def load(path):
    try:
        with open(path, newline="") as f:
            rows = list(csv.DictReader(f))
    except Exception as e:
        return None, None, str(e)
    if not rows:
        return 0, collections.Counter(), None
    key = next((k for k in BATCH_KEYS if k in rows[0]), None)
    if key is None:
        return len(rows), None, None
    return len(rows), collections.Counter((r.get(key) or "").strip() for r in rows), None


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    version = sys.argv[1]
    filters = sys.argv[2:]
    man = os.path.join(STORE, "versions", version, "MANIFEST.csv")
    if not os.path.exists(man):
        sys.exit("no such snapshot: " + man)

    rows = [r for r in csv.DictReader(open(man)) if r["rel_path"].lower().endswith(".csv")]
    if filters:
        rows = [r for r in rows if any(f in r["rel_path"] for f in filters)]

    flagged, checked, skipped = [], 0, 0
    for r in rows:
        rel = r["rel_path"]
        live = os.path.join(ROOT, rel)
        sha = r["sha256"]
        blob = os.path.join(STORE, "blobs", sha[:2], sha)
        if not os.path.exists(live) or not os.path.exists(blob):
            skipped += 1
            continue
        n_old, c_old, e1 = load(blob)
        n_new, c_new, e2 = load(live)
        if e1 or e2 or n_old is None or n_new is None:
            skipped += 1
            continue
        checked += 1
        lost, gained, drops = [], [], []
        if c_old is not None and c_new is not None:
            lost = sorted(set(c_old) - set(c_new))
            gained = sorted(set(c_new) - set(c_old))
            for b in sorted(set(c_old) & set(c_new)):
                if c_new[b] < c_old[b]:
                    drops.append((c_old[b] - c_new[b], b))
            drops.sort(reverse=True)
        if n_new != n_old or lost or drops:
            flagged.append((rel, n_old, n_new, c_old, c_new, lost, gained, drops))

    print("CSVs compared: %d   (skipped, missing on one side: %d)" % (checked, skipped))
    if not flagged:
        print("\nno row-count or per-batch coverage change in any CSV.")
        return
    for rel, n_old, n_new, c_old, c_new, lost, gained, drops in flagged:
        nb_old = len(c_old) if c_old is not None else "-"
        nb_new = len(c_new) if c_new is not None else "-"
        print("\n%s" % rel)
        print("   rows %s -> %s   batches %s -> %s" % (n_old, n_new, nb_old, nb_new))
        if lost:
            print("   !! BATCHES LOST (%d): %s" % (len(lost), lost[:8]))
        if gained:
            print("   batches gained (%d): %s" % (len(gained), gained[:8]))
        if drops:
            print("   largest per-batch row drops: %s" % [(b, -d) for d, b in drops[:6]])


if __name__ == "__main__":
    main()
