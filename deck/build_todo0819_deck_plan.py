#!/usr/bin/env python3
"""Build the Illustrator operation plan for the 2026-08-19 to-do list, from the READ-ONLY geometry dumps.

WHY A GENERATED PLAN AND NOT A HAND-WRITTEN JSX
    Every operation has to be keyed to an item that really exists on the deck, at the bounds the dump
    recorded, or the JSX silently does nothing (NOTES: "scripted edits fail SILENTLY"). Generating the plan
    from `_claude_tmp/geom9_*.tsv` means every key is taken from the deck's own current state, and the plan
    file is a reviewable record of exactly what will change before anything is opened.

    It also lets each placement be solved against the geometry of the DECK BEING WRITTEN rather than its
    sibling's -- the 2026-08-18 lesson that mirroring is not a coordinate copy.

WHAT IT ENCODES (to-do list 0819 1pm)
  figure item 1 + 8   the ablation-anchored shape/rotation plots leave the main deck for the supplemental as
                      the new ablation->metaphase versions, and a rate TABLE takes their place on the main board
  figure item 9/10    "supplemental" means META_FIGURES_20260813_supplemental, and things moved there must
                      actually land ON the matching artboard
  figure item 11      the main deck keeps NINE artboards -- the "auto 2026-08-18" boards go
  all-figures item 2  every timestrip is placed as its independently movable PIECES, not one block
  all-figures item 5a the hec1/mad1 intensity plot goes next to the hec1 timestrips on the main board
  all-figures item 15 the p-value dot plot moves off the main boards
  all-figures item 16 combination figures are replaced by their individual panels
  all-figures item 17 the artboard-2 table moves to the supplemental with its two new companion figures

  PLUS a SYNC-BACK that is not on her list but is required before any of it: her PUBLICATION copies carry 15
  figures each that the working decks do not (they sit on a `legend_bullets` layer that the working decks
  lost). Rebuilding or mirroring without restoring those would delete them from her file.
"""
import collections
import io
import json
import os

ROOT = "/Volumes/4 MB"
DUMPS = f"{ROOT}/_claude_tmp"
PDF = f"{ROOT}/ablation_figures_20260625/_ai_relink/pdf"
PUBPDF = f"{ROOT}/ablation_figures_20260625/_ai_relink/pdf_pub"
OUT = f"{DUMPS}/todo0819_plan.json"

DECK_FILE = {
    "0814":     f"{ROOT}/1_DECKS/META_FIGURES_20260814.ai",
    "0813supp": f"{ROOT}/1_DECKS/META_FIGURES_20260813_supplemental.ai",
    "newfig":   f"{ROOT}/1_DECKS/NEW_FIGURES_20260804.ai",
    "supp":     f"{ROOT}/1_DECKS/other.ai",
    "newts":    f"{ROOT}/1_DECKS/NEW_TIMESTRIPS_20260804.ai",
    "pub0814":  f"{ROOT}/1_DECKS/META_FIGURES_20260814_PUBLICATION.ai",
    "pub0813":  f"{ROOT}/1_DECKS/META_FIGURES_20260813_supplemental_PUBLICATION.ai",
}
PUB_OF = {"0814": "pub0814", "0813supp": "pub0813"}
IS_PUB = {"pub0814", "pub0813"}


def rows(tag):
    p = f"{DUMPS}/geom9_{tag}.tsv"
    if not os.path.exists(p):
        return []
    out = []
    for ln in io.open(p, encoding="utf-8", errors="replace").read().replace("\r", "\n").split("\n"):
        f = ln.split("\t")
        if len(f) > 11:
            out.append(f)
    return out


def items(tag):
    """[(name, key, artboard, L, T, R, B, layer)] for every PlacedItem carrying a figure name."""
    out = []
    for f in rows(tag):
        if f[0] != "PlacedItem" or not f[5]:
            continue
        try:
            L, T, R, B = float(f[6]), float(f[7]), float(f[8]), float(f[9])
        except Exception:
            continue
        out.append({"name": f[5], "key": f"{f[0]}|{L:.1f}|{T:.1f}", "ab": f[1],
                    "L": L, "T": T, "R": R, "B": B, "layer": f[10]})
    return out


def artboards(tag):
    out = {}
    for f in rows(tag):
        if f[0] == "ARTBOARD":
            try:
                out[int(f[1])] = (f[5], float(f[6]), float(f[7]), float(f[8]), float(f[9]))
            except Exception:
                pass
    return out


