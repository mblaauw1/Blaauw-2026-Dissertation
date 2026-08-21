"""checks.py — independent cross-checks over every annotation/master store on /Volumes/4 MB.

Design principles
  * MANY SMALL INDEPENDENT CHECKS. A single "verify" function hides failures; 30 narrow checks do not.
  * EVERY CHECK IS A CROSS-CHECK where possible: a value is compared against a DIFFERENT source that was
    produced by a different route (traces vs pairing, points vs stored length, derived columns vs recompute,
    frames.json vs annotation frame index, snapshots vs live).
  * SEVERITY: ERROR = data is wrong or lost. WARN = suspicious / needs a human. INFO = coverage stats.
  * NO SIDE EFFECTS. checks never write.

Usage
    python3 "/Volumes/4 MB/dataops/checks.py"            # run all, human output
    python3 "/Volumes/4 MB/dataops/checks.py" --json     # machine-readable
    from checks import run_all; rep = run_all()          # for the transaction guard
"""
import csv, io, os, re, json, glob, math, collections, sys

ROOT = "/Volumes/4 MB"
A = f"{ROOT}/annotations"
MASTER = f"{ROOT}/ABLATION_MASTER.csv"
REG = []            # (id, title, fn)
BEHAVIORS = {"", "congressed", "noncongression", "at_plate"}


def check(cid, title):
    def deco(fn):
        REG.append((cid, title, fn)); return fn
    return deco


def rd(p):
    if not os.path.isfile(p): return []
    t = open(p, encoding="utf-8", errors="replace").read().replace("\r\n", "\n").replace("\r", "\n")
    return list(csv.DictReader(io.StringIO(t)))


def master_rows():
    rows = list(csv.reader(open(MASTER)))
    h = [c.strip() for c in rows[1]]
    return [{h[i]: (r[i] if i < len(r) else "") for i in range(len(h))} for r in rows[2:] if r and r[0].strip()], h


def num(v):
    try: return float(str(v).strip().replace(",", ""))
    except Exception: return None


def hms(v):
    """H:MM:SS -> seconds. Times are elapsed from FIRST ABLATION, so a LEADING MINUS means the event
    happened BEFORE the ablation and the whole value is negative. Splitting on ':' loses that sign when the
    hour field is '-0' — that bug produced 4 false 'out-of-order event time' errors on 2026-07-22."""
    v = (v or "").strip()
    if not v: return None
    neg = v.startswith("-")
    if neg: v = v[1:]
    if ":" in v:
        try:
            p = [float(x) for x in v.split(":")]
            while len(p) < 3: p.insert(0, 0)
            s = p[0] * 3600 + p[1] * 60 + p[2]
        except Exception: return None
    else:
        s = num(v)
        if s is None: return None
    return -s if neg else s


_FR = None
def frames_json():
    """batch -> frames.json dict (roi, fps, n frames). Cached."""
    global _FR
    if _FR is None:
        _FR = {}
        for fj in glob.glob(f"{ROOT}/pipeline_session_output/*/*/*_frames.json"):
            b = os.path.basename(os.path.dirname(fj))
            try: _FR[b] = json.load(open(fj))
            except Exception: pass
    return _FR


# ---------------------------------------------------------------- STRUCTURE
@check("S1", "every store has its required columns")
def s1():
    need = {"kt_points.csv": {"id","batch","frame","x","y","label","notes"},
            "meta_plates.csv": {"id","batch","frame","points","label"},
            "cell_outlines.csv": {"id","batch","frame","points","label"},
            "chromo_measure_lines.csv": {"id","batch","chr_num","frame","points","length_um","pixel_size_um"},
            "CHROMO_LENGTH_BEHAVIOR_PAIRING.csv": {"id","batch","chr1_length_um","chr1_movement"},
            "SISTERLESS_PLATE_JOIN_TIMES.csv": {"id","batch","chromosome_1_plate_join"},
            "CHROMOSOME_MASTER.csv": {"batch","chr_num","length_um","behavior","congression_time_s"}}
    out = []
    for f, cols in need.items():
        r = rd(f"{A}/{f}")
        if not r: out.append(("ERROR", f"{f}: missing or empty")); continue
        gap = cols - set(r[0])
        if gap: out.append(("ERROR", f"{f}: missing columns {sorted(gap)}"))
    return out


@check("S2", "ids are unique within each store")
def s2():
    out = []
    for f in ["kt_points.csv","meta_plates.csv","cell_outlines.csv","chromo_measure_lines.csv",
              "chromo_lines.csv","lagging_lengths.csv","CHROMO_LENGTH_BEHAVIOR_PAIRING.csv",
              "SISTERLESS_PLATE_JOIN_TIMES.csv","PREABL_CHROMOSOME_ASSIGNMENT.csv"]:
        r = rd(f"{A}/{f}")
        if not r or "id" not in r[0]: continue
        d = [k for k, v in collections.Counter(x["id"] for x in r).items() if v > 1]
        if d: out.append(("ERROR", f"{f}: {len(d)} duplicate ids (e.g. {d[:5]})"))
    return out


@check("S3", "no blank batch names; no wholly-empty rows")
def s3():
    out = []
    for f in ["kt_points.csv","meta_plates.csv","cell_outlines.csv","chromo_measure_lines.csv"]:
        r = rd(f"{A}/{f}")
        n = sum(1 for x in r if not (x.get("batch") or "").strip())
        if n: out.append(("ERROR", f"{f}: {n} rows with no batch"))
    return out


