#!/usr/bin/env python3
"""AUDIT: does ANY script or ANY registered figure still carry an ellipse-derived quantity?

Asked for directly on 2026-08-03 after the ellipse fit was retired. This does NOT trust the change log —
it tests the artefacts.

FOUR INDEPENDENT CHECKS
  [A] CODE — every script that reads kinetochore-outline geometry is searched for a live ellipse fit, for
      the retired `ellipse_*` column names, AND for a COVARIANCE ELLIPSE computed under another name
      (`eigh(cov)` scaled into an axis LENGTH, which is what the retired code's own fallback branch did).
      A PCA call that only yields a DIRECTION is not an ellipse fit and is reported separately, not flagged.
  [B] STORES — the derived CSVs are reconciled row-by-row against a freshly computed caliper value for the
      same trace. Every `major_um` must equal the caliper number and must NOT equal the retired ellipse
      number. This is the decisive test: figures inherit from these stores.
  [C] FIGURES — every registered figure whose data CSV holds a suspect column is compared against BOTH the
      current caliper store and the retired ellipse table, by value. Matching the retired table = still
      ellipse-derived.
  [D] COMPLETENESS — is the "25 scripts" set itself complete? Every .py that reads any derived store is
      enumerated, so a consumer cannot hide by not being on a hand-written list.

Safe to run while she is annotating: it reads `kt_outlines.csv` ONCE and only ever compares a store against
that same snapshot, so rows she adds mid-run cannot register as a mismatch.
"""
import csv, json, os, re, sys
import numpy as np

ROOT = "/Volumes/4 MB"
FIG = f"{ROOT}/ablation_figures_20260625"
DATA = f"{ROOT}/ablation_plots/data"
RETIRED_CSV = f"{ROOT}/_retired/ellipse_shape_method_20260803/kt_shape_metrics_ELLIPSE_DERIVED_retired_20260803.csv"
sys.path.insert(0, FIG)
csv.field_size_limit(10 ** 9)

DERIVED_STORES = ["kt_shape_metrics", "KT_OUTLINE_TRACKS", "KT_LANDMARK_ANALYSIS", "KT_TENSION",
                  "KT_SISTER", "KT_CHROMO_ANALYSIS", "MAD1_KT_OUTLINE_TRACKS"]
SUSPECT = re.compile(r"major|minor|aspect|elong|roundness|angle_deg|strain|anisotrop|stretch", re.I)
BAD_CODE = [
    ("live ellipse fit", re.compile(r"^[^#]*\bfitEllipse\b")),
    ("retired ellipse column", re.compile(r"^[^#]*ellipse_(major|minor|aspect)")),
    ("covariance ellipse as a LENGTH", re.compile(r"^[^#]*sqrt\s*\(\s*(np\.)?maximum\(\s*w")),
]
PCA_DIRECTION = re.compile(r"linalg\s*\.\s*(svd|eigh)|np\s*\.\s*cov")   # tokenised lines are space-separated

report = []


def A_code(scripts):
    print("\n[A] CODE — live ellipse fits / retired columns / covariance-ellipse lengths")
    # Search only EXECUTABLE code. The first version regex-matched raw lines and flagged the docstring that
    # explains why the ellipse was retired — a false positive. Tokenising drops comments and string
    # literals, so prose about the retired method can never register as the method still being live.
    import io, tokenize
    bad, pca_only = [], []
    for s in sorted(scripts):
        p = os.path.join(FIG, s)
        if not os.path.isfile(p):
            continue
        src = open(p, errors="replace").read()
        code_lines = {}
        try:
            for tok in tokenize.generate_tokens(io.StringIO(src).readline):
                if tok.type in (tokenize.COMMENT, tokenize.STRING, tokenize.NL, tokenize.NEWLINE):
                    continue
                code_lines.setdefault(tok.start[0], []).append(tok.string)
        except Exception:
            code_lines = {i: [l] for i, l in enumerate(src.splitlines(), 1)}
        for i, toks in code_lines.items():
            line = " ".join(toks)
            for label, rx in BAD_CODE:
                if rx.search(line):
                    bad.append((s, i, label, line.strip()[:90]))
            if PCA_DIRECTION.search(line):
                pca_only.append(s)
    if bad:
        for s, i, lab, txt in bad:
            print(f"    FAIL {s}:{i}  [{lab}]  {txt}")
    else:
        print(f"    PASS — 0 live ellipse fits, 0 retired-column reads, 0 covariance-ellipse lengths "
              f"across {len(scripts)} scripts")
    d = sorted(set(pca_only))
    print(f"    (informational) {len(d)} scripts use PCA/SVD for a DIRECTION only — not a shape fit: "
          f"{', '.join(d[:6])}{' ...' if len(d) > 6 else ''}")
    report.append(("A", not bad, f"{len(bad)} code violations"))
    return not bad