def has_pdf(name, pub=False):
    return os.path.exists(f"{PUBPDF if pub else PDF}/{name}.pdf")


def pieces_of(name):
    out, n = [], 1
    while os.path.exists(f"{PDF}/{name}__piece{n}.pdf"):
        out.append(f"{name}__piece{n}")
        n += 1
    return out


def panels_of(name):
    out, n = [], 1
    while os.path.exists(f"{PDF}/{name}__p{n}.pdf"):
        out.append(f"{name}__p{n}")
        n += 1
    return out


# ── the figure-level decisions, spelled out so the plan is auditable ──────────────────────────────────
# item 1: these six leave the MAIN deck. The first four are RELINKED to their metaphase-onset twins (same
# slot, same size -- the main board is supposed to show the metaphase-onset version); the last two already
# have their `_meta` twin on the same board, so the ablation-anchored copy is simply removed.
RELINK_MAIN = {
    "G1_roundness_combined_trendscaled":        "G1_roundness_combined_meta_trendscaled",
    "G1_area_combined_trendscaled":             "G1_area_combined_meta_trendscaled",
    "G1_roundness_combined_trendscaled_delta":  "G1_roundness_combined_meta_trendscaled_delta",
    "G1_area_combined_trendscaled_delta":       "G1_area_combined_meta_trendscaled_delta",
}
REMOVE_MAIN = [
    "G1_roundness_collagen_vs_pooled",     # `_meta` twin already on the same board
    "G1_area_collagen_vs_pooled",
    "G8_pooling_2plus3_vs_3",              # item 15: the p-value dot plot -> supplemental
    "G1_collagen_duration_table",          # item 17: the artboard-2 table -> supplemental
]
# item 1 + 8 + 15 + 17: what the SUPPLEMENTAL deck gains, and on which artboard.
# The artboard numbers mirror the main deck's, per item 9 ("placed on the correctly corresponding art board
# as it was in the main to keep organization").
TO_SUPP = [
    (4, "G1_roundness_combined_abl2meta_trendscaled",       1500),
    (4, "G1_area_combined_abl2meta_trendscaled",            1500),
    (4, "G1_plate_rotation_combined_abl2meta_trendscaled",  1500),
    (4, "G1_centroid_movement_combined_abl2meta_trendscaled", 1500),
    (4, "G1_roundness_combined_abl2meta_trendscaled_delta", 1500),
    (4, "G1_area_combined_abl2meta_trendscaled_delta",      1500),
    (4, "G1_plate_rotation_combined_abl2meta_trendscaled_delta", 1500),
    (4, "G1_centroid_movement_combined_abl2meta_trendscaled_delta", 1500),
    (4, "G1_roundness_collagen_vs_pooled_abl2meta",         1500),
    (4, "G1_area_collagen_vs_pooled_abl2meta",              1500),
    (4, "G8_pooling_2plus3_vs_3",                           1500),
    (2, "G1_collagen_duration_table",                       1900),
    (2, "G1_collagen_duration_dist",                        1500),
    (2, "G1_collagen_duration_percell",                     1500),
]
# item 8: the rate table takes the moved plots' place on the MAIN board 4.
TO_MAIN = [
    (4, "G1_shape_rate_table", 2200),
    (1, "G5_hec1_mad1_dot_quant", 1500),     # item 5a: "supposed to be a plot with the intensity of hec1
]                                            #  ... on the main artboard next to these timestrips but its not there"