# ---------------------------------------------------------------- REFERENTIAL
@check("R1", "every annotated batch exists in the master")
def r1():
    m = {r["Batch Name"] for r in master_rows()[0]}
    out = []
    for f in ["kt_points.csv","meta_plates.csv","cell_outlines.csv","chromo_measure_lines.csv",
              "CHROMOSOME_MASTER.csv","CHROMO_LENGTH_BEHAVIOR_PAIRING.csv","SISTERLESS_PLATE_JOIN_TIMES.csv"]:
        bad = sorted({(r.get("batch") or "").strip() for r in rd(f"{A}/{f}")} - m - {""})
        if bad: out.append(("ERROR", f"{f}: {len(bad)} batches not in master (e.g. {bad[:3]})"))
    return out


@check("R2", "master mirror-id columns resolve to live rows")
def r2():
    rows, h = master_rows(); out = []
    for col, f in [("kt_point_ids","kt_points.csv"),("meta_plate_ids","meta_plates.csv"),
                   ("cell_outline_ids","cell_outlines.csv"),("chromo_line_ids","chromo_lines.csv"),
                   ("lagging_ids","lagging_lengths.csv"),("chromo_pairing_ids","CHROMO_LENGTH_BEHAVIOR_PAIRING.csv"),
                   ("sisterless_plate_join_ids","SISTERLESS_PLATE_JOIN_TIMES.csv"),
                   ("chromosome_annotation_ids","CHROMOSOME_MASTER.csv"),
                   ("preabl_chromosome_ids","PREABL_CHROMOSOME_ASSIGNMENT.csv")]:
        if col not in h: continue
        live = {r.get("id") for r in rd(f"{A}/{f}")}
        stale = 0
        for r in rows:
            for x in [s.strip() for s in (r.get(col) or "").split(",") if s.strip()]:
                if x not in live: stale += 1
        if stale: out.append(("ERROR", f"{col}: {stale} ids reference rows that no longer exist"))
    return out


@check("R3", "every annotation row is referenced by its batch's mirror-id column")
def r3():
    rows, h = master_rows()
    idx = {r["Batch Name"]: r for r in rows}; out = []
    for col, f in [("kt_point_ids","kt_points.csv"),("meta_plate_ids","meta_plates.csv"),
                   ("cell_outline_ids","cell_outlines.csv")]:
        if col not in h: continue
        miss = 0
        byb = collections.defaultdict(set)
        for r in rd(f"{A}/{f}"): byb[(r.get("batch") or "").strip()].add(r.get("id"))
        for b, ids in byb.items():
            listed = {s.strip() for s in (idx.get(b, {}).get(col) or "").split(",") if s.strip()}
            miss += len(ids - listed)
        if miss: out.append(("WARN", f"{col}: {miss} rows exist but are not listed in the master mirror"))
    return out


# ---------------------------------------------------------------- GEOMETRY / PHYSICS
@check("G1", "annotation coordinates fall inside the batch's crop")
def g1():
    fr = frames_json(); out = []; bad = collections.Counter()
    for f, xs in [("kt_points.csv", None), ("meta_plates.csv", "points"), ("cell_outlines.csv", "points"),
                  ("chromo_measure_lines.csv", "points")]:
        for r in rd(f"{A}/{f}"):
            j = fr.get((r.get("batch") or "").strip())
            if not j or "roi" not in j: continue
            W, H = j["roi"].get("w"), j["roi"].get("h")
            pts = []
            if xs and (r.get("points") or "").strip():
                try: pts = json.loads(r["points"])
                except Exception: continue
            elif num(r.get("x")) is not None:
                pts = [[num(r["x"]), num(r["y"])]]
            for p in pts:
                if p[0] < -2 or p[1] < -2 or p[0] > W + 2 or p[1] > H + 2:
                    bad[f] += 1; break
    for f, n in bad.items(): out.append(("ERROR", f"{f}: {n} rows have coordinates outside the {W}x{H} crop"))
    return out


@check("G2", "annotation frame index is within the batch's frame count")
def g2():
    """KNOWN, ACCEPTED stale frames live in dataops/ACCEPTED_STALE_FRAMES.csv, mirroring how L1 handles
    accepted losses, and for the same underlying cause: annotations drawn on a render that has since been
    re-cropped or re-rendered SHORTER. Those cannot be repaired by index arithmetic -- the old and new renders
    do not share a time base, so re-anchoring by nearest time lands the mark on the wrong image -- and each is
    recorded per (batch, file) with the measurement that establishes it. They stay visible as INFO rather than
    vanishing; anything NOT in that registry is a new, unexplained regression and still fires as a WARN."""
    fr = frames_json(); out = []; bad = collections.defaultdict(collections.Counter)
    for f in ["kt_points.csv","meta_plates.csv","cell_outlines.csv","chromo_measure_lines.csv"]:
        for r in rd(f"{A}/{f}"):
            b = (r.get("batch") or "").strip()
            j = fr.get(b)
            if not j: continue
            n = len(j.get("frames", []))
            fi = num(r.get("frame"))
            if n and fi is not None and (fi < 0 or fi >= n): bad[f][b] += 1

    acc = {}
    ap = f"{os.path.dirname(os.path.abspath(__file__))}/ACCEPTED_STALE_FRAMES.csv"
    if os.path.exists(ap):
        for r in rd(ap):
            try: acc[((r.get("file") or "").strip(), (r.get("batch") or "").strip())] = int(r.get("count") or 0)
            except ValueError: pass

    live, known = collections.Counter(), 0
    for f, per in bad.items():
        for b, n in per.items():
            a = acc.get((f, b), 0)
            known += min(a, n)
            if n > a: live[f] += n - a
    for f, n in live.items():
        out.append(("WARN", f"{f}: {n} rows reference a frame beyond the movie length"))
    if known:
        out.append(("INFO", f"{known} stale-frame rows are known and accepted "
                            f"({len(acc)} entries in ACCEPTED_STALE_FRAMES.csv) — annotations drawn on renders "
                            f"that were later re-cropped; not repairable by index arithmetic"))
    return out


