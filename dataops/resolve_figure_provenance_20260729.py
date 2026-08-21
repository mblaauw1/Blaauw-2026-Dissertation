#!/usr/bin/env python3
"""Give every deck figure a traceable generating script (user 2026-07-29).

WHY: 97 figures placed in the two .ai decks had no usable provenance - `code` was empty, or the
retroactive placeholder "deck.py", or None. That is exactly the failure that let
`group4_lagging_examples` fall out of the frame-off-by-one re-run scope: a provenance lookup returned
nothing, so the script was never re-run while its figure stayed in the deck looking current.

METHOD: search EVERY .py under /Volumes/4 MB (figures dir, dataops, kt_outline, _scratch) for a
writer of each figure - `savefig(".../<name>.png")`, `record_plot("<name>"` or `save(fig, "<name>"`.
Report a unique hit, an ambiguous set, or nothing. Only entries with no usable provenance are
touched; an entry already naming a real script is left alone.

Writes `code` (the resolved script) and `provenance_resolved_20260729` (how it was found) into
PLOT_SETTINGS. It does NOT fabricate a code/ archive copy - that would imply the file is the code the
figure was actually built from, which is only true if the script is re-run through record_plot.

  python3 resolve_figure_provenance_20260729.py            # dry run
  python3 resolve_figure_provenance_20260729.py --apply
"""
import json, os, re, shutil, subprocess, sys, time, collections

ROOT = "/Volumes/4 MB"
PS = os.path.join(ROOT, "ablation_plots/PLOT_SETTINGS.json")
CODE = os.path.join(ROOT, "ablation_plots/code")
APPLY = "--apply" in sys.argv
SEARCH = ["ablation_figures_20260625", "dataops", "kt_outline", "_scratch", "ablation_plots"]

ps = json.load(open(PS))
have_code = {}
for f in os.listdir(CODE):
    m = re.match(r"(.+?)__(.+\.py)$", f)
    if m:
        have_code[m.group(1)] = m.group(2)

# ---- which figures does the deck actually place? ----
links = set()
for d in ["ablation_plots/_superseded_decks/ablation_figures_grouped copy.ai",
          "ablation_plots/_superseded_decks/ablation_figures_kinetochore_overflow.ai"]:
    out = subprocess.run(["strings", os.path.join(ROOT, d)], capture_output=True, text=True).stdout
    for m in re.findall(r"([A-Za-z0-9_.\-]+\.(?:pdf|png))", out):
        links.add(m.rsplit(".", 1)[0])


def usable(entry, base):
    """does this figure already have provenance we can act on?"""
    if base in have_code:
        return True
    c = str((entry or {}).get("code") or "").strip()
    return bool(c) and c.lower() not in ("none", "deck.py")


need = sorted(b for b in links if not usable(ps.get(b), b))
print("deck figures needing provenance: %d" % len(need))

# ---- index every python file once ----
files = []
for sub in SEARCH:
    p = os.path.join(ROOT, sub)
    if not os.path.isdir(p):
        continue
    for dirpath, _, names in os.walk(p):
        if "__pycache__" in dirpath:
            continue
        for n in names:
            if n.endswith(".py"):
                files.append(os.path.join(dirpath, n))
print("python files searched: %d" % len(files))

def is_archive(path):
    """archived copies are not the generator - they are snapshots OF the generator."""
    p = path.replace(os.sep, "/")
    return ("_builder_backup" in p or "/ablation_plots/code/" in p or "/_retired" in p
            or "/_superseded" in p or ".bak" in p)


src = {}
for f in files:
    if is_archive(f):
        continue
    try:
        src[f] = open(f, encoding="utf-8", errors="ignore").read()
    except Exception:
        pass
print("python files searched (archives excluded): %d" % len(src))


def direct_lookup(base):
    """find the script(s) that write this exact figure name."""
    esc = re.escape(base)
    pats = [(r'savefig\([^)]*?[\'"/]%s\.(?:png|pdf|svg)' % esc, "savefig"),
            (r'record_plot\(\s*[\'"]%s[\'"]' % esc, "record_plot"),
            (r'save\(\s*\w+\s*,\s*[\'"]%s[\'"]' % esc, "save()"),
            (r'[\'"]%s[\'"]' % esc, "name-literal")]
    for pat, how in pats:
        hits = collections.OrderedDict()
        for f, s in src.items():
            if re.search(pat, s):
                hits.setdefault(os.path.relpath(f, ROOT), how)
        if hits:
            return hits, how
    return collections.OrderedDict(), None


# suffix families: a variant is drawn by the SAME script as its parent, with different axes/style.
# handoff-4 section 6: "_zoom = same figure, tighter axes" and _journal = the same data drawn to
# lib.journal_violin conventions. So a variant inherits its parent's generator.
SUFFIXES = ["_journal_zoom", "_journal", "_zoom", "_aligned", "_nolines", "_scaled01", "_trendscaled"]


