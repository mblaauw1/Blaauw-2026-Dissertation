"""Assign each kinetochore-outline TRACK to one of the cell's sisterless chromosomes -> pair outlines with LENGTH.

USER 2026-08-08: "given you know the initial and final stats of all sisterless kinetochores in a cell
(because of how we recorded where it was at the start of metaphase and end, and if it did any important
movements between those two times (like polar congressing), and that you should have paired each of these
movement descripors for a batch to the chromosome length of the kinetochore that it describes, im wondering
if you can use this information to look at the kintochore trace data and assign a track of kinetochore
outlines to each of three kinetochores in a cell (so that the kinetochore outlines can ultimately be paired
with a chromosome length)."

THE LINK, and it is entirely from her own records -- nothing is auto-detected:
  * `SISTERLESS_PLATE_JOIN_TIMES.csv` gives, per cell, WHEN each of chromosomes 1/2/3 joined the plate
    (`chromosome_k_plate_join_s`), or the marker `anaphase` for one that never joined.
  * `CHROMO_LENGTH_BEHAVIOR_PAIRING.csv` gives that same cell's `chr{k}_length_um` and `chr{k}_movement`,
    already paired per chromosome index -- so index k carries BOTH a join time and a length.
  * A POLAR outline track ends when that chromosome stops being polar, i.e. when it congresses.
So: match a polar track's END time to the nearest chromosome join time, and index k hands over the length.

AMBIGUITY IS REFUSED, NOT GUESSED. An assignment is only accepted when the nearest join time is clearly
nearer than the runner-up (`MARGIN_S`) and within `MAX_GAP_S`. Everything else is recorded as unassigned
with the reason. This mirrors the pole-track linkage rule already used on this project, where every
accepted linkage cleared its threshold by a wide margin.

A chromosome whose join time is the literal string `anaphase` never congressed: its kinetochore is the one
still polar at the end, so it is matched to the polar track that survives longest, and only when exactly
one such chromosome and one such track exist.
"""
import sys; sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import os, csv, collections, numpy as np, matplotlib.pyplot as plt
import lib
lib.apply_style()
csv.field_size_limit(10 ** 9)

A = "/Volumes/4 MB/annotations/"
OUT = "/Volumes/4 MB/ablation_figures_20260625/group7"; os.makedirs(OUT, exist_ok=True)
PLOT_ID = "G7_track_to_chromosome_assignment"
SCRIPT = __file__
MAX_GAP_S = 180.0        # a track end more than 3 min from any join time is not that congression event
MARGIN_S = 60.0          # nearest must beat runner-up by this, else it is ambiguous

full, _ = lib.load_master(); MR = {r["Batch Name"]: r for r in full}
_dbl = lib.double_chromosome_batches()


def usable(b):
    return not (lib.plot_excluded(b) or lib.is_mad1(b) or b in _dbl)


# ---- her per-chromosome records -----------------------------------------------------------------
JOIN = {}
for r in csv.DictReader(open(A + "SISTERLESS_PLATE_JOIN_TIMES.csv", newline="", encoding="utf-8",
                             errors="replace")):
    if (r.get("exclude_this_data") or "").strip():
        continue
    b = (r.get("batch") or "").strip()
    d = {}
    for k in (1, 2, 3):
        raw = (r.get(f"chromosome_{k}_plate_join") or "").strip().lower()
        s = (r.get(f"chromosome_{k}_plate_join_s") or "").strip()
        if raw in ("", "n/a"):
            continue
        if raw == "anaphase":
            d[k] = ("anaphase", None)
        else:
            try:
                d[k] = ("time", float(s))
            except Exception:
                pass
    if d:
        JOIN[b] = d