@check("G3", "stored trace length equals the length recomputed from its points")
def g3():
    out = []; bad = []
    for r in rd(f"{A}/chromo_measure_lines.csv"):
        L = num(r.get("length_um")); ps = num(r.get("pixel_size_um"))
        try: P = json.loads(r["points"])
        except Exception: continue
        if L is None or ps is None or len(P) < 2: continue
        calc = sum(math.dist(P[i], P[i+1]) for i in range(len(P)-1)) * ps
        if abs(calc - L) > max(0.02, 0.02 * L):
            bad.append(f"{r['batch']} chr{r.get('chr_num')}: stored {L} vs recomputed {round(calc,3)}")
    if bad: out.append(("ERROR", f"chromo_measure_lines: {len(bad)} length mismatches; e.g. {bad[:3]}"))
    return out


@check("G4", "meta-plate lines are usable by the plot readers (>=2 points)")
def g4():
    # 2026-07-22: freehand (>2-point) plate lines are NOT a defect. Every consumer reads the mark as a
    # POLYLINE and accepts len(pts)>=2 — group4_tracking_dist.plate_axis (SVD/PCA), group4_movement._plate_axis,
    # custom_sisterless_movement.dist_to_plate, metaplate_rotation_by_sisterless. The remaining freehand lines
    # deviate from their own chord by a median 0.65 um (max 2.0 um), so flattening them to 2 points would
    # DESTROY measured curvature. Reported as INFO, not a WARN. Only <2-point marks are real breakage.
    bad, free = 0, 0
    for r in rd(f"{A}/meta_plates.csv"):
        try: P = json.loads(r.get("points") or "[]")
        except Exception: continue
        if len(P) == 0: continue
        if len(P) < 2: bad += 1
        elif len(P) > 2: free += 1
    out = []
    if bad: out.append(("ERROR", f"meta_plates: {bad} lines have fewer than 2 points — unusable"))
    if free: out.append(("INFO", f"meta_plates: {free} freehand (>2-point) lines — supported by every reader, not converted on purpose"))
    return out


@check("G5", "pixel size and chromosome length are physically plausible")
def g5():
    out = []
    ps = [num(r.get("pixel_size_um")) for r in rd(f"{A}/chromo_measure_lines.csv")]
    weird = [p for p in ps if p is not None and not (0.02 <= p <= 0.30)]
    if weird: out.append(("ERROR", f"chromo_measure_lines: implausible pixel sizes {sorted(set(weird))[:5]}"))
    bad = [(r["batch"], r["chr_num"], r["length_um"]) for r in rd(f"{A}/CHROMOSOME_MASTER.csv")
           if num(r.get("length_um")) is not None and not (0.5 <= num(r["length_um"]) <= 25)]
    if bad: out.append(("WARN", f"CHROMO_COMPLETE: {len(bad)} lengths outside 0.5-25um {bad[:3]}"))
    return out


# ---------------------------------------------------------------- TEMPORAL
@check("T1", "NEB < metaphase < anaphase < cytokinesis")
def t1():
    """Split by Exclude (2026-07-27): an Exclude=Yes cell is already pulled from every plot and cohort, so a
    bad time on it cannot reach a figure — it is a data-hygiene note, not a live error. Keeping the two in one
    ERROR line meant the check never went quiet and so never signalled anything new."""
    out = []; bad = []; excl = []
    for r in master_rows()[0]:
        n, m, a, c = (hms(r.get(k)) for k in ("NEB Time (s)","Metaphase Start (s)","Anaphase Onset (s)","Cytokinesis Onset (s)"))
        seq = [(x, lbl) for x, lbl in ((n,"NEB"),(m,"meta"),(a,"ana"),(c,"cyto")) if x is not None]
        for i in range(len(seq)-1):
            if seq[i][0] > seq[i+1][0]:
                msg = f"{r['Batch Name']}: {seq[i][1]}={seq[i][0]:g}s > {seq[i+1][1]}={seq[i+1][0]:g}s"
                (excl if (r.get("Exclude") or "").strip().lower() in ("yes","true","1") else bad).append(msg)
                break
    if bad: out.append(("ERROR", f"{len(bad)} LIVE cells with out-of-order event times: {bad}"))
    # 2026-08-17: demoted WARN -> INFO after trying to repair all three and establishing that they cannot be.
    # Each is Exclude=Yes with a curated reason ("dramatically out of focus at about min 33 of monitoring",
    # "very unhealthy"), so none reaches a figure. All three show the same signature -- an anaphase that would
    # order correctly with one more hour on it -- but that is a GUESS at her curated times, and it cannot be
    # confirmed: neither cell has a frames.json, and the only surviving timing evidence
    # (_reviews_and_reference/raw_metadata_harvest/sidecars/*_MMStack_Pos0_metadata.txt) covers a SINGLE acquisition -- 22 frames /31s
    # for Zm_ablation_2um_9, 178 frames /265s for two_sisterless_kinetochores_5 -- not the multi-sweep session
    # the master times span (that cell's Notes read "SAMESWEEP: 00:32:13"). Rewriting her event times on
    # inference alone would be worse than leaving them visible, so they stay printed, at their true severity.
    if excl: out.append(("INFO", f"{len(excl)} Exclude=Yes cells with out-of-order event times (not in any plot, not repairable): {excl}"))
    return out


