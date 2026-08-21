#!/usr/bin/env python3
"""Keep `_ai_relink/pdf_pub/` in step with `_ai_relink/pdf/`.

WHY THIS EXISTS
---------------
`pdf_pub/` is NOT a copy of `pdf/`. It is a SECOND RENDERING of the same figures, produced by
`PUB=1`: figure titles stripped, any in-axes text over 70 characters blanked, every axis label /
tick / legend / table cell pushed through `canon_labels.py`, and mm:ss converted to minutes on a
`(min)` axis. It exists because of her 2026-08-17 item 7 — the "extra words" she wanted gone live
INSIDE the linked PDFs, so no Illustrator pass could remove them.

Only `META_FIGURES_20260814_PUBLICATION.ai` and `META_FIGURES_20260813_supplemental_PUBLICATION.ai`
link it. That is exactly why it goes stale: a normal builder re-run refreshes `pdf/`, the working
decks pick the change up, and the publication copies silently keep yesterday's figure. It bit twice
in two days (2026-08-18: G4_lagging_bar, then 14 more including every item-19 zoom sheet).

USE
---
    python3 dataops/sync_pub.py --check     # report only; exit 1 if anything is stale
    python3 dataops/sync_pub.py             # re-run the owning builders under PUB=1

Run it after ANY figure rebuild. `--check` is cheap and is what `checks.py` calls.
"""
import argparse, collections, io, json, os, re, subprocess, sys, time

R   = "/Volumes/4 MB"
FIG = R + "/ablation_figures_20260625"
PDF = FIG + "/_ai_relink/pdf"
PUB = FIG + "/_ai_relink/pdf_pub"
# the two decks that LINK pdf_pub, and the live decks they mirror
MIRRORED = {"0814": "META_FIGURES_20260814", "0813supp": "META_FIGURES_20260813_supplemental"}
# The two PUBLICATION decks are audited TOO. They have drifted from their live twins (30 figures sit
# only on the publication copies, 2026-08-18), and those were invisible to an audit scoped to the
# live decks alone -- exactly the silent-staleness this module exists to stop.
PUB_DECKS = ("pub0814", "pub0813")

def placed_on(tag):
    p = f"{R}/_claude_tmp/geom9_{tag}.tsv"
    if not os.path.exists(p): return set()
    out = set()
    for ln in io.open(p, encoding="utf-8", errors="replace").read().replace("\r", "\n").split("\n"):
        f = ln.split("\t")
        if len(f) > 11 and f[0] == "PlacedItem" and f[5]: out.add(f[5])
    return out

def audit():
    """-> (stale, missing) figure-name lists, for figures on the two mirrored decks."""
    names = set()
    for tag in tuple(MIRRORED) + PUB_DECKS: names |= placed_on(tag)
    stale, missing = [], []
    for n in sorted(names):
        a, b = f"{PDF}/{n}.pdf", f"{PUB}/{n}.pdf"
        if not os.path.exists(a): continue
        if not os.path.exists(b): missing.append(n)
        elif os.path.getmtime(b) < os.path.getmtime(a) - 2: stale.append(n)
    return stale, missing, len(names)

def builder_of(name, ps):
    """PLOT_SETTINGS records an ARCHIVED COPY of each generating script under ablation_plots/code/.
    Resolve back to the live builder, which is what has to be re-run."""
    code = ((ps.get(name) or {}).get("code") or "")
    if not code: return None
    base = os.path.basename(code)
    # archived copies are named "<plot_id>__<builder>.py"
    if "__" in base: base = base.split("__", 1)[1]
    for cand in (f"{FIG}/{base}", f"{FIG}/figures/{base}"):
        if os.path.exists(cand): return cand
    return None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="report only, exit 1 if stale")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    stale, missing, total = audit()
    bad = stale + missing
    print(f"[pub] {total} figures placed on the mirrored + publication decks")
    print(f"[pub] stale publication twins : {len(stale)}")
    print(f"[pub] missing publication twins: {len(missing)}")
    for n in stale[:40]:   print("      stale  ", n)
    for n in missing[:40]: print("      missing", n)
    if not bad:
        print("[pub] publication library is in step with the working library.")
        return 0
    if a.check:
        print("\n[pub] run `python3 dataops/sync_pub.py` to regenerate.")
        return 1

    ps = json.load(io.open(R + "/ablation_plots/PLOT_SETTINGS.json", encoding="utf-8", errors="replace"))
    by = collections.defaultdict(list)
    orphan = []
    for n in bad:
        b = builder_of(n, ps)
        (by[b].append(n) if b else orphan.append(n))
    print(f"\n[pub] {len(by)} builders to re-run under PUB=1")
    for b, names in by.items():
        print(f"   {os.path.basename(b):48s} -> {len(names)} figure(s)")
    if orphan:
        print(f"\n[pub] ⚠ {len(orphan)} figure(s) have no resolvable builder — regenerate by hand:")
        for n in orphan: print("      ", n)
    if a.dry_run: return 0

    env = dict(os.environ); env["PUB"] = "1"
    # group_timestrips is a monolith: TRACED_ONLY keeps it to the one figure the decks link
    for b, names in by.items():
        e = dict(env)
        if os.path.basename(b) == "group_timestrips.py": e["TRACED_ONLY"] = "1"
        t0 = time.time()
        r = subprocess.run([sys.executable, "-u", b], cwd=FIG, env=e,
                           capture_output=True, text=True, timeout=3600)
        print(f"   {os.path.basename(b):48s} rc={r.returncode}  {time.time()-t0:.0f}s")
        if r.returncode != 0:
            print("      " + (r.stderr or "").strip()[-400:])

    stale, missing, _ = audit()
    left = stale + missing
    print(f"\n[pub] after regeneration: {len(left)} still out of step")
    for n in left: print("      ", n)
    return 0 if not left else 1

if __name__ == "__main__":
    sys.exit(main())
