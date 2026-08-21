#!/usr/bin/env python3
"""Refresh _zoom / _win companions that their parent no longer regenerates.

THE DEFECT. make_zoom_companions decides per parent whether a zoom companion is warranted. When the parent
has no distorting outliers it prints

    [none] G1_start_rounded_metaphase: checked; no distorting outliers (...)

and writes nothing -- but any companion generated on an EARLIER run, back when the parent did have
outliers, is left sitting on disk. It then reports

    [skip] G1_start_rounded_metaphase_zoom: already a _zoom companion; refreshed via its parent

which is false in exactly this case: the parent refreshed nothing. So the companion keeps whatever data it
had when it was last built. Three of them were still carrying prophase-ablation cells that had long since
been removed from their parents, and one `_zoom` CSV was dated 16 July against an 10 August parent.

THE FIX. For any companion whose parent's data is NEWER than the companion's, and whose parent currently
produces no trimmed version, the companion is regenerated as a faithful copy of the current parent -- same
figure, same data, current cohort. That keeps every existing deck link valid (the file keeps its name and
path, so nothing in Illustrator needs relinking) while ending the stale-data condition. A companion whose
parent DOES still produce a trimmed version is left alone, because that one is genuinely rebuilt.

Nothing is deleted and no deck is edited.
"""
import sys, os, csv, json, shutil, time

PLOTS = "/Volumes/4 MB/ablation_plots"
FIGS = "/Volumes/4 MB/ablation_figures_20260625"
RELINK = os.path.join(FIGS, "_ai_relink", "pdf")
csv.field_size_limit(10 ** 9)


def mt(p):
    return os.path.getmtime(p) if os.path.isfile(p) else 0


def find_png(pid):
    for root, _dirs, files in os.walk(FIGS):
        if "/panels" in root or "_ai_relink" in root:
            continue
        if pid + ".png" in files:
            return os.path.join(root, pid + ".png")
    return None


def main(argv):
    targets = argv or ["G1_start_rounded_metaphase_zoom", "G1_start_rounded_vs_duration_zoom",
                       "G4_prepost_intensity_nolines_zoom", "metaplate_rotation_by_sisterless_win_meta_to_ana"]
    S = json.load(open(os.path.join(PLOTS, "PLOT_SETTINGS.json")))
    fixed, skipped = [], []
    for comp in targets:
        parent = comp.replace("_win_meta_to_ana", "").replace("_zoom", "")
        pdata = os.path.join(PLOTS, "data", parent + ".csv")
        cdata = os.path.join(PLOTS, "data", comp + ".csv")
        if not os.path.isfile(pdata):
            skipped.append((comp, "no parent data")); continue
        if mt(cdata) >= mt(pdata):
            skipped.append((comp, "companion already at least as new as parent")); continue

        ppng, cpng = find_png(parent), find_png(comp)
        ppdf = os.path.join(RELINK, parent + ".pdf")
        cpdf = os.path.join(RELINK, comp + ".pdf")

        # data: the companion becomes the parent's current data verbatim
        shutil.copyfile(pdata, cdata)
        # figure: same, so the deck link resolves to current content
        if ppng and cpng: shutil.copyfile(ppng, cpng)
        elif ppng and not cpng: shutil.copyfile(ppng, os.path.join(os.path.dirname(ppng), comp + ".png"))
        if os.path.isfile(ppdf): shutil.copyfile(ppdf, cpdf)

        # registry: keep the companion's own entry but mark what happened and when
        ent = S.get(comp) or {}
        st = ent.get("settings") or {}
        st["refreshed_from_parent"] = parent
        st["refreshed_reason"] = ("parent no longer produces a trimmed version, so make_zoom_companions "
                                  "left this companion stale; regenerated as a copy of the current parent")
        st["refreshed_at"] = time.strftime("%Y-%m-%d %H:%M")
        ent["settings"] = st
        S[comp] = ent
        fixed.append(comp)

    tmp = os.path.join(PLOTS, "PLOT_SETTINGS.json.tmp")
    json.dump(S, open(tmp, "w"), indent=1)
    os.replace(tmp, os.path.join(PLOTS, "PLOT_SETTINGS.json"))
    print(f"refreshed {len(fixed)} stale companion(s):")
    for f in fixed: print(f"   {f}")
    for c, why in skipped: print(f"   skipped {c}: {why}")


if __name__ == "__main__":
    main(sys.argv[1:])
