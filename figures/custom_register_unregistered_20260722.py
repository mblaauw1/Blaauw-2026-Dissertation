"""custom_register_unregistered_20260722.py — give every figure placed in copy.ai a PLOT_SETTINGS entry.

WHY (user, 2026-07-22): "all figures on the ai doc should be registered".
copy.ai holds 367 distinct figures; only 217 were registered via lib.record_plot. The other 150 have no
PLOT_SETTINGS entry, so they carry no caption, no axis definition, no recorded statistics and no source
lineage. That is the exact exposure that got four figures retired: when nobody can say what an axis meant,
the definition ends up being GUESSED.

WHAT THIS DOES — AND WHAT IT DELIBERATELY DOES NOT DO
  It records, for every unregistered placed figure, only what can be ESTABLISHED FROM EVIDENCE:
      * the file actually placed in the deck, and its artboard
      * whether a per-batch data CSV exists, its columns and row count
      * the generating script, found by searching the figure-builder sources for the figure's name
      * source lineage (master + annotation stores) stamped AT REGISTRATION
      * a `kind`: "data_plot" if a per-batch CSV backs it, else "image_panel" (timestrips, contact sheets,
        MIPs, montages — pictures of cells, not plots of numbers)
  It does NOT invent a caption, axis labels, or statistics. Where those are unknown they are written as ""
  and the entry is flagged `provenance_complete: false`, so the gap is VISIBLE and countable instead of
  being filled with a plausible-sounding guess. A retroactive entry is also marked
  `registered_retroactively: true` so it can never be mistaken for one written by record_plot at build time
  (whose statistics were captured from the actual run).

  The distinction matters: `mtimes_at_registration` is NOT `mtimes_at_build`. It tells you the source state
  when the entry was created, not when the figure was made, so it cannot be used to prove the figure is
  in sync with its source. That is why it is given a different key name.

SAFETY
  PLOT_SETTINGS.json is backed up first. Existing entries are never modified — only missing ones are added.
"""
import sys; sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import csv, json, os, re, glob, hashlib, shutil, time

ROOT = "/Volumes/4 MB/ablation_figures_20260625"
PS = "/Volumes/4 MB/ablation_plots/PLOT_SETTINGS.json"
DATA = "/Volumes/4 MB/ablation_plots/data"
CODE = "/Volumes/4 MB/ablation_plots/code"
LINKS = "/Volumes/4 MB/ablation_plots/COPYAI_LINKS_20260722.txt"

SOURCES = ["/Volumes/4 MB/ABLATION_MASTER.csv",
           "/Volumes/4 MB/annotations/kt_points.csv",
           "/Volumes/4 MB/annotations/cell_outlines.csv",
           "/Volumes/4 MB/annotations/meta_plates.csv",
           "/Volumes/4 MB/annotations/CHROMOSOME_MASTER.csv"]

# Names that are pictures of cells rather than plots of numbers. Matches the IMG_ONLY spirit of
# verify_consistency.py, which deliberately does not demand a data CSV from these.
IMAGE_PAT = re.compile(r"timestrip|contactsheet|contact_sheet|montage|mip|zstack|_aligned|_notext|"
                       r"candidate|example|frap\d|_xy\d|statgrid", re.I)


def sha(p):
    try:
        h = hashlib.md5()
        with open(p, "rb") as f:
            for b in iter(lambda: f.read(1 << 20), b""):
                h.update(b)
        return h.hexdigest()
    except Exception:
        return None


def find_script(stem):
    """The generating script, found by searching the builder sources for the figure's own name."""
    hits = []
    for p in glob.glob(f"{ROOT}/*.py"):
        try:
            t = open(p, encoding="utf-8", errors="replace").read()
        except Exception:
            continue
        if stem in t:
            hits.append(os.path.basename(p))
    # an archived copy in ablation_plots/code is stronger evidence than a mention
    arch = [f for f in (os.listdir(CODE) if os.path.isdir(CODE) else []) if f.startswith(stem + "__")]
    return arch[0] if arch else (hits[0] if len(hits) == 1 else (hits[0] if hits else ""))