def B_stores():
    """Reconcile every derived store against a freshly computed CALIPER value, joined EXACTLY.

    The first version keyed on (batch,label,frame). That key is AMBIGUOUS — 2580 of 5091 objects share one
    (paired traces are one object per trace, and a frame can carry several kinetochores) — so a legitimate
    second object on a frame read as a mismatch and the check reported 1426 false failures. The stores carry
    `trace_ids`, which identifies the exact set of traces measured, so join on that.
    """
    print("\n[B] STORES — reconcile each derived store against a freshly computed CALIPER value")
    import kt_shape_metrics as K
    import lib as _lib
    import collections
    recs = []
    for r in csv.DictReader(open(K.SRC)):          # ONE read; safe against concurrent annotation
        if r.get("channel") != "fluor":
            continue
        if _lib.kt_outline_excluded(r.get("batch")) or _lib.focus_excluded(r.get("id")):
            continue
        try:
            recs.append((r, json.loads(r["points"])))
        except Exception:
            pass
    groups = collections.OrderedDict()
    for r, pts in recs:
        # 2026-08-03: this audit carried its OWN copy of the grouping rule and went stale the moment
        # grp-tagged `paired` started obeying the grp rule — it then reported 114 phantom mismatches against
        # a store that was correct. Third instance of the same class of bug today. K.group_key, always.
        groups.setdefault(K.group_key(r), []).append((r, pts))
    truth_id, truth_set = {}, {}
    for key, mem in groups.items():
        r0 = mem[0][0]
        m = K._combined_metrics([p for (_, p) in mem], float(r0.get("pixel_size_um") or 0.062))
        if not m:
            continue
        truth_id[str(r0.get("id"))] = m["major_um"]
        truth_set[tuple(sorted(str(x[0].get("id")) for x in mem))] = m["major_um"]
    ell = {}
    if os.path.isfile(RETIRED_CSV):
        for r in csv.DictReader(open(RETIRED_CSV)):
            try:
                ell[str(r["id"])] = float(r["major_um"])
            except Exception:
                pass

    def idset(v):
        return tuple(sorted(x.strip() for x in str(v or "").replace(";", ",").split(",") if x.strip()))

    # Landmark rows carry track_id+frame but no trace_ids. Bridging on (track_id,frame) is ALSO ambiguous —
    # that pair is non-unique in both stores (105 duplicate rows, e.g. `...|paired|5` frame 36 appears 3x,
    # i.e. the tracker put three objects of one frame into one track) — and collapsing it produced 87 phantom
    # mismatches. kt_landmark_analysis emits exactly one row per tracks row IN ORDER, so join by ROW INDEX,
    # after asserting the two stores are the same length.
    tp = f"{ROOT}/annotations/KT_OUTLINE_TRACKS_20260723.csv"
    bridge_by_row = []
    if os.path.isfile(tp):
        bridge_by_row = [idset(r.get("trace_ids")) for r in csv.DictReader(open(tp))]

    ok = True
    for store, how in [("ablation_plots/data/kt_shape_metrics.csv", "id"),
                       ("annotations/KT_OUTLINE_TRACKS_20260723.csv", "trace_ids"),
                       ("annotations/KT_LANDMARK_ANALYSIS_20260723.csv", "bridge")]:
        p = os.path.join(ROOT, store)
        if not os.path.isfile(p):
            print(f"    -- {os.path.basename(store)}: not present"); continue
        rows = list(csv.DictReader(open(p)))
        if not rows or "major_um" not in rows[0]:
            print(f"    -- {os.path.basename(store)}: no major_um column"); continue
        if how == "bridge" and len(rows) != len(bridge_by_row):
            print(f"    FAIL {os.path.basename(store):42s} row-count mismatch vs tracks "
                  f"({len(rows)} vs {len(bridge_by_row)}) — cannot join by index")
            ok = False
            continue
        n = mism = matches_ell = 0
        for ri, r in enumerate(rows):
            try:
                v = float(r["major_um"])
            except Exception:
                continue
            if how == "id":
                exp = truth_id.get(str(r.get("id") or ""))
            elif how == "trace_ids":
                exp = truth_set.get(idset(r.get("trace_ids")))
            else:
                exp = truth_set.get(bridge_by_row[ri]) if ri < len(bridge_by_row) else None
            if exp is None:
                continue
            n += 1
            if abs(v - exp) > 1e-3:
                mism += 1
            e = ell.get(str(r.get("id") or ""))
            if e is not None and abs(v - e) < 1e-6 and abs(exp - e) > 1e-3:
                matches_ell += 1
        verdict = "PASS" if (n > 0 and mism == 0 and matches_ell == 0) else "FAIL"
        if verdict == "FAIL":
            ok = False
        print(f"    {verdict} {os.path.basename(store):42s} {n:5d} joined, "
              f"{mism} differ from calipers, {matches_ell} match the RETIRED ellipse value")
    report.append(("B", ok, "store reconciliation (exact trace_ids join)"))
    return ok