@check("T2", "master duration columns equal their recomputation")
def t2():
    out = []; bad = []
    for r in master_rows()[0]:
        m, a, d = hms(r.get("Metaphase Start (s)")), hms(r.get("Anaphase Onset (s)")), num(r.get("Meta Duration (s)"))
        if None in (m, a, d): continue
        if abs((a - m) - d) > 1.5:
            bad.append(f"{r['Batch Name']}: stored {d} vs {round(a-m,1)}")
    if bad: out.append(("ERROR", f"Meta Duration (s) stale for {len(bad)} cells; e.g. {bad[:3]}"))
    return out


@check("T3", "congression time lies between metaphase onset and anaphase")
def t3():
    """Split by Exclude (2026-08-17), for the same reason T1 was split on 2026-07-27: an Exclude=Yes cell is
    already pulled from every plot and cohort, so a bad time on it cannot reach a figure.

    The whole standing backlog here was ONE excluded cell, 20250409 ptk_yfpcdc20_1 (chr2/chr3, congression
    1349s vs anaphase 660s), and its congression is not the wrong half: her plate-join annotation records
    chromosome_2/3_plate_join = 0:22:29 at frame 163, while the master's own Notes on that row read
    "technically, metaphase had already started at 0:05:00. consider excluding" -- i.e. the master's event
    times are the truncated ones, which is also why she excluded the cell. Nothing here is repairable by
    editing the congression, and the cell reaches no figure, so it is an INFO note, not a WARN."""
    m = {r["Batch Name"]: r for r in master_rows()[0]}; bad = []; excl = []
    for r in rd(f"{A}/CHROMOSOME_MASTER.csv"):
        t = num(r.get("congression_time_s"))
        row = m.get(r["batch"].strip())
        if t is None or not row: continue
        a = hms(row.get("Anaphase Onset (s)"))
        if a is not None and t > a + 1:
            msg = f"{r['batch']} chr{r['chr_num']}: congress {t}s > anaphase {a}s"
            (excl if (row.get("Exclude") or "").strip().lower() in ("yes","true","1") else bad).append(msg)
    out = []
    if bad: out.append(("WARN", f"{len(bad)} congression times after anaphase; e.g. {bad[:3]}"))
    if excl: out.append(("INFO", f"{len(excl)} congression times after anaphase on Exclude=Yes cells (not in any plot): {excl[:3]}"))
    return out


# ---------------------------------------------------------------- CROSS-FILE
@check("X1", "behavior vocabulary is closed")
def x1():
    bad = collections.Counter()
    for f in ["CHROMOSOME_MASTER.csv"]:
        for r in rd(f"{A}/{f}"):
            if (r.get("behavior") or "") not in BEHAVIORS: bad[(f, r.get("behavior"))] += 1
    return [("ERROR", f"unknown behavior values: {dict(bad)}")] if bad else []


@check("X2", "a congression time implies behavior == congressed")
def x2():
    bad = [f"{r['batch']} chr{r['chr_num']} ({r['behavior']})" for r in rd(f"{A}/CHROMOSOME_MASTER.csv")
           if num(r.get("congression_time_s")) is not None and r.get("behavior") != "congressed"]
    return [("ERROR", f"{len(bad)} rows have a congression time but are not 'congressed': {bad[:5]}")] if bad else []


@check("X3", "no second per-chromosome table has reappeared")
def x3():
    # 2026-07-22: the CAM-vs-CHROMO_COMPLETE comparison is retired — there is now exactly ONE
    # per-chromosome table (CHROMOSOME_MASTER.csv). This check guards that decision instead:
    # a resurrected rival table would silently re-split the data again.
    rivals = [f for f in ("CHROMOSOME_ANNOTATIONS_MASTER.csv", "CHROMO_COMPLETE_20260720.csv")
              if os.path.isfile(f"{A}/{f}")]
    return [("ERROR", f"a rival per-chromosome table exists again: {rivals} — one table only")] if rivals else []


@check("X4", "PAIRING lengths equal the drawn traces")
def x4():
    tr = collections.defaultdict(dict)
    for r in rd(f"{A}/chromo_measure_lines.csv"):
        L = num(r.get("length_um"))
        if L is not None: tr[r["batch"].strip()][str(r.get("chr_num")).strip()] = round(L, 3)
    bad = []
    for r in rd(f"{A}/CHROMO_LENGTH_BEHAVIOR_PAIRING.csv"):
        b = r["batch"].strip()
        for cn in "123":
            v = num(r.get(f"chr{cn}_length_um")); t = tr.get(b, {}).get(cn)
            if v is not None and t is not None and abs(v - t) > 0.002:
                bad.append(f"{b} chr{cn}: pairing {v} vs trace {t}")
    return [("ERROR", f"{len(bad)} pairing/trace length disagreements: {bad[:3]}")] if bad else []


@check("X5", "plate-join sentinel '0' never carries a congression time")
def x5():
    pj = {r["batch"].strip(): r for r in rd(f"{A}/SISTERLESS_PLATE_JOIN_TIMES.csv")}
    bad = []
    for r in rd(f"{A}/CHROMOSOME_MASTER.csv"):
        v = (pj.get(r["batch"].strip(), {}).get(f"chromosome_{r['chr_num']}_plate_join") or "").strip()
        if v in ("0", "0:00:00") and num(r.get("congression_time_s")) == 0:
            bad.append(f"{r['batch']} chr{r['chr_num']}")
    return [("WARN", f"{len(bad)} rows still show the 0-sentinel as a 0:00:00 congression: {bad[:5]}")] if bad else []


