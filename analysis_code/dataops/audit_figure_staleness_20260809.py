#!/usr/bin/env python3
"""Which figures were built from data that has since changed? Uses recorded hashes, not a snapshot diff.

WHY THIS REPLACES THE EARLIER DELTA. `rerun_ktoutline_figures_20260809.py` reported "5 figures changed"
by snapshotting figure data CSVs before and after its own run. That snapshot was taken AFTER the KT chain
had already run earlier the same day, so it measured only the tail of the day's changes and understated
them. Worse, it can never detect a figure that SHOULD have been rebuilt but wasn't.

`lib.record_plot` stores, per figure, the source files it read plus their md5 AT BUILD TIME
(`source.hashes_at_build`). Comparing those against the files on disk right now answers the real question
-- is this figure consistent with the data as it stands? -- with no dependence on when anything was run.

Reports three classes:
  CURRENT  every recorded source still hashes the same -> the figure matches the data
  STALE    at least one source has changed since the figure was built -> needs a rebuild
  UNKNOWN  no hashes recorded (older figures) -> cannot be judged either way
"""
import csv, hashlib, json, os, collections

PS = "/Volumes/4 MB/ablation_plots/PLOT_SETTINGS.json"
OUT = "/Volumes/4 MB/ablation_plots/FIGURE_STALENESS_20260809.csv"
ps = json.load(open(PS))

_h = {}
def md5(p):
    if p in _h:
        return _h[p]
    try:
        m = hashlib.md5()
        with open(p, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                m.update(chunk)
        _h[p] = m.hexdigest()
    except Exception:
        _h[p] = None
    return _h[p]


rows, cls = [], collections.Counter()
changed_src = collections.Counter()
for pid, ent in sorted(ps.items()):
    if not isinstance(ent, dict):
        continue
    src = ent.get("source") or {}
    if not isinstance(src, dict):
        cls["UNKNOWN"] += 1
        rows.append([pid, "UNKNOWN", "", ""]); continue
    hashes = src.get("hashes_at_build") or {}
    if not hashes:
        cls["UNKNOWN"] += 1
        rows.append([pid, "UNKNOWN", "", ""]); continue
    stale = []
    for path, h in hashes.items():
        now = md5(path)
        if now is None:
            stale.append(os.path.basename(path) + " (missing)")
        elif now != h:
            stale.append(os.path.basename(path))
            changed_src[os.path.basename(path)] += 1
    if stale:
        cls["STALE"] += 1
        rows.append([pid, "STALE", ";".join(sorted(set(stale))), len(hashes)])
    else:
        cls["CURRENT"] += 1
        rows.append([pid, "CURRENT", "", len(hashes)])

with open(OUT, "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["plot_id", "state", "changed_sources", "n_sources_tracked"])
    w.writerows(rows)

print(f"figures audited: {len(rows)}")
for k in ("CURRENT", "STALE", "UNKNOWN"):
    print(f"   {k:8s} {cls[k]}")
print("\nsources that changed since figures were built (figure count):")
for s, n in changed_src.most_common(15):
    print(f"   {s:46s} {n}")
stale = [r for r in rows if r[1] == "STALE"]
if stale:
    print(f"\nSTALE figures ({len(stale)}) — first 25:")
    for r in stale[:25]:
        print(f"   {r[0][:56]:56s} <- {r[2][:60]}")
print(f"\nwrote {OUT}")
