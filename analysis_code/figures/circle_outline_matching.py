#!/usr/bin/env python3
"""Which circle marker belongs to which MANUAL kt_outline? (user 2026-07-28)

Her constraints, implemented as hard rules:
  R1  SAME FRAME ONLY. A circle is never matched to an outline from another plane/frame.
  R2  SAME KINETOCHORE TYPE. polar/sisterless circle -> polar outline; paired_kt -> paired;
      lagging -> lagging. A cross-type match means it grabbed a different kinetochore.
  R3  ONE-TO-ONE within a frame. Two circles on one frame annotate two DIFFERENT kinetochores, so they
      can never claim the same outline. Solved as a global optimal assignment (Hungarian), not greedy
      nearest — greedy is exactly what produces double-claims.
  R4  NOT EVERYTHING PAIRS. A circle may mark a kinetochore she never traced (e.g. a different control KT),
      and an outline may have no circle. Those stay UNMATCHED and fall back to image centering rather than
      being forced onto a wrong partner.
  R5  DISTANCE CEILING. Beyond MAX_PX the two marks are not the same object whatever the labels say.

Also reports, for the OLD greedy nearest-outline rule, how often each rule was violated — that is the
"is this actually happening?" check.

Writes annotations/CIRCLE_OUTLINE_MATCH_20260728.csv (one row per circle, matched or not).
"""
import sys, os, csv, json, collections
sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import numpy as np
from scipy.optimize import linear_sum_assignment
import lib
ROOT = "/Volumes/4 MB"; csv.field_size_limit(10 ** 9)
A = f"{ROOT}/annotations"
MAX_PX = 25.0          # beyond this they are not the same kinetochore
CIRCLE_TO_OUTLINE = {"polar": "polar", "sisterless": "polar", "paired_kt": "paired", "lagging": "lagging"}

circles = collections.defaultdict(list)
for r in csv.DictReader(open(f"{A}/kt_points.csv", newline="")):
    lab = r["label"].strip()
    if lab not in CIRCLE_TO_OUTLINE or not r["frame"].strip().isdigit():
        continue
    try: circles[(r["batch"].strip(), int(r["frame"]))].append(
        dict(id=r["id"], label=lab, x=float(r["x"]), y=float(r["y"])))
    except Exception: pass

outlines = collections.defaultdict(list)
for r in csv.DictReader(open(f"{A}/kt_outlines.csv", newline="")):
    if not r["frame"].strip().isdigit():
        continue
    try: P = np.array(json.loads(r["points"]), float)
    except Exception: continue
    if len(P) < 4:
        continue
    outlines[(r["batch"].strip(), int(r["frame"]))].append(
        dict(id=r["id"], label=r["label"].strip(), c=lib.polygon_centroid(P)))

keys = sorted(set(circles) & set(outlines))
print(f"{len(keys)} (cell, frame) pairs carry BOTH circles and outlines")

greedy_wrongtype = greedy_double = 0
greedy_claims = collections.Counter()
rows = []
n_match = n_unmatched_far = n_unmatched_type = n_unmatched_taken = 0

for k in keys:
    C, O = circles[k], outlines[k]
    # ---- what the OLD greedy nearest rule would have done (the diagnostic) ----
    claims = collections.Counter()
    for c in C:
        best = min(O, key=lambda o: (o["c"][0] - c["x"]) ** 2 + (o["c"][1] - c["y"]) ** 2)
        d = float(np.hypot(best["c"][0] - c["x"], best["c"][1] - c["y"]))
        if d <= 40:
            claims[best["id"]] += 1
            if CIRCLE_TO_OUTLINE[c["label"]] != best["label"]:
                greedy_wrongtype += 1
    greedy_double += sum(v - 1 for v in claims.values() if v > 1)

    # ---- constrained optimal assignment ----
    cost = np.full((len(C), len(O)), 1e6)
    for i, c in enumerate(C):
        for j, o in enumerate(O):
            if CIRCLE_TO_OUTLINE[c["label"]] != o["label"]:
                continue                                     # R2
            d = float(np.hypot(o["c"][0] - c["x"], o["c"][1] - c["y"]))
            if d <= MAX_PX:                                  # R5
                cost[i, j] = d
    ri, cj = linear_sum_assignment(cost)                     # R3 one-to-one
    taken = {}
    for i, j in zip(ri, cj):
        if cost[i, j] < 1e6:
            taken[i] = j
    for i, c in enumerate(C):
        if i in taken:
            o = O[taken[i]]
            d = float(np.hypot(o["c"][0] - c["x"], o["c"][1] - c["y"]))
            rows.append(dict(batch=k[0], frame=k[1], circle_id=c["id"], circle_label=c["label"],
                             outline_id=o["id"], outline_label=o["label"],
                             dist_px=round(d, 2), snap_x=round(float(o["c"][0]), 2),
                             snap_y=round(float(o["c"][1]), 2), status="matched"))
            n_match += 1
        else:
            same = [o for o in O if CIRCLE_TO_OUTLINE[c["label"]] == o["label"]]
            if not same:
                st = "no outline of this type on the frame"; n_unmatched_type += 1
            else:
                dmin = min(float(np.hypot(o["c"][0] - c["x"], o["c"][1] - c["y"])) for o in same)
                if dmin > MAX_PX:
                    st = f"nearest same-type outline {dmin:.0f}px away"; n_unmatched_far += 1
                else:
                    st = "same-type outline already claimed by another circle"; n_unmatched_taken += 1
            rows.append(dict(batch=k[0], frame=k[1], circle_id=c["id"], circle_label=c["label"],
                             outline_id="", outline_label="", dist_px="", snap_x="", snap_y="",
                             status=st))

with open(f"{A}/CIRCLE_OUTLINE_MATCH_20260728.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)

tot = len(rows)
print(f"\n--- OLD greedy nearest-outline rule: how often it broke her constraints ---")
print(f"  matched a circle to a DIFFERENT-TYPE outline : {greedy_wrongtype}")
print(f"  two circles claiming the SAME outline        : {greedy_double}")
print(f"\n--- constrained assignment (same frame, same type, one-to-one, <= {MAX_PX:.0f}px) ---")
print(f"  circles on frames that have outlines : {tot}")
print(f"  MATCHED to an outline                : {n_match} ({n_match/tot*100:.1f}%)")
print(f"  unmatched, no outline of that type   : {n_unmatched_type}")
print(f"  unmatched, nearest same-type too far : {n_unmatched_far}")
print(f"  unmatched, that outline already taken: {n_unmatched_taken}")
d = [r["dist_px"] for r in rows if r["status"] == "matched"]
if d:
    print(f"  matched click->outline-centre distance: median {np.median(d):.2f} px, p90 {np.percentile(d,90):.2f}")
by = collections.Counter((r["circle_label"], r["outline_label"]) for r in rows if r["status"] == "matched")
print("  matched pairs by type:", dict(by))
print(f"\nwrote {A}/CIRCLE_OUTLINE_MATCH_20260728.csv")