@check("X6", "kt track indices do not exceed the cell's sisterless count")
def x6():
    m = {r["Batch Name"]: r for r in master_rows()[0]}
    bad = []
    for r in rd(f"{A}/kt_points.csv"):
        if r.get("label") != "sisterless": continue
        mm = re.search(r"kt:(\d+)", r.get("notes") or "")
        if not mm: continue
        n = (m.get(r["batch"].strip(), {}).get("# Sisterless KTs") or "").strip()
        if n.isdigit() and int(mm.group(1)) > int(n): bad.append(f"{r['batch']} kt:{mm.group(1)} > {n}")
    return [("ERROR", f"{len(set(bad))} batches have a kt index above their sisterless count: {sorted(set(bad))[:3]}")] if bad else []


@check("X7", "plate-join n_sisterless matches the master")
def x7():
    m = {r["Batch Name"]: (r.get("# Sisterless KTs") or "").strip() for r in master_rows()[0]}
    bad = [f"{r['batch']}: pj={r.get('n_sisterless')} master={m.get(r['batch'].strip())}"
           for r in rd(f"{A}/SISTERLESS_PLATE_JOIN_TIMES.csv")
           if (r.get("n_sisterless") or "").strip() and m.get(r["batch"].strip())
           and (r.get("n_sisterless") or "").strip() != m.get(r["batch"].strip())]
    return [("WARN", f"{len(bad)} plate-join rows disagree with master sisterless count: {bad[:3]}")] if bad else []


@check("X8", "no chromosome number exceeds the cell's sisterless count")
def x8():
    m = {r["Batch Name"]: (r.get("# Sisterless KTs") or "").strip() for r in master_rows()[0]}
    bad = [f"{r['batch']} chr{r['chr_num']} (n={m.get(r['batch'].strip())})"
           for r in rd(f"{A}/CHROMOSOME_MASTER.csv")
           if (m.get(r["batch"].strip()) or "").isdigit() and int(r["chr_num"]) > int(m[r["batch"].strip()])]
    return [("WARN", f"{len(bad)} chromosome rows above the sisterless count: {bad[:3]}")] if bad else []


# ---------------------------------------------------------------- DUPLICATES / COVERAGE
@check("D1", "identical lengths within one cell (a trace counted twice)")
def d1():
    by = collections.defaultdict(list); out = []
    for r in rd(f"{A}/CHROMOSOME_MASTER.csv"):
        L = num(r.get("length_um"))
        if L is not None: by[r["batch"].strip()].append((r["chr_num"], round(L, 3)))
    for b, v in by.items():
        dup = [x for x, n in collections.Counter(l for _, l in v).items() if n > 1]
        if dup: out.append(("WARN", f"{b}: identical lengths {dup} on chr {[c for c,l in v if l in dup]}"))
    return out


@check("K1", "kt_outlines store is internally consistent")
def k1():
    """The KT-outline slides store (annotations/kt_outlines.csv, added 2026-07-22). Every trace must have a
    parseable polygon, live in a batch the master knows, and be reachable from the master's kt_outline_ids."""
    rows = rd(f"{A}/kt_outlines.csv")
    if not rows: return []
    out = []
    ids = [r.get("id") for r in rows]
    if len(set(ids)) != len(ids):
        out.append(("ERROR", f"kt_outlines: {len(ids)-len(set(ids))} duplicate ids"))
    bad_pts = [r["id"] for r in rows
               if not (lambda p: isinstance(p, list) and len(p) >= 2)(_safe_json(r.get("points")))]
    if bad_pts:
        out.append(("ERROR", f"kt_outlines: {len(bad_pts)} rows with an unusable polygon: {bad_pts[:5]}"))
    known = {r[0].strip() for r in rd_master()}
    orph = sorted({r["batch"].strip() for r in rows if r["batch"].strip() not in known})
    if orph:
        out.append(("ERROR", f"kt_outlines: {len(orph)} batches not in ABLATION_MASTER: {orph[:3]}"))
    # master mirror (§3c id-key convention)
    mm = {}
    for r in rd_master(as_dict=True):
        if r.get("kt_outline_ids"): mm[r["Batch Name"].strip()] = set(r["kt_outline_ids"].split(","))
    miss = []
    for b in {r["batch"].strip() for r in rows}:
        want = {r["id"] for r in rows if r["batch"].strip() == b}
        if mm.get(b, set()) != want: miss.append(b)
    if miss:
        out.append(("WARN", f"kt_outlines: master kt_outline_ids out of sync for {len(miss)} batches: {miss[:3]}"))
    zs = sum(1 for r in rows if (r.get("z_slice") or "0") not in ("", "0"))
    if zs:
        out.append(("INFO", f"kt_outlines: {zs} traces sit on a z-slice, not a distinct timepoint"))
    return out


def _safe_json(s):
    try: return json.loads(s or "")
    except Exception: return None


def rd_master(as_dict=False):
    t = open(f"{ROOT}/ABLATION_MASTER.csv", encoding="utf-8", errors="replace").read().replace("\r\n", "\n").replace("\r", "\n")
    rows = list(csv.reader(io.StringIO(t)))
    hi = next(i for i, r in enumerate(rows) if r and r[0].strip() == "Batch Name")
    if not as_dict:
        return [r for r in rows[hi + 1:] if r and r[0].strip()]
    hdr = [c.strip() for c in rows[hi]]
    return [{c: (r[i].strip() if i < len(r) else "") for i, c in enumerate(hdr)}
            for r in rows[hi + 1:] if r and r[0].strip()]


@check("D2", "duplicate annotation rows (same batch/label/frame/position)")
def d2():
    out = []
    for f in ["kt_points.csv","meta_plates.csv","cell_outlines.csv"]:
        c = collections.Counter((r["batch"].strip(), r.get("label"), r.get("frame"),
                                 r.get("x"), r.get("y"), (r.get("points") or "")[:40],
                                 re.search(r"kt:(\d+)", r.get("notes") or "").group(1) if re.search(r"kt:(\d+)", r.get("notes") or "") else "")
                                for r in rd(f"{A}/{f}"))
        d = [k for k, n in c.items() if n > 1]
        if d: out.append(("WARN", f"{f}: {len(d)} duplicate rows (e.g. {d[0][:4]})"))
    return out


