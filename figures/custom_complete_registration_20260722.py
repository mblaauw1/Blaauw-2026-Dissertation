"""custom_complete_registration_20260722.py — finish the registration so EVERY figure in copy.ai has a
complete PLOT_SETTINGS entry, including the timestrips and cell pictures.

User 2026-07-22: "everything should be registered, even the pictures of cells/timestrips".

The retroactive pass gave all 367 placed figures an entry but left caption/axes blank, because inventing
them is the failure that got four figures retired. This pass FILLS THEM FROM EVIDENCE, and records where
each value came from so a reader can tell a recovered fact from an authored one:

  DATA PLOTS
    axes are read out of the figure's OWN GENERATING CODE — the `set_xlabel` / `set_ylabel` / `set_title`
    calls in the script that draws it. That is what the figure actually says, not a reconstruction.
    If the script draws several figures and the labels are ambiguous, EVERY candidate is recorded and the
    entry stays incomplete rather than one being picked.
    Where no script is identified, the axes fall back to the recorded data CSV's own columns, tagged
    `axes_source: "data CSV columns"` so it is obvious the label was not read from the plotting code.

  IMAGE PANELS (timestrips, montages, contact sheets, MIPs, IF panels)
    these have no x/y, so "axes" is not the missing information — PROVENANCE is: which cell, which frames,
    which channel, at what magnification. Most already ship a panel-index CSV recording exactly that
    (batch, source_tif, role, frame_idx, t_sec, channel_labels, pixel_um, scalebar_um), so the description
    is assembled from those fields verbatim. Panels with no index CSV get the image's real pixel
    dimensions and its generating script instead.

Nothing here overwrites an entry written by lib.record_plot at build time.
"""
import sys; sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import csv, json, os, re, glob, shutil

PS = "/Volumes/4 MB/ablation_plots/PLOT_SETTINGS.json"
DATA = "/Volumes/4 MB/ablation_plots/data"
ROOT = "/Volumes/4 MB/ablation_figures_20260625"
CODE = "/Volumes/4 MB/ablation_plots/code"

LBL = re.compile(r"""set_(xlabel|ylabel|title)\s*\(\s*(?:f?["'])(.*?)["']""", re.S)
SUP = re.compile(r"""suptitle\s*\(\s*(?:f?["'])(.*?)["']""", re.S)


def script_path(entry):
    c = entry.get("code") or ""
    if not c:
        return None
    for p in (os.path.join(CODE, c), os.path.join(ROOT, c)):
        if os.path.isfile(p):
            return p
    return None


def labels_from_code(p):
    """Every axis label / title the script sets, de-duplicated in order of appearance."""
    try:
        t = open(p, encoding="utf-8", errors="replace").read()
    except Exception:
        return {}
    out = {"xlabel": [], "ylabel": [], "title": []}
    for kind, txt in LBL.findall(t):
        k = {"xlabel": "xlabel", "ylabel": "ylabel", "title": "title"}[kind]
        txt = txt.strip()
        if txt and txt not in out[k]:
            out[k].append(txt)
    for txt in SUP.findall(t):
        txt = txt.strip()
        if txt and txt not in out["title"]:
            out["title"].append(txt)
    return out


def panel_description(stem):
    """Assemble a factual description of an image panel from its recorded panel-index CSV."""
    p = f"{DATA}/{stem}.csv"
    if not os.path.isfile(p):
        return None
    try:
        rows = list(csv.DictReader(open(p, encoding="utf-8", errors="replace")))
    except Exception:
        return None
    if not rows:
        return None
    g = lambda k: [(r.get(k) or "").strip() for r in rows if (r.get(k) or "").strip()]
    batches = sorted(set(g("batch")))
    roles = sorted(set(g("role")))
    chans = sorted(set(g("channel_labels")))
    px = sorted(set(g("pixel_um")))
    sb = sorted(set(g("scalebar_um")))
    ts = [float(x) for x in g("t_sec") if re.match(r"^-?\d+(\.\d+)?$", x)]
    bits = [f"{len(rows)} frame{'s' if len(rows) != 1 else ''}"]
    if batches:
        bits.append("cell " + (batches[0] if len(batches) == 1 else f"{len(batches)} cells"))
    if roles:
        bits.append("role " + "/".join(roles))
    if chans:
        bits.append("channel " + "/".join(chans))
    if ts:
        bits.append(f"t {min(ts):.0f}–{max(ts):.0f} s")
    if px:
        bits.append(f"pixel {px[0]} µm")
    if sb:
        bits.append(f"scalebar {sb[0]} µm")
    return {"text": "Image panel — " + ", ".join(bits) + ".",
            "batches": batches, "roles": roles, "channels": chans,
            "n_frames": len(rows),
            "t_sec_range": [min(ts), max(ts)] if ts else None,
            "pixel_um": px[0] if px else None, "scalebar_um": sb[0] if sb else None}