def main():
    ops = []
    notes = []

    # ── 0. SYNC-BACK: figures that live only on her publication copies ────────────────────────────
    for work, pub in PUB_OF.items():
        wnames = {i["name"] for i in items(work)}
        for it in items(pub):
            if it["name"] in wnames or "__piece" in it["name"]:
                continue
            if not has_pdf(it["name"]):
                notes.append(f"SYNC SKIP (no working pdf): {it['name']}")
                continue
            ops.append({"deck": work, "op": "place", "name": it["name"],
                        "at": [it["L"], it["T"]], "w": round(it["R"] - it["L"], 1),
                        "pub": False, "why": f"sync-back from {pub} (was only on the publication copy)"})
            wnames.add(it["name"])

    # ── 1. main deck: relink / remove / place (and the same on its publication copy) ───────────────
    for deck in ("0814", "pub0814"):
        pub = deck in IS_PUB
        for it in items(deck):
            if it["name"] in RELINK_MAIN:
                to = RELINK_MAIN[it["name"]]
                if not has_pdf(to, pub):
                    notes.append(f"{deck}: relink target missing: {to} (pub={pub})"); continue
                ops.append({"deck": deck, "op": "relink", "key": it["key"], "to": to, "pub": pub,
                            "why": "item 1 -- main board shows the metaphase-onset version"})
            elif it["name"] in REMOVE_MAIN:
                ops.append({"deck": deck, "op": "remove", "key": it["key"], "name": it["name"],
                            "why": "item 1/15/17 -- moved to the supplemental deck"})
        have_main = {i["name"] for i in items(deck)}
        for ab, name, w in TO_MAIN:
            # idempotent: this plan is regenerated and re-applied until nothing is left, so never place a
            # second copy of something the deck already carries
            if name in have_main:
                notes.append(f"{deck}: already carries {name}"); continue
            if not has_pdf(name, pub):
                notes.append(f"{deck}: cannot place {name} (pub={pub}) -- no pdf"); continue
            ops.append({"deck": deck, "op": "place", "ab": ab, "name": name, "w": w, "pub": pub,
                        "why": "item 8 / item 5a"})

    # ── 2. supplemental deck: receive everything the main deck gave up ─────────────────────────────
    for deck in ("0813supp", "pub0813"):
        pub = deck in IS_PUB
        have = {i["name"] for i in items(deck)}
        for ab, name, w in TO_SUPP:
            if name in have:
                notes.append(f"{deck}: already carries {name}"); continue
            if not has_pdf(name, pub):
                notes.append(f"{deck}: cannot place {name} (pub={pub}) -- no pdf"); continue
            ops.append({"deck": deck, "op": "place", "ab": ab, "name": name, "w": w, "pub": pub,
                        "why": "item 1/8/15/17 -- moved off the main deck"})

    # ── 3. item 11: the main figure file keeps NINE artboards ──────────────────────────────────────
    for deck in ("0814", "pub0814", "0813supp", "pub0813"):
        ab = artboards(deck)
        extra = sorted([i for i, v in ab.items() if str(v[0]).startswith("auto 2026-08-18")], reverse=True)
        for i in extra:
            ops.append({"deck": deck, "op": "delartboard", "ab": i, "abname": ab[i][0],
                        "why": "item 11 -- one artboard per thesis figure; the auto boards are not figures"})

    # ── 4. item 2: every timestrip placed as its independently movable pieces ──────────────────────
    for deck in DECK_FILE:
        pub = deck in IS_PUB
        for it in items(deck):
            if "__piece" in it["name"]:
                continue
            pcs = pieces_of(it["name"])
            if len(pcs) < 2:
                continue
            if pub and not all(has_pdf(p, True) for p in pcs):
                notes.append(f"{deck}: pieces of {it['name']} have no publication twin yet"); continue
            ops.append({"deck": deck, "op": "pieces", "key": it["key"], "name": it["name"],
                        "names": pcs, "at": [it["L"], it["T"]], "w": round(it["R"] - it["L"], 1),
                        "pub": pub, "why": "item 2 -- ablation and monitoring must be movable separately"})

    # ── 5. item 16: no combination figures; place their panels instead ─────────────────────────────
    for deck in DECK_FILE:
        pub = deck in IS_PUB
        for it in items(deck):
            if "__p" in it["name"] or "__piece" in it["name"]:
                continue
            pans = panels_of(it["name"])
            if len(pans) < 2:
                continue
            if pub and not all(has_pdf(p, True) for p in pans):
                notes.append(f"{deck}: panels of {it['name']} have no publication twin yet"); continue
            ops.append({"deck": deck, "op": "pieces", "key": it["key"], "name": it["name"],
                        "names": pans, "at": [it["L"], it["T"]], "w": round(it["R"] - it["L"], 1),
                        "pub": pub, "why": "item 16 -- a combination figure that can only be moved as one piece"})

    plan = {"decks": DECK_FILE, "pdf": PDF, "pub_pdf": PUBPDF, "ops": ops, "notes": notes}
    json.dump(plan, open(OUT, "w"), indent=1)
    c = collections.Counter((o["deck"], o["op"]) for o in ops)
    print(f"plan -> {OUT}")
    for k in sorted(c):
        print(f"   {k[0]:10s} {k[1]:12s} {c[k]}")
    print(f"   TOTAL ops: {len(ops)}   notes: {len(notes)}")
    for n in notes[:25]:
        print(f"      note: {n}")
    if len(notes) > 25:
        print(f"      ... {len(notes)-25} more notes in the plan file")


if __name__ == "__main__":
    main()