@check("C1", "eligible on-target cells missing chromosome rows")
def c1():
    rows, _ = master_rows()
    cc = collections.defaultdict(set)
    for r in rd(f"{A}/CHROMOSOME_MASTER.csv"): cc[r["batch"].strip()].add(r["chr_num"])
    miss = []
    for r in rows:
        n = (r.get("# Sisterless KTs") or "").strip()
        if n not in ("1","2","3"): continue
        if (r.get("On-Target / Off-Target") or "").strip().lower()[:2] != "on": continue
        if (r.get("Exclude") or "").strip().lower() in ("yes","true","1"): continue
        if len(cc.get(r["Batch Name"], set())) < int(n): miss.append(f"{r['Batch Name']} ({len(cc.get(r['Batch Name'],set()))}/{n})")
    return [("INFO", f"{len(miss)} eligible cells lack a full chromosome set: {miss[:5]}")] if miss else []


# ---------------------------------------------------------------- LOSS
@check("L1", "no batch has FEWER annotations now than in any earlier snapshot")
def l1():
    """COUNT-based loss detection, per (batch, label).

    Two earlier attempts were unreliable and I state why:
      v1 keyed on (batch, label, frame) -> cell outlines were RE-ANCHORED to new frames in June 2026, so
         re-anchored rows looked deleted.
      v2 keyed on geometry -> the 2026-07-20 freehand->2-point meta_plate conversion RE-FIT each line, moving
         even its endpoints, so converted rows looked deleted (reported 129 lost for a batch whose true
         deficit was 3).
    Counts survive both transformations: re-anchoring and re-fitting preserve the number of annotations.
    A deficit therefore means rows genuinely disappeared. Deliberate deletions are excluded via the
    _retired/ and *_REMOVED_* archives."""
    KT = {"pre_abl","pre_abl_pair","post_abl","post_abl_pair","cytosol_bg","polar","lagging","sisterless","paired_kt","mad1_sister"}
    TGT = {"cell_outline":"cell_outlines.csv","meta_plate":"meta_plates.csv","chromo_line":"chromo_lines.csv",
           "lagging_length":"lagging_lengths.csv","lagging_width":"lagging_lengths.csv",
           "kt_outline":"kt_outlines.csv","crop":"crop_boxes.csv"}

    # KEY ON (batch, TYPE) OVER DISTINCT GEOMETRY.  Fixed 2026-07-22: this check counted by (batch,label)
    # only and never opened kt_outlines.csv, a store that did not exist when it was written -- a kinetochore
    # OUTLINE carries label "polar"/"lagging"/"plate" with type "kt_outline", so the check looked for those
    # labels in kt_points.csv, found none, and reported them lost.
    # Fixed again 2026-07-27, two remaining false-positive sources, both measured:
    #   (a) RE-TYPING.  Keying on the label made every relabel look like loss: the user's 07-27 review moved
    #       133 outlines from polar to paired in 20250401 ptk_yfpcdc20_28 and L1 called it "133 unaccounted
    #       for" while the geometry never moved.  Loss is a property of (batch, TYPE); a label change inside
    #       a type conserves the count.  Label movements are still reported, as INFO.
    #   (b) DUPLICATE ROWS.  serve_annotation's live duplicate-id bug writes the same trace twice, so a
    #       snapshot's ROW count exceeds its true annotation count and the live file looks short (e.g.
    #       20250711 double ablation_21 "60 -> 49" is 49 traces recorded 60 times).  Counting DISTINCT
    #       (frame, geometry) per (batch,type) is immune to it, and to the re-anchoring/re-fitting that
    #       defeated the two earlier attempts described above.
    # Net effect on the standing backlog: 41 deficits / 605 annotations -> 5 deficits / 32 annotations.
    def _ident(r):
        g = (r.get("points") or "").strip()
        return g if g else f"{r.get('x','')}|{r.get('y','')}|{r.get('w','')}|{r.get('h','')}"

    def counts(rows, by_label=False):
        seen = collections.defaultdict(set)
        for r in rows:
            lab = r.get("label")
            if not lab: continue
            key = ((r.get("batch") or "").strip(), (r.get("type") or "").strip())
            if by_label: key = key + (lab,)
            seen[key].add((r.get("frame", ""), _ident(r)))
        return collections.Counter({k: len(v) for k, v in seen.items()})

    STORES = set(list(TGT.values()) + ["kt_points.csv", "kt_outlines.csv", "crop_boxes.csv",
                                       "polar_tracks.csv", "poles.csv", "timestrip_frames.csv"])
    live, live_lab = collections.Counter(), collections.Counter()
    for f in STORES:
        pth = f"{A}/{f}"
        if os.path.exists(pth):
            rows = rd(pth); live += counts(rows); live_lab += counts(rows, True)

    # deliberate deletions, archived to _retired/ or *_REMOVED_* with a README line stating why
    removed = collections.Counter()
    for f in glob.glob(f"{ROOT}/_master_backups/*_REMOVED_*.csv") + glob.glob(f"{ROOT}/_retired/*.csv"):
        removed += counts(rd(f))

    # KNOWN, ACCEPTED losses: entries the user has seen and decided not to restore. Kept visible as a WARN
    # so they never vanish, but they do not fire as ERROR on every run.  dataops/ACCEPTED_LOSSES.csv.
    accepted, acc_why = collections.Counter(), {}
    for r in rd(f"{ROOT}/dataops/ACCEPTED_LOSSES.csv"):
        try: n = int((r.get("count") or "0").strip())
        except ValueError: continue
        k = ((r.get("batch") or "").strip(), (r.get("type") or "").strip())
        accepted[k] += n; acc_why[k] = (r.get("reason") or "").strip()

    peak, where, peak_lab = collections.Counter(), {}, collections.Counter()
    scanned = 0
    for s in glob.glob("/Users/mblaauw/Downloads/annotations_*.csv") + glob.glob(f"{ROOT}/_master_backups/*_pre_*.csv"):
        rows = rd(s)
        if not rows or "label" not in rows[0]: continue
        scanned += 1
        for k, n in counts(rows).items():
            if k[1] not in TGT: continue
            if n > peak[k]: peak[k] = n; where[k] = os.path.basename(s)
        for k, n in counts(rows, True).items():
            if k[1] not in TGT and k[2] not in KT and k[2] not in TGT: continue
            if n > peak_lab[k]: peak_lab[k] = n

    out = [("INFO", f"scanned {scanned} snapshots; distinct (frame,geometry) per (batch,type); "
                    f"deliberate deletions and ACCEPTED_LOSSES.csv excluded")]
    deficits, accepted_hits = [], []
    for k, n in peak.items():
        have = live[k] + removed[k]
        if have >= n: continue
        short = n - have
        if accepted[k] >= short:
            accepted_hits.append((short, k, acc_why.get(k, "")))
        else:
            deficits.append((short - accepted[k], k, n, have + accepted[k], where[k]))
    deficits.sort(reverse=True)
    if accepted_hits:
        accepted_hits.sort(reverse=True)
        # 2026-08-17: WARN -> INFO, matching the ACCEPTED_STALE_FRAMES registry that G2 gained the same day.
        # Both registries hold the SAME underlying situation -- annotations whose snapshot frame indices
        # predate a re-crop, so restoring or re-anchoring them would place marks on the wrong images -- and
        # all four remaining entries were re-checked on 2026-08-17 and confirmed still not restorable. INFO
        # keeps them printed in full on every run (the point of the registry) at their true severity, so a
        # genuinely NEW loss still stands out as an ERROR instead of hiding in a line that never goes quiet.
        out.append(("INFO", f"{len(accepted_hits)} known-and-accepted losses "
                            f"({sum(d for d, _, _ in accepted_hits)} annotations), not restored: "
                            + "; ".join(f"{k[0]} [{k[1]}] -{d}" for d, k, _ in accepted_hits[:6])))
    # label MOVEMENTS inside a type (re-typing) — informational, never loss
    moved = 0
    for k, n in peak_lab.items():
        if live_lab[k] + removed[k] < n: moved += n - live_lab[k] - removed[k]
    if moved:
        out.append(("INFO", f"{moved} annotations changed label inside their type since a snapshot "
                            f"(re-typing, not loss — geometry conserved)"))
    # A batch that is no longer IN the master was renamed by reprocessing (batch identity changed when
    # image-analysis names became raw-acquisition names, NOTES §10).  Its old-name rows are not "lost" --
    # they were re-keyed.  Report those separately so the real deficit is not buried.
    try:
        _m = list(csv.reader(open(f"{ROOT}/ABLATION_MASTER.csv")))
        _hi = next(i for i, r in enumerate(_m) if r and r[0].strip() == "Batch Name")
        live_batches = {r[0].strip() for r in _m[_hi + 1:] if r and r[0].strip()}
    except Exception:
        live_batches = set()
    renamed = [d for d in deficits if d[1][0] not in live_batches]
    real = [d for d in deficits if d[1][0] in live_batches]
    for d, k, was, have, src in real[:20]:
        out.append(("ERROR", f"{k[0]} [{k[1]}]: {was} in {src}, only {have} now (+archived/accepted) — {d} unaccounted for"))
    if real:
        out.append(("INFO", f"{len(real)} (batch,type) pairs with a deficit on a LIVE batch; "
                            f"total {sum(d for d, _, _, _, _ in real)} annotations"))
    if renamed:
        out.append(("INFO", f"{len(renamed)} pairs ({sum(d for d,_,_,_,_ in renamed)} annotations) belong to "
                            f"batch names that are no longer in the master — renamed by reprocessing, re-keyed, "
                            f"not lost: {sorted({d[1][0] for d in renamed})[:5]}"))
    return out


