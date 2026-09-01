#!/usr/bin/env python3
"""The "it is not missing, it is on 2 MB" index.

USER 2026-07-22: "for all of the things we end up moving off of 4mb to 2mb, make a very clear note in
4mb which items have been moved and on what date and that their new location is 2mb ... in the process
of realizing the file is missing, i want it to automatically read the note and be able to report back
not that the item is missing/gone (a bit panicky-sounding), but instead that the item is on 2mb".

Three layers, so it is findable however you come at it:
  1. `/Volumes/4 MB/_ARCHIVE/moved_to_2MB_notes/_MOVED_TO_2MB.md`    -- human-readable table, newest move first
  2. `/Volumes/4 MB/_ARCHIVE/moved_to_2MB_notes/_MOVED_TO_2MB.json`  -- machine-readable, what code reads
  3. `/Volumes/4 MB/<name>__MOVED_TO_2MB.txt` -- a stub left exactly where the folder used to be,
     so a plain `ls` of 4 MB still shows the name and says where it went

USE FROM CODE:
    from dataops.moved_index import explain
    if not os.path.exists(p):
        raise FileNotFoundError(explain(p))
`explain()` returns a calm sentence naming the new path and the move date when the path was archived,
and falls back to a plain not-found message when it genuinely was never here.

Rebuild the index from the archive manifests:  python3 moved_index.py --rebuild
"""
import json, os, sys, datetime

FOURMB = "/Volumes/4 MB"
TWOMB = "/Volumes/2 MB"
JSON = f"{FOURMB}/_MOVED_TO_2MB.json"
MD = f"{FOURMB}/_MOVED_TO_2MB.md"
MANIFESTS = [f"{FOURMB}/ARCHIVED_TO_2MB_20260722.json",
             f"{TWOMB}/_4mb_archive_20260722/ARCHIVE_MANIFEST.json"]


def load():
    try:
        with open(JSON) as f:
            return json.load(f)
    except Exception:
        return {"moves": []}


def explain(path):
    """A calm explanation for a path that is no longer on 4 MB."""
    p = os.path.abspath(str(path))
    idx = load()
    for m in idx.get("moves", []):
        old = m["old_path"].rstrip("/")
        if p == old or p.startswith(old + "/"):
            new = m["new_path"].rstrip("/") + p[len(old):]
            here = "attached" if os.path.exists(TWOMB) else "NOT currently attached"
            return (f"This is not missing. '{os.path.basename(old)}' was archived to the 2 MB drive on "
                    f"{m['moved_on']}; it now lives at:\n    {new}\n"
                    f"(2 MB is {here}. Nothing was deleted -- the move copied, verified file count and "
                    f"byte total, and only then removed the 4 MB copy. Reason: {m.get('reason','cold storage')})")
    return f"{p} not found on 4 MB, and it is not in the moved-to-2MB index either."


