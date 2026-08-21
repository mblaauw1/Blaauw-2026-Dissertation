#!/usr/bin/env python3
"""Regenerate the JSON inputs that the deck JSX passes consume.

WHY THIS EXISTS (2026-07-29b): DECK_TITLES_SIG_FAMILY_20260729.jsx, PLACE_ZOOMS_BESIDE_PARENT_20260729.jsx,
MOVE_RETIRED_20260729.jsx and DUMP_ARTBOARDS_20260729.jsx all read their inputs from JSON files that a
previous session wrote with inline code that was never saved, into a /private/tmp scratchpad belonging to a
session that has since ended. That breaks the never-save-locally rule and put the whole deck-mark step one
/private/tmp clean away from being unreproducible. The files have been copied to /Volumes/4 MB/_working/_deck_jsx_inputs
and every JSX/py path repointed there; this script regenerates the ones whose rule is DOCUMENTED.

RULES, and where each is documented — none of this is inferred:
  retired.json   Figures that must never be highlighted and that carry the red RETIRED brand.
                 = {figures whose artboard is AB23} UNION {PLOT_SETTINGS entries flagged "retired"}.
                 Sources: handoff-8 §5 "Retired figures moved, never deleted - they go to AB23";
                 §3.9 "All 44 figures on the retired artboard branded"; the five mark conventions,
                 "red ... Used ONLY on the retired artboard".
                 VERIFIED: this reproduces the existing retired.json exactly (42 names, 0 differences).
  sig_place.json The yellow SIG_HIGHLIGHT list.
                 = every key of the significance scan, MINUS retired.
                 Sources: memory/feedback_copyai_significance_highlights - "for each PLACED plot's data CSV,
                 test Mann-Whitney/Kruskal on EVERY grouping x numeric metric AND Spearman on EVERY numeric
                 column pair; flag p<0.05 ... EXCLUDE retired plots from highlighting"; the scan itself
                 (dataops/sig_scan_20260729.py) already restricts to placed figures and already strips
                 statgrid/sanitycheck/mechanical pairs, so no further filtering belongs here.
                 VERIFIED: the existing sig_place.json is a strict subset of what this rule produces; the
                 difference is exactly the figures that only became significant in the newer scan.

  families.json  The grey FAMILY_GROUP blocks - "versions of the same data". RULE RECOVERED 2026-07-29b by
                 enumerating every parent/member pair in the existing file, which uses exactly nine suffixes
                 and no others: _zoom (63 pairs), _aligned (18), _trendscaled (13), _journal (12), _meta (4),
                 _metaphase (3), _scaled01 (3), _ecdf (2), _nolines (1). Two properties of the real rule that
                 the JSX header does not spell out:
                   * exactly ONE suffix is stripped, and only when the stripped name is ITSELF a placed
                     figure. That is why G2_dur_align_to_meta and G2_dur_neb_to_meta stay standalone (there
                     is no G2_dur_align_to figure) while G1_area_combined_meta is folded into
                     G1_area_combined.
                   * a figure can be BOTH a member of its parent's family and the parent of its own -
                     G1_area_combined_meta is a member of G1_area_combined AND the parent of
                     G1_area_combined_meta_trendscaled. The grey blocks are bounding boxes, so they nest.
                 ANSWERING THE QUESTION THIS FILE USED TO ASK: `_meta` IS a family variant. The existing
                 families.json pairs G1_area_combined with G1_area_combined_meta itself.
                 This rule reproduces 95 of the 99 existing groups exactly and - the part that makes it safe
                 to adopt - produces NO group that contradicts the old file: every one of the 99 is present,
                 26 more real families are added that the old file simply MISSED (G4_oscillation +
                 G4_oscillation_zoom on the same artboard AB14, the whole G6trk_* and G5shape_* sets from
                 the empty-data-table fix, G4_velocity, G4_distance_vs_fluor, ...), and 4 groups gain a
                 _zoom member the old file had dropped. Same-artboard was tested as a possible extra
                 constraint and REJECTED: it makes the match worse (60 of 99), and G4_oscillation and its
                 zoom are on the same artboard anyway.

NOT REGENERATED HERE, on purpose:
  deck_titles.json  has its own generator - dataops/build_deck_titles_20260729.py
  artboards.json    is dumped from the live .ai by DUMP_ARTBOARDS_20260729.jsx
  place_zooms.json  the companions to place beside their parent. The current file lists 7 window companions
                    and there are now 11, so it needs rebuilding - but "not yet beside its parent" is a
                    question about deck GEOMETRY (are the two frames adjacent?), which only DUMP_ARTBOARDS
                    can answer, and the artboards.json dump records the artboard but not the bounding box.
                    Left alone until the next Illustrator pass can re-dump geometry.

  python3 build_deck_jsx_inputs_20260729.py           # regenerate retired + sig_place + families
  python3 build_deck_jsx_inputs_20260729.py --check   # report what would change, write nothing
"""
import collections
import json, os, sys