@check("P1", "publication library in step with the working library")
def _pub_in_step():
    """`_ai_relink/pdf_pub/` is a SECOND RENDERING of each figure (PUB=1: titles stripped, long text
    blanked, labels canonicalised), linked ONLY by the two *_PUBLICATION.ai decks. A normal builder
    re-run refreshes `pdf/` and silently leaves `pdf_pub/` behind, so the publication copies keep
    showing yesterday's figure. That went unnoticed twice in two days (2026-08-18), which is why it
    is a standing check rather than something to remember.
    Fix: `python3 dataops/sync_pub.py`."""
    out = []
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import sync_pub
        stale, missing, total = sync_pub.audit()
    except Exception as e:
        return [("WARN", f"could not audit the publication library: {type(e).__name__}: {e}")]
    if not total:
        return [("INFO", "no geometry dump found - run DUMP_ALL9 first to audit the publication library")]
    if missing:
        out.append(("ERROR", f"{len(missing)} figure(s) on a mirrored deck have NO publication twin "
                             f"(e.g. {missing[:3]}) - run dataops/sync_pub.py"))
    if stale:
        out.append(("ERROR", f"{len(stale)} publication twin(s) are older than the working PDF "
                             f"(e.g. {stale[:3]}) - run dataops/sync_pub.py"))
    return out