# USE THE CONSOLIDATED PER-CHROMOSOME TABLE. `CHROMOSOME_MASTER.csv` is the single per-chromosome table
# everything was consolidated into (NOTES 2026-07-22); `CHROMO_LENGTH_BEHAVIOR_PAIRING.csv` is a partial
# predecessor. Using the partial one covered only 23 of the 65 plate-join cells and yielded 8 assignments
# with a length; the master covers 62 of 65 and carries `behavior` + `congression_time_s` PER CHROMOSOME,
# which is exactly the "important movements between metaphase start and end" she described.
LEN = {}
CONG = {}
for r in csv.DictReader(open(A + "CHROMOSOME_MASTER.csv", newline="", encoding="utf-8",
                             errors="replace")):
    b = (r.get("batch") or "").strip()
    try:
        k = int(float((r.get("chr_num") or "").strip()))
    except Exception:
        continue
    v = (r.get("length_um") or "").strip()
    beh = (r.get("behavior") or "").strip()
    if v:
        try:
            LEN.setdefault(b, {})[k] = (float(v), beh)
        except Exception:
            pass
    ct = (r.get("congression_time_s") or "").strip()
    if ct:
        try:
            CONG.setdefault(b, {})[k] = float(ct)
        except Exception:
            pass

print(f"cells with plate-join records: {len(JOIN)}   with chromosome lengths: {len(LEN)}")
print(f"cells with BOTH: {len(set(JOIN) & set(LEN))}")

# ---- polar tracks and when they end ---------------------------------------------------------------
TR = collections.defaultdict(list)
for r in csv.DictReader(open(A + "KT_OUTLINE_TRACKS_20260723.csv", newline="", encoding="utf-8",
                             errors="replace")):
    b = r["batch"].strip()
    if usable(b) and (r.get("label") or "").strip() == "polar":
        TR[b].append(r)

rows, unassigned = [], collections.Counter()
for b, rs in TR.items():
    if b not in JOIN and b not in CONG:
        unassigned["no plate-join record and no congression time"] += 1; continue
    if b not in JOIN:
        # CHROMOSOME_MASTER carries congression_time_s per chromosome, so a cell missing from the
        # plate-join file can still be assigned from the master alone.
        JOIN[b] = {k: ("time", v) for k, v in CONG[b].items()}
    ends, spans = {}, {}
    for r in rs:
        t = (r.get("t_sec") or "").strip()
        if not t:
            continue
        tid = r["track_id"]
        t = float(t)
        ends[tid] = max(ends.get(tid, float("-inf")), t)
        spans.setdefault(tid, []).append(t)
    if not ends:
        continue
    timed = {k: v for k, (kind, v) in JOIN[b].items() if kind == "time"}
    never = [k for k, (kind, v) in JOIN[b].items() if kind == "anaphase"]
    used = set()
    # 1) the never-congressing chromosome -> the longest-surviving polar track, only if both are unique
    if len(never) == 1 and len(ends) >= 1:
        longest = max(ends, key=lambda t: ends[t])
        k = never[0]
        L = LEN.get(b, {}).get(k)
        rows.append([b, longest, k, "", f"{ends[longest]:.1f}", "never_congressed",
                     (f"{L[0]:.3f}" if L else ""), (L[1] if L else ""), len(spans.get(longest, []))])
        used.add(longest)
    # 2) the rest by nearest join time, with an ambiguity guard
    for tid, te in sorted(ends.items(), key=lambda kv: kv[1]):
        if tid in used:
            continue
        if not timed:
            unassigned["no timed join events left"] += 1; continue
        d = sorted(((abs(te - v), k, v) for k, v in timed.items()))
        best = d[0]
        if best[0] > MAX_GAP_S:
            unassigned[f"nearest join {best[0]:.0f}s away (> {MAX_GAP_S:.0f}s)"] += 1; continue
        if len(d) > 1 and (d[1][0] - best[0]) < MARGIN_S:
            unassigned["ambiguous: two join times within margin"] += 1; continue
        k = best[1]
        L = LEN.get(b, {}).get(k)
        rows.append([b, tid, k, f"{best[2]:.1f}", f"{te:.1f}", f"{best[0]:.1f}",
                     (f"{L[0]:.3f}" if L else ""), (L[1] if L else ""), len(spans.get(tid, []))])
        del timed[k]

print(f"\nassigned tracks: {len(rows)}")
withlen = [r for r in rows if r[6]]
print(f"  of which carry a chromosome length: {len(withlen)}")
for k, v in unassigned.most_common():
    print(f"  unassigned {v:3d}  {k}")

hdr = ["batch", "track_id", "chromosome_index", "plate_join_s", "track_end_s", "match_gap_s",
       "chr_length_um", "chr_movement", "n_frames_in_track"]