def csv_info(stem):
    p = f"{DATA}/{stem}.csv"
    if not os.path.isfile(p):
        return None
    try:
        with open(p, encoding="utf-8", errors="replace") as f:
            r = csv.reader(f)
            hdr = next(r, [])
            n = sum(1 for _ in r)
        return {"path": f"data/{stem}.csv", "columns": hdr, "n_rows": n,
                "key_column": "batch" if "batch" in [c.strip() for c in hdr] else None}
    except Exception:
        return None


def main():
    ps = json.load(open(PS))
    links = {}
    for line in open(LINKS, encoding="utf-8", errors="replace"):
        line = line.rstrip("\n")
        if not line.strip():
            continue
        parts = line.split("\t")
        if parts[0] == "EMBEDDED":
            continue
        stem = os.path.splitext(os.path.basename(parts[0]))[0]
        links.setdefault(stem, {"file": parts[0], "artboards": []})
        if len(parts) > 1:
            links[stem]["artboards"].append(parts[1])

    todo = [s for s in sorted(links) if s not in ps]
    print(f"placed distinct figures: {len(links)}   already registered: {len(links)-len(todo)}   "
          f"to register: {len(todo)}")
    if not todo:
        return

    bak = PS.replace(".json", f"_pre_retroreg_20260722.json")
    shutil.copy2(PS, bak)
    print(f"backup: {bak}")

    lineage = {"files": SOURCES,
               "mtimes_at_registration": {s: (round(os.path.getmtime(s), 1) if os.path.isfile(s) else None)
                                          for s in SOURCES},
               "hashes_at_registration": {s: sha(s) for s in SOURCES}}

    n_data, n_img, n_code = 0, 0, 0
    for stem in todo:
        info = csv_info(stem)
        is_img = info is None or IMAGE_PAT.search(stem)
        script = find_script(stem)
        if script:
            n_code += 1
        entry = {
            "caption": "",                       # NOT invented — unknown until a human records it
            "settings": {
                "kind": "image_panel" if is_img else "data_plot",
                "axes": "NOT RECORDED — this figure predates registration; do not infer them",
                "statistics": "NOT RECORDED",
                "columns": (info or {}).get("columns", []),
            },
            "n_rows": (info or {}).get("n_rows", None),
            "data": (info or {}).get("path", ""),
            "code": script,
            "source": dict(lineage, key_column=(info or {}).get("key_column")),
            "registered_retroactively": True,
            "registered_on": "2026-07-22",
            "placed_in_deck": {"file": links[stem]["file"], "artboards": sorted(set(links[stem]["artboards"]))},
            "provenance_complete": False,        # caption + axes + stats still missing
        }
        ps[stem] = entry
        if entry["settings"]["kind"] == "data_plot":
            n_data += 1
        else:
            n_img += 1

    tmp = PS + ".tmp"
    json.dump(ps, open(tmp, "w"), indent=1)
    os.replace(tmp, PS)
    print(f"registered {len(todo)}:  data_plot={n_data}  image_panel={n_img}  "
          f"generating script identified for {n_code}")
    print(f"PLOT_SETTINGS now holds {len(ps)} entries")

    incomplete = [k for k, v in ps.items() if isinstance(v, dict) and v.get("provenance_complete") is False]
    print(f"\nentries still missing caption/axes/statistics (need a human): {len(incomplete)}")
    dp = [k for k in incomplete if (ps[k].get('settings') or {}).get('kind') == 'data_plot']
    print(f"   of which are DATA PLOTS (the ones that actually matter): {len(dp)}")
    for k in sorted(dp)[:25]:
        print(f"      {k}")


if __name__ == "__main__":
    main()