def run_all(only=None):
    rep = {"checks": [], "counts": collections.Counter()}
    for cid, title, fn in REG:
        if only and cid not in only: continue
        try: res = fn() or []
        except Exception as e: res = [("ERROR", f"check crashed: {type(e).__name__}: {e}")]
        rep["checks"].append({"id": cid, "title": title,
                              "findings": [{"severity": s, "message": m} for s, m in res]})
        for s, _ in res: rep["counts"][s] += 1
        if not res: rep["counts"]["PASS"] += 1
    return rep



@check("IF1", "no fixed-IF (0.031 um/px) cell inside a micron-valued figure")
def check_if_cells_not_in_micron_figures():
    """A FIXED-IF cell in a figure whose values are in microns is a SCALE ERROR, not a cohort question.

    IF acquisitions are z-stacks at 0.031 um/px -- half the 0.062 of every timelapse cell -- so a builder
    that converts pixels to microns with a fixed scale would report their distances at DOUBLE. They are
    deliberately NOT excluded globally (they are the subject of `G5_item2_IF_KT_561/640`), so this guards
    the actual hazard instead. Added 2026-08-20, when she asked whether 0.031/0.058 cells reach the main or
    supplemental decks; at that time none did, and this keeps it that way.
    """
    import csv as _c, glob as _g, os as _o, sys as _s
    _s.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
    import lib as _l
    out = []
    for p_ in _g.glob("/Volumes/4 MB/ablation_plots/data/*.csv"):
        try:
            with open(p_, newline="", encoding="utf-8", errors="replace") as fh:
                rd = _c.DictReader(fh)
                fn = rd.fieldnames or []
                bcol = next((c for c in fn if c and c.strip().lower() in ("batch", "batch name", "cell")), None)
                # a column is micron-VALUED only if it holds a measurement. `pixel_um` and `scalebar_um`
                # are METADATA -- the first version of this check flagged the two IF figures on those and
                # was a false positive, which is worse than no check because it trains you to ignore it.
                META = {"pixel_um", "pixel_size_um", "scalebar_um", "bar_um", "px_um"}
                umcol = [c for c in fn
                         if c and c.strip().lower() not in META
                         and ("_um" in c.lower() or "um)" in c.lower())]
                if not bcol or not umcol:
                    continue
                rows_ = list(rd)
                vals = set()
                for r in rows_:
                    for c in umcol:
                        v = (r.get(c) or "").strip()
                        try:
                            vals.add(round(float(v), 6))
                        except ValueError:
                            pass
                if len(vals) < 3:              # a constant is a setting, not a measured distance
                    continue
                hits = {(r.get(bcol) or "").strip() for r in rows_}
        except Exception:
            continue
        n = sum(1 for b in hits if b and _l.is_if(b))
        if n:
            out.append(("ERROR", f"{_o.path.basename(p_)[:-4]}: {n} fixed-IF cell(s) in a micron-valued "
                                 "figure (0.031 vs 0.062 um/px -> distances doubled)"))
    return out


@check("DECK1", "live deck registry resolves, and no live tool points at a retired deck")
def check_deck_registry():
    """She renames and re-saves decks as she works, and a path hardcoded in a dozen scripts then becomes a
    silent pointer to a retired file that still opens and still looks plausible.

    2026-08-19 `supplemental.ai` -> `other.ai`; 2026-08-20 both PUBLICATION decks and `other.ai` -> the
    `_20260820` versions after she spent hours in them. `annotations/DECKS.json` is the one place the live
    paths are written down; this fails if any of them has moved, or if a LIVE tool still names a retired
    file. Historical one-off JSX keep their literals on purpose -- they are a record of what was done, not
    tools that get run again.
    """
    import json as _j, os as _o, io as _io, glob as _g
    out = []
    try:
        reg = _j.load(open("/Volumes/4 MB/annotations/DECKS.json"))
    except Exception as e:
        return [("ERROR", f"DECKS.json unreadable: {e}")]
    for d in reg.get("decks", []):
        if not _o.path.exists(d["path"]):
            out.append(("ERROR", f"live deck {d['tag']} missing: {_o.path.basename(d['path'])}"))
    retired = [_o.path.basename(r["path"]) for r in reg.get("retired", [])]
    LIVE_DIRS = ("/Volumes/4 MB/dataops", "/Volumes/4 MB/_claude_tools",
                 "/Volumes/4 MB/ablation_figures_20260625")
    for d in LIVE_DIRS:
        for p_ in _g.glob(f"{d}/*"):
            base = _o.path.basename(p_)
            if (_o.path.isdir(p_) or ".bak" in base or base.endswith((".png", ".pdf", ".csv", ".json"))):
                continue
            try:
                s_ = _io.open(p_, encoding="utf-8", errors="replace").read()
            except Exception:
                continue
            for r in retired:
                if f"/{r}" in s_ or f'"{r}"' in s_:
                    out.append(("ERROR", f"{_o.path.relpath(p_, '/Volumes/4 MB')} still names retired deck {r}"))
    return out


if __name__ == "__main__":
    rep = run_all()
    if "--json" in sys.argv:
        print(json.dumps(rep, indent=1)); sys.exit(0)
    for c in rep["checks"]:
        if not c["findings"]:
            print(f"  PASS  [{c['id']}] {c['title']}")
        else:
            for f in c["findings"]:
                print(f"  {f['severity']:5s} [{c['id']}] {f['message']}")
    n = rep["counts"]
    print("\n" + "=" * 78)
    print(f"checks run {len(rep['checks'])}   PASS {n['PASS']}   ERROR {n['ERROR']}   WARN {n['WARN']}   INFO {n['INFO']}")
    sys.exit(1 if n["ERROR"] else 0)