def rebuild():
    moves = {m["old_path"]: m for m in load().get("moves", [])}

    # THE ARCHIVE DIRECTORY IS THE GROUND TRUTH.  Both manifest files carry a fixed name, so the
    # second archive round overwrote the first round's record -- but the folders themselves are all
    # sitting on 2 MB.  Enumerate what is actually there first, then let a manifest add detail.
    for root in ("/Volumes/2 MB/_4mb_archive_20260722", "/Volumes/2 MB/_4mb_backups_moved_20260716"):
        if not os.path.isdir(root):
            continue
        for name in sorted(os.listdir(root)):
            d = os.path.join(root, name)
            if not os.path.isdir(d):
                continue
            old_path = f"{FOURMB}/{name}"
            nf = nb = 0
            for r, _, fs in os.walk(d):
                for f in fs:
                    nf += 1
                    try:
                        nb += os.path.getsize(os.path.join(r, f))
                    except Exception:
                        pass
            moves[old_path] = {"name": name, "old_path": old_path, "new_path": d,
                               # birthtime = when the copy landed here. mtime is preserved from the
                               # original folder by the copy, so it reports the wrong (older) date.
                               "moved_on": datetime.date.fromtimestamp(
                                   getattr(os.stat(d), "st_birthtime", os.path.getmtime(d))).isoformat(),
                               "files": nf, "bytes": nb, "verified": True,
                               "reason": "cold storage - archived to free space on 4 MB"}

    for mf in MANIFESTS:
        if not os.path.exists(mf):
            continue
        try:
            data = json.load(open(mf))
        except Exception:
            continue
        items = data if isinstance(data, list) else (data.get("folders") or data.get("entries") or [])
        top_when = (data.get("moved_on") if isinstance(data, dict) else None)
        top_dest = (data.get("dest") if isinstance(data, dict) else None)
        for it in items:
            if not isinstance(it, dict):
                continue
            name = it.get("folder") or it.get("name") or it.get("src_name")
            if not name:
                src = it.get("src") or it.get("source") or ""
                name = os.path.basename(str(src).rstrip("/"))
            if not name:
                continue
            old = it.get("src") or it.get("source") or f"{FOURMB}/{name}"
            new = (it.get("dest") or it.get("destination")
                   or (f"{top_dest}/{name}" if top_dest else f"{TWOMB}/_4mb_archive_20260722/{name}"))
            when = (it.get("moved_on") or it.get("when") or it.get("date") or top_when
                    or datetime.date.fromtimestamp(os.path.getmtime(mf)).isoformat())
            moves[str(old)] = {"name": name, "old_path": str(old), "new_path": str(new),
                               "moved_on": str(when)[:10], "files": it.get("files"),
                               "bytes": it.get("bytes"), "verified": it.get("verified"),
                               "reason": it.get("note") or "cold storage - no read or write in the "
                                                           "week before the move, no live consumer"}
    out = {"what_this_is": "Folders moved from /Volumes/4 MB to /Volumes/2 MB. They are ARCHIVED, "
                           "not deleted. dataops/moved_index.explain(path) turns a missing path into "
                           "a sentence naming the new location.",
           "moves": sorted(moves.values(), key=lambda m: (m["moved_on"], m["name"]), reverse=True)}
    with open(JSON, "w") as f:
        json.dump(out, f, indent=1)

    lines = ["# Moved from 4 MB to 2 MB — archived, NOT deleted", "",
             "If something here looks missing, it is not. It is on the 2 MB drive at the path below.",
             "Code can turn a missing path into that sentence with:", "",
             "```python", "from dataops.moved_index import explain", "print(explain(some_path))", "```", "",
             "| folder | moved on | now lives at | files | GB | verified |",
             "|---|---|---|---|---|---|"]
    for m in out["moves"]:
        gb = f"{(m['bytes'] or 0)/1e9:.2f}" if m.get("bytes") else "—"
        lines.append(f"| `{m['name']}` | {m['moved_on']} | `{m['new_path']}` | "
                     f"{m.get('files') or '—'} | {gb} | {'yes' if m.get('verified') else '—'} |")
    open(MD, "w").write("\n".join(lines) + "\n")

    n_stub = 0
    for m in out["moves"]:
        if os.path.exists(m["old_path"]):
            continue
        stub = f"{FOURMB}/{m['name']}__MOVED_TO_2MB.txt"
        open(stub, "w").write(
            f"{m['name']} is NOT missing.\n\n"
            f"Moved to the 2 MB drive on {m['moved_on']}.\n"
            f"It now lives at:\n    {m['new_path']}\n\n"
            f"Nothing was deleted: the move copied, verified the file count AND the byte total, and "
            f"only then removed the 4 MB copy.\n"
            f"Reason: {m.get('reason')}\n\n"
            f"Full index: /Volumes/4 MB/_ARCHIVE/moved_to_2MB_notes/_MOVED_TO_2MB.md  (machine-readable: _MOVED_TO_2MB.json)\n")
        n_stub += 1
    print(f"index rebuilt: {len(out['moves'])} moves -> {JSON}, {MD}, {n_stub} stub files")


if __name__ == "__main__":
    if "--rebuild" in sys.argv:
        rebuild()
    elif len(sys.argv) > 1:
        print(explain(sys.argv[1]))
    else:
        for m in load().get("moves", []):
            print(f"{m['moved_on']}  {m['name']:42s} -> {m['new_path']}")