def parent_of(base):
    for s in SUFFIXES:
        if base.endswith(s) and len(base) > len(s):
            return base[: -len(s)]
    return None


# Programmatic names: these figures are written through an f-string (savefig(f"{OUT}/{name}.png")),
# so no string literal of the figure name exists anywhere to match. The generator is known from the
# naming family. Verified 2026-07-29 by reading each builder's savefig call.
FAMILY = [
    (r"^\d-sisterless", "ablation_figures_20260625/group_timestrips.py"),
    (r"^(double-chromosome|off-target|unmanipulated-control|polar|traced_cell)", "ablation_figures_20260625/group_timestrips.py"),
    (r"_frap0(_aligned)?$", "ablation_figures_20260625/group_frap_timestrips.py"),
    (r"^frap_candidates", "ablation_figures_20260625/build_frap_candidate_pages.py"),
    (r"_candidates(_\d+)?$", "ablation_figures_20260625/group_timestrips.py"),
    (r"^G4_lagging_examples", "ablation_figures_20260625/group4_lagging_examples.py"),
    (r"^G5_IF_", "ablation_figures_20260625/group5_if_timestrip.py"),
    (r"^collagenON_", "ablation_figures_20260625/custom_collagen_vs_triple_shape.py"),
    # custom_collagen_vs_triple_shape.py:155 -> f"collagen_vs_triple_{'roundness' if ... else 'area'}.png"
    (r"^collagen_vs_triple_", "ablation_figures_20260625/custom_collagen_vs_triple_shape.py"),
    (r"^G\d_.*timestrip", "ablation_figures_20260625/group_timestrips.py"),
    (r"^DEMO_.*timestrip", "ablation_figures_20260625/build_demo_timestrips.py"),
]


def family_lookup(base):
    for pat, script in FAMILY:
        if re.search(pat, base):
            if os.path.exists(os.path.join(ROOT, script)):
                return script
    return None


resolved, ambiguous, unresolved = {}, {}, []
for base in need:
    fam = family_lookup(base)
    if fam:
        resolved[base] = (fam, "programmatic filename (f-string); generator identified by naming family")
        continue
    hits, how = direct_lookup(base)
    if len(hits) == 1:
        resolved[base] = (next(iter(hits)), how)
        continue
    if not hits:
        # try the parent chain for _zoom / _journal / _aligned style variants
        chain, p = [], parent_of(base)
        while p and len(chain) < 4:
            chain.append(p)
            ph, phow = direct_lookup(p)
            if len(ph) == 1:
                resolved[base] = (next(iter(ph)),
                                  "inherited from parent '%s' via %s" % (p, phow))
                break
            if p in have_code:
                resolved[base] = ("ablation_figures_20260625/" + have_code[p],
                                  "inherited from parent '%s' (code/ archive)" % p)
                break
            p = parent_of(p)
        else:
            unresolved.append(base)
        if base not in resolved and base not in unresolved:
            unresolved.append(base)
        continue
    ambiguous[base] = hits

print()
print("  uniquely resolved : %d" % len(resolved))
print("  ambiguous (>1)    : %d" % len(ambiguous))
print("  unresolved        : %d" % len(unresolved))
for b, (f, how) in list(resolved.items())[:10]:
    print("     %-52s %-46s via %s" % (b, f, how))
if ambiguous:
    print("  ambiguous examples:")
    for b, h in list(ambiguous.items())[:6]:
        print("     %-52s %s" % (b, list(h)[:3]))
if unresolved:
    print("  unresolved: %s" % unresolved[:12])

if not APPLY:
    print("\nDRY RUN - nothing written. Re-run with --apply.")
    sys.exit(0)

bak = "%s.%s_pre_provenance.bak" % (PS, time.strftime("%Y%m%d_%H%M%S"))
shutil.copy2(PS, bak)
n = 0
for b, (f, how) in resolved.items():
    e = ps.setdefault(b, {})
    e["code"] = f
    e["provenance_resolved_20260729"] = ("resolved by searching every .py under /Volumes/4 MB for a "
                                         "writer of this figure; matched via %s" % how)
    n += 1
for b, h in ambiguous.items():
    e = ps.setdefault(b, {})
    e["provenance_resolved_20260729"] = "AMBIGUOUS - written by: %s" % ", ".join(list(h))
    n += 1
tmp = PS + ".tmp"
json.dump(ps, open(tmp, "w"), indent=1)
os.replace(tmp, PS)
chk = json.load(open(PS))
assert len(chk) >= len(ps), "entry count shrank"
print("\nAPPLIED provenance to %d entries; backup %s" % (n, os.path.basename(bak)))