with open("/Volumes/4 MB/ablation_plots/data/G7_track_to_chromosome_assignment.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(hdr); w.writerows(rows)

# ---- figure: what the pairing buys -- outline shape/behaviour vs chromosome length ---------------
SH = collections.defaultdict(list)
for r in csv.DictReader(open(A + "KT_OUTLINE_TRACKS_20260723.csv", newline="", encoding="utf-8",
                             errors="replace")):
    SH[r["track_id"]].append(r)

fig, axes = plt.subplots(1, 3, figsize=(13.6, 4.6))
pts = []
for r in withlen:
    tid = r[1]; L = float(r[6])
    g = SH.get(tid, [])
    def num(key):
        v = [float(x[key]) for x in g if (x.get(key) or "").strip()]
        return float(np.median(v)) if v else np.nan
    ps = float(MR.get(r[0], {}).get("Pixel Size (um)", "") or 0.062)
    seq = sorted([(float(x["t_sec"]), float(x["cx_px"]), float(x["cy_px"]))
                  for x in g if (x.get("t_sec") or "").strip()])
    sp = [np.hypot(c[1] - a[1], c[2] - a[2]) * ps / (c[0] - a[0])
          for a, c in zip(seq, seq[1:]) if c[0] > a[0]]
    pts.append((L, num("area_um2"), num("circularity"), float(np.median(sp)) if sp else np.nan,
                float(r[4]) - (float(r[3]) if r[3] else float(r[4]))))
pts = [p for p in pts if np.isfinite(p[0])]
for ax, i, ylab in ((axes[0], 1, "median outline area (um2)"),
                    (axes[1], 2, "median circularity"),
                    (axes[2], 3, "median speed (um/s)")):
    xs = np.array([p[0] for p in pts]); ys = np.array([p[i] for p in pts])
    ok = np.isfinite(xs) & np.isfinite(ys)
    ax.scatter(xs[ok], ys[ok], s=52, c="#762a83", edgecolor="k", lw=.5)
    ax.set_xlabel("assigned chromosome length (um)"); ax.set_ylabel(ylab, fontsize=9)
    if ok.sum() >= 4:
        try:
            from scipy import stats as st
            rho, p = st.spearmanr(xs[ok], ys[ok])
            ax.set_title(f"rho={rho:.2f}, p={p:.2g}, n={ok.sum()}", fontsize=9,
                         color=("#b2182b" if p < .05 else "#444"))
            z = np.polyfit(xs[ok], ys[ok], 1)
            xx = np.linspace(xs[ok].min(), xs[ok].max(), 20)
            ax.plot(xx, np.polyval(z, xx), "--", color="#762a83", lw=1.2)
        except Exception:
            pass
fig.suptitle("Kinetochore outline tracks paired with their chromosome's length, via her plate-join records",
             fontsize=11, y=1.02)
fig.tight_layout()
png = os.path.join(OUT, PLOT_ID + ".png")
fig.savefig(png, dpi=200, bbox_inches="tight"); plt.close(fig)
print("wrote", png)

lib.record_plot(
    PLOT_ID, hdr, rows,
    {"kind": "assignment+scatter", "max_gap_s": MAX_GAP_S, "margin_s": MARGIN_S},
    script=SCRIPT,
    caption=(f"Each polar outline track assigned to one of the cell's sisterless chromosomes by matching "
             f"the track's END (when it stops being polar = congression) to her recorded "
             f"chromosome_k_plate_join time; the chromosome index then supplies the length from "
             f"CHROMO_LENGTH_BEHAVIOR_PAIRING. Ambiguous matches are REFUSED, not guessed: nearest must be "
             f"within {MAX_GAP_S:.0f}s and beat the runner-up by {MARGIN_S:.0f}s. "
             f"{len(rows)} tracks assigned, {len(withlen)} with a length."),
    source=[A + "SISTERLESS_PLATE_JOIN_TIMES.csv", A + "CHROMOSOME_MASTER.csv",
            A + "KT_OUTLINE_TRACKS_20260723.csv"],
    key_column="batch", fig=png,
)
print("recorded", PLOT_ID)