def image_dims(stem, placed_file):
    for cand in [placed_file] + [f"{ROOT}/{g}/{stem}.png" for g in
                                 ("group1", "group2", "group3", "group4", "group5", "")]:
        if cand and os.path.isfile(cand) and cand.lower().endswith(".png"):
            try:
                import struct
                raw = open(cand, "rb").read(29)
                w, h = struct.unpack(">II", raw[16:24])
                return {"file": cand, "pixels": [w, h], "bytes": os.path.getsize(cand)}
            except Exception:
                pass
    return None


def main():
    ps = json.load(open(PS))
    shutil.copy2(PS, PS.replace(".json", "_pre_complete_20260722.json"))
    done_dp = done_img = amb = 0
    still = []

    for stem, v in ps.items():
        if not isinstance(v, dict) or v.get("provenance_complete") is not False:
            continue
        st = v.get("settings") or {}
        kind = st.get("kind")

        if kind == "image_panel":
            desc = panel_description(stem)
            if desc:
                v["caption"] = desc.pop("text")
                st.update(desc)
                st["axes"] = "n/a — image panel"
                v["caption_source"] = "assembled from the recorded panel-index CSV fields"
                v["provenance_complete"] = True
                done_img += 1
            else:
                dims = image_dims(stem, (v.get("placed_in_deck") or {}).get("file"))
                sp = script_path(v)
                if dims:
                    st["image"] = dims
                    v["caption"] = (f"Image panel — {dims['pixels'][0]}x{dims['pixels'][1]} px"
                                    + (f", built by {os.path.basename(sp)}" if sp else "") + ".")
                    st["axes"] = "n/a — image panel"
                    v["caption_source"] = ("image dimensions read from the placed file"
                                           + ("; generating script identified" if sp else
                                              "; NO generating script identified"))
                    v["provenance_complete"] = bool(sp)
                    if sp:
                        done_img += 1
                    else:
                        still.append((stem, "image panel, no index CSV and no script"))
                else:
                    still.append((stem, "image panel, no index CSV and no readable image"))
            v["settings"] = st
            continue

        # ---- data plot: read the axes out of the code that draws it
        sp = script_path(v)
        lab = labels_from_code(sp) if sp else {}
        xs, ys, ts_ = lab.get("xlabel", []), lab.get("ylabel", []), lab.get("title", [])
        if sp and len(xs) == 1 and len(ys) == 1:
            st["x"] = xs[0]; st["y"] = ys[0]
            if ts_:
                st["title"] = ts_[0]
            st["axes"] = f"x = {xs[0]} | y = {ys[0]}"
            v["axes_source"] = f"read from set_xlabel/set_ylabel in {os.path.basename(sp)}"
            if not v.get("caption"):
                v["caption"] = ts_[0] if ts_ else f"{ys[0]} vs {xs[0]}"
                v["caption_source"] = v["axes_source"]
            v["provenance_complete"] = True
            done_dp += 1
        elif sp and (xs or ys):
            st["axes_candidates"] = {"xlabel": xs, "ylabel": ys, "title": ts_}
            st["axes"] = ("AMBIGUOUS — the script draws several figures; candidates recorded above, "
                          "none chosen")
            v["axes_source"] = f"candidates from {os.path.basename(sp)}"
            amb += 1
            still.append((stem, f"script draws {max(len(xs),len(ys))} figures — axes ambiguous"))
        else:
            cols = [c.strip() for c in (st.get("columns") or []) if c.strip() and c.strip() != "batch"]
            if len(cols) >= 2:
                st["axes"] = f"x = {cols[0]} | y = {cols[1]}   (from the data CSV columns, NOT the code)"
                v["axes_source"] = "data CSV columns — the plotting code was not identified"
                st["axes_confidence"] = "low"
            still.append((stem, "no generating script identified"))
        v["settings"] = st

    tmp = PS + ".tmp"
    json.dump(ps, open(tmp, "w"), indent=1)
    os.replace(tmp, PS)

    inc = [k for k, v in ps.items() if isinstance(v, dict) and v.get("provenance_complete") is False]
    print(f"completed this pass:  data plots {done_dp}   image panels {done_img}   ambiguous {amb}")
    print(f"PLOT_SETTINGS entries: {len(ps)}")
    print(f"complete provenance:   {len(ps)-len(inc)}")
    print(f"still incomplete:      {len(inc)}")
    for s, why in sorted(still)[:40]:
        print(f"   {s:52s} {why}")


if __name__ == "__main__":
    main()
