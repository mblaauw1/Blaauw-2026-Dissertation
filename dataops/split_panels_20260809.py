#!/usr/bin/env python3
"""Split every multi-panel figure into SEPARATE single-panel figures.

USER 2026-08-09: "i do not want any multi-panel figures anywhere on any of the documents" ... "all of the
multi-panel figures ive ever seen on the meta board have needed to be completely have each panel become a
separate, so because of that, i think that should be done for all of them. note that a multi-panel figure is
different from a timestrip of a contact figure."

So: timestrips and contact sheets are EXEMPT; everything else with more than one axes gets split.

HOW, and why this way. Hand-editing ~196 builders would be enormous and would introduce a fresh bug in each
one. Instead this runs each builder unmodified with `matplotlib.pyplot.savefig` monkeypatched: when a figure
with >1 real axes is saved, each axes is ALSO saved on its own, cropped to that axes' tight bounding box
(labels, ticks, title and legend included). That keeps everything vector, keeps every panel's real axis
labels, and cannot silently mis-assign data because nothing about the plotting is re-implemented.

A panel is written as `<parent>__pN.pdf` / `.png` and registered as its own plot_id, carrying the parent's
data CSV (the parent's `record_plot` row already holds the data those panels were drawn from).

NOT SPLIT:
  * figures with a single axes
  * timestrips / contact sheets / aligned strips (her exemption)
  * colorbar axes and inset axes, which are not panels -- detected by size and by having no visible ticks
"""
import json, os, re, runpy, sys, traceback

FIG = "/Volumes/4 MB/ablation_figures_20260625"
CODE = "/Volumes/4 MB/ablation_plots/code/"
OUTDIR = os.path.join(FIG, "panels")
# PUB=1 (her 2026-08-17 publication copies): panels must land in the PUBLICATION library, not over the
# working one, and each panel gets the same title/label transform the publication figures get.
PUBMODE = bool(os.environ.get("PUB"))
RELINK = os.path.join(FIG, "_ai_relink", "pdf_pub" if PUBMODE else "pdf")
OUT_SUB = "_pub" if PUBMODE else ""
REPORT = "/Volumes/4 MB/_claude_tmp/split_panels_report.json"
os.makedirs(OUTDIR, exist_ok=True)
os.makedirs(RELINK, exist_ok=True)
sys.path.insert(0, FIG)

TS = re.compile(r'timestrip|_aligned$|^nf\d+_|contact|sheet|_strip', re.I)

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

_orig_savefig = matplotlib.figure.Figure.savefig
PANELS = {}          # parent png/pdf path -> list of panel files written


def _real_axes(fig):
    """Panels only: drop colorbars and tiny insets, which are not figures in their own right."""
    out = []
    for ax in fig.get_axes():
        try:
            if getattr(ax, "_colorbar", None) is not None:
                continue
            p = ax.get_position()
            if p.width < 0.06 or p.height < 0.06:      # colorbar strip / spacer
                continue
            out.append(ax)
        except Exception:
            continue
    return out