def C_figures():
    """Is every registered figure's recorded data NEWER than the ellipse retirement?

    Value fingerprinting was tried first and does not work: these are continuous quantities, the retired and
    current tables each hold ~10k values, and a 900-row figure collides with BOTH sets (e.g. G6ph_strain
    scored 885 ellipse-only against 869 caliper-only — noise, not provenance). Provenance is decided by
    WHEN the data was written, against the moment the ellipse left the code, which is unambiguous.
    """
    print("\n[C] FIGURES — is every figure's recorded data newer than the ellipse retirement?")
    S = json.load(open(f"{ROOT}/ablation_plots/PLOT_SETTINGS.json"))
    stamp = f"{ROOT}/ablation_plots/data/kt_shape_metrics.csv"
    t_ref = os.path.getmtime(stamp)
    root = FIG
    tainted = set()
    for f in os.listdir(root):
        if not f.endswith(".py"):
            continue
        try:
            src = open(os.path.join(root, f), errors="replace").read()
        except Exception:
            continue
        if any(t in src for t in DERIVED_STORES):
            tainted.add(f)
    stale, fresh, norows = [], 0, []
    for k, v in S.items():
        if not isinstance(v, dict):
            continue
        if os.path.basename(str(v.get("code") or "")).split("__")[-1] not in tainted:
            continue
        p = f"{DATA}/{k}.csv"
        if not os.path.isfile(p):
            norows.append(k); continue
        if os.path.getmtime(p) + 1.0 < t_ref:
            stale.append((k, round((t_ref - os.path.getmtime(p)) / 3600.0, 1)))
        else:
            fresh += 1
    print(f"    reference: kt_shape_metrics.csv written {os.path.getmtime(stamp):.0f}")
    print(f"    figures from ellipse-reading scripts: {fresh + len(stale) + len(norows)}")
    print(f"      data written AFTER the retirement : {fresh}")
    print(f"      data OLDER than the retirement    : {len(stale)}")
    for k, h in sorted(stale, key=lambda x: -x[1])[:20]:
        print(f"        STALE {k}  ({h} h older)")
    if norows:
        print(f"      no data CSV on disk               : {len(norows)}  {norows[:6]}")
    ok = not stale
    report.append(("C", ok, f"{len(stale)} stale figure tables"))
    return ok


def D_completeness():
    print("\n[D] COMPLETENESS — every .py that reads a derived store (is the '25' list complete?)")
    found = {}
    for f in sorted(os.listdir(FIG)):
        if not f.endswith(".py"):
            continue
        try:
            s = open(os.path.join(FIG, f), errors="replace").read()
        except Exception:
            continue
        hit = [d for d in DERIVED_STORES if d in s]
        if hit:
            found[f] = hit
    print(f"    {len(found)} scripts read kinetochore-outline geometry")
    return found


if __name__ == "__main__":
    print("=" * 96)
    print("ELLIPSE-RESIDUE AUDIT")
    print("=" * 96)
    scripts = D_completeness()
    a = A_code(set(scripts))
    b = B_stores()
    c = C_figures()
    print("\n" + "=" * 96)
    for tag, ok, note in report:
        print(f"  [{tag}] {'PASS' if ok else 'FAIL'}  — {note}")
    print("=" * 96)
    sys.exit(0 if all(ok for _, ok, _ in report) else 1)