ROOT = "/Volumes/4 MB"
# the nine suffixes the existing families.json actually uses, most-common first
FAMILY_SUFFIXES = ["_zoom", "_aligned", "_trendscaled", "_journal", "_meta",
                   "_metaphase", "_scaled01", "_ecdf", "_nolines"]
OUTDIR = os.path.join(ROOT, "_deck_jsx_inputs")
SIG_LIST = os.path.join(ROOT, "_sig_highlight_list_20260729.json")
CHECK = "--check" in sys.argv


def load(p):
    with open(p) as f:
        return json.load(f)


def write(name, obj):
    p = os.path.join(OUTDIR, name)
    old = load(p) if os.path.isfile(p) else None
    if old == obj:
        print(f"  {name}: unchanged ({len(obj)} entries)")
        return
    if old is not None:
        a, b = set(old), set(obj)
        print(f"  {name}: {len(old)} -> {len(obj)}  (+{len(b - a)} / -{len(a - b)})")
        for n in sorted(a - b)[:6]:
            print(f"      - {n}")
        for n in sorted(b - a)[:6]:
            print(f"      + {n}")
        if isinstance(obj, dict):     # a dropped MEMBER is as much a change as a dropped group
            changed = [k for k in a & b if sorted(old[k]) != sorted(obj[k])]
            for k in changed[:6]:
                print(f"      ~ {k}: {sorted(old[k])} -> {sorted(obj[k])}")
            if changed:
                print(f"      ({len(changed)} groups changed membership)")
    if CHECK:
        return
    if old is not None:                       # back up before overwriting, then write
        with open(p + ".bak", "w") as f:
            json.dump(old, f, indent=1)
    tmp = p + ".tmp"
    with open(tmp, "w") as f:
        json.dump(obj, f, indent=1)
    os.replace(tmp, p)


os.makedirs(OUTDIR, exist_ok=True)
artboards = load(os.path.join(OUTDIR, "artboards.json"))
settings = load(os.path.join(ROOT, "ablation_plots/PLOT_SETTINGS.json"))
sig = load(SIG_LIST)

retired = sorted({f for f, ab in artboards.items() if ab == "AB23"} |
                 {k for k, v in settings.items() if isinstance(v, dict) and v.get("retired")})
sig_place = sorted(set(sig) - set(retired))

groups = collections.defaultdict(set)
for fig in artboards:
    for suf in FAMILY_SUFFIXES:
        if fig.endswith(suf):
            parent = fig[:-len(suf)]
            if parent in artboards:          # only fold when the parent is itself a placed figure
                groups[parent].update((parent, fig))
            break                            # strip ONE suffix, not a chain
families = {p: sorted(v) for p, v in sorted(groups.items())}

print(f"artboards {len(artboards)} figures · PLOT_SETTINGS {len(settings)} entries · "
      f"significance scan {len(sig)} figures")
write("retired.json", retired)
write("sig_place.json", sig_place)
write("families.json", families)
print("place_zooms.json left untouched — needs deck geometry; see this file's docstring.")