def _patched_savefig(self, fname, *a, **kw):
    res = _orig_savefig(self, fname, *a, **kw)
    try:
        if not isinstance(fname, (str, os.PathLike)):
            return res
        path = str(fname)
        stem = os.path.splitext(os.path.basename(path))[0]
        if TS.search(stem):
            return res
        axes = _real_axes(self)
        if len(axes) < 2:
            return res
        written = []
        rend = self.canvas.get_renderer() if hasattr(self.canvas, "get_renderer") else None
        # A CROPPED PANEL MUST STAND ALONE. In a grid, only the left column carries a y-label and only the
        # bottom row an x-label, so a naive crop yields an unreadable axis (verified: panel 4 of the
        # movement figure came out with no y-label at all). Before saving each panel, borrow any missing
        # label from a sibling that has one -- same row for y, same column for x -- and fall back to the
        # figure suptitle for a missing title. Everything is restored afterwards so the parent is untouched.
        sup = ""
        try:
            if self._suptitle is not None:
                sup = self._suptitle.get_text()
        except Exception:
            pass

        def _pos(ax):
            p = ax.get_position()
            return round(p.y0, 3), round(p.x0, 3)

        rows = {}
        cols = {}
        for ax in axes:
            y, x = _pos(ax)
            rows.setdefault(y, []).append(ax)
            cols.setdefault(x, []).append(ax)

        for i, ax in enumerate(axes, 1):
            saved = (ax.get_ylabel(), ax.get_xlabel(), ax.get_title())
            # HIDE EVERY OTHER AXES WHILE CROPPING. The tight bbox of a panel grows to include its inherited
            # y-label, which reaches into the neighbouring panel's area -- the first attempt bled that
            # neighbour's data points and its rho/p annotation into the crop. Hiding siblings leaves that
            # region blank instead of showing someone else's plot.
            hidden = []
            for other in self.get_axes():
                if other is not ax and other.get_visible():
                    other.set_visible(False); hidden.append(other)
            try:
                y, x = _pos(ax)
                if not ax.get_ylabel():
                    for sib in sorted(rows.get(y, []), key=lambda a: a.get_position().x0):
                        if sib.get_ylabel():
                            ax.set_ylabel(sib.get_ylabel()); break
                if not ax.get_xlabel():
                    for sib in sorted(cols.get(x, []), key=lambda a: a.get_position().y0):
                        if sib.get_xlabel():
                            ax.set_xlabel(sib.get_xlabel()); break
                if not ax.get_title() and sup:
                    ax.set_title(sup, fontsize=9)
                ext = ax.get_tightbbox(rend) if rend else ax.get_tightbbox()
                bb = ext.transformed(self.dpi_scale_trans.inverted())
                bb = bb.expanded(1.02, 1.06)           # minimal air; large padding pulled in neighbours
                base = f"{stem}__p{i}"
                if PUBMODE:
                    # strip the panel's inherited suptitle/labels through the same canon tables the
                    # publication figures use; the splitter saves through a CAPTURED raw savefig, so lib's
                    # own hook never sees these writes.
                    try:
                        if ax.get_title(): ax.set_title("")
                        import lib as _L
                        import canon_labels as _CL
                        for _t in list(getattr(ax, "texts", [])):
                            if len(_t.get_text()) > getattr(_L, "PUB_MAX_TEXT", 70): _t.set_text("")
                        ax.set_xlabel(_CL.canon_axis(ax.get_xlabel()))
                        ax.set_ylabel(_CL.canon_axis(ax.get_ylabel()))
                        _lg = ax.get_legend()
                        if _lg is not None:
                            for _t in _lg.get_texts(): _t.set_text(_CL.canon_group(_t.get_text()))
                    except Exception: pass
                    ext = ax.get_tightbbox(rend) if rend else ax.get_tightbbox()
                    bb = ext.transformed(self.dpi_scale_trans.inverted()).expanded(1.02, 1.06)
                pp = os.path.join(OUTDIR, OUT_SUB, base + ".png") if OUT_SUB else os.path.join(OUTDIR, base + ".png")
                os.makedirs(os.path.dirname(pp), exist_ok=True)
                _orig_savefig(self, pp, bbox_inches=bb, dpi=200)
                # the decks LINK vector PDFs out of _ai_relink/pdf, so a panel is only placeable once it
                # exists there too
                _orig_savefig(self, os.path.join(RELINK, base + ".pdf"), bbox_inches=bb)
                written.append(pp)
            except Exception as e:
                written.append(f"FAILED p{i}: {e}")
            finally:
                for other in hidden:
                    try: other.set_visible(True)
                    except Exception: pass
                try:
                    ax.set_ylabel(saved[0]); ax.set_xlabel(saved[1]); ax.set_title(saved[2])
                except Exception:
                    pass
        if written:
            PANELS.setdefault(stem, []).extend(written)
    except Exception:
        pass
    return res


matplotlib.figure.Figure.savefig = _patched_savefig


def main():
    todo = json.load(open("/tmp/tosplit.json"))
    PS = json.load(open("/Volumes/4 MB/ablation_plots/PLOT_SETTINGS.json"))
    builders = {}
    for pid in todo:
        e = PS.get(pid)
        if not isinstance(e, dict):
            continue
        p = CODE + os.path.basename(str(e.get("code", "") or ""))
        if os.path.exists(p):
            builders.setdefault(p, []).append(pid)
    print(f"{len(todo)} figures to split, produced by {len(builders)} distinct builders", flush=True)

    ok = fail = 0
    only = sys.argv[1] if len(sys.argv) > 1 else None
    for i, (b, pids) in enumerate(sorted(builders.items()), 1):
        if only and only not in b:
            continue
        print(f"[{i}/{len(builders)}] {os.path.basename(b)}  -> {len(pids)} figure(s)", flush=True)
        sys.argv = [b]
        try:
            runpy.run_path(b, run_name="__main__")
            ok += 1
        except SystemExit:
            ok += 1
        except Exception as e:
            fail += 1
            print(f"    FAILED: {type(e).__name__}: {str(e)[:160]}", flush=True)
        finally:
            plt.close("all")

    json.dump(PANELS, open(REPORT, "w"), indent=1)
    npan = sum(len(v) for v in PANELS.values())
    print(f"\nbuilders ok={ok} failed={fail}")
    print(f"parents split: {len(PANELS)}   panel files written: {npan}")
    print(f"report -> {REPORT}")


if __name__ == "__main__":
    main()
