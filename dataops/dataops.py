"""dataops — the ONLY sanctioned way to modify annotation/master CSVs on /Volumes/4 MB.

Why this exists (2026-07-22): edits were being made by ad-hoc scripts. That produced, in one session:
  * a measured plate-join value (0:13:21 / 801 s / frame 116) deleted instead of superseded,
  * original hand-written `pairing_notes` overwritten instead of appended,
  * a correction applied to 12 rows when the user had named 3,
  * a master cell write that silently did not persist,
  * and (2026-07-20) 25 meta_plate frames dropped by a format conversion, undetected for two days.

Every one of those is prevented by a rule below. Do not bypass this module.

RULES ENFORCED
  R1 BACKUP-FIRST     every target is copied to _master_backups/<name>_pre_<tag>.csv before any write.
  R2 ATOMIC           write to .tmp then os.replace; never partial-write a live file.
  R3 VERIFY-BY-REREAD after writing, the file is re-read from disk and the change asserted. A write that
                      does not persist raises. (This is what silently failed on 2026-07-22.)
  R4 NO ROW LOSS      row count may only change if the caller passes expect_delta=<int>. Deleted rows must
                      be archived to _retired/ first.
  R5 NO SILENT VALUE DESTRUCTION
                      overwriting a NON-EMPTY cell with a different value requires reason=... ; overwriting
                      a MEASUREMENT column (see MEASURED) additionally requires allow_measurement_loss=True.
  R6 NOTES ARE APPEND-ONLY
                      free-text columns (see NOTE_COLS) are appended to, never replaced.
  R7 PROVENANCE       every change records who/why into _logs/dataops_audit.jsonl (append-only).
  R8 SCOPE            an edit applies to exactly the keys the caller lists. No pattern-based bulk edits.
"""
import csv, io, os, json, shutil, datetime

ROOT = "/Volumes/4 MB"
BACKUPS = f"{ROOT}/_master_backups"
RETIRED = f"{ROOT}/_retired"
AUDIT = f"{ROOT}/_logs/dataops_audit.jsonl"

# columns that hold a MEASUREMENT — destroying one of these needs an explicit override
MEASURED = {
    "length_um", "area_um2", "perimeter_um", "x", "y", "points", "kk_um",
    "chromosome_1_plate_join", "chromosome_2_plate_join", "chromosome_3_plate_join",
    "chromosome_1_plate_join_s", "chromosome_2_plate_join_s", "chromosome_3_plate_join_s",
    "chromosome_1_plate_join_frame", "chromosome_2_plate_join_frame", "chromosome_3_plate_join_frame",
    "chr1_length_um", "chr2_length_um", "chr3_length_um",
    "congression_time_s", "congression_hms", "Metaphase Start (s)", "Anaphase Onset (s)", "NEB Time (s)",
}
# free-text columns: append, never replace
NOTE_COLS = {"notes", "pairing_notes", "Notes", "annotation_notes", "Polar Comments", "Lagging Comments",
             "Exclude Reason", "behavior_raw"}


def _now():
    return datetime.datetime.now().isoformat(timespec="seconds")


def read(path):
    """read a CSV as (rows, header_index_map). Handles CR-only and non-UTF8 bytes."""
    t = open(path, encoding="utf-8", errors="replace").read().replace("\r\n", "\n").replace("\r", "\n")
    rows = list(csv.reader(io.StringIO(t)))
    if not rows:
        raise ValueError(f"empty file: {path}")
    return rows


def header_row(path, rows):
    """ABLATION_MASTER.csv has a 2-ROW header (real names on index 1). Everything else uses index 0."""
    return 1 if os.path.basename(path) == "ABLATION_MASTER.csv" else 0


def audit(entry):
    os.makedirs(os.path.dirname(AUDIT), exist_ok=True)
    with open(AUDIT, "a") as f:
        f.write(json.dumps(entry) + "\n")


def backup(path, tag):
    os.makedirs(BACKUPS, exist_ok=True)
    dst = f"{BACKUPS}/{os.path.basename(path).rsplit('.',1)[0]}_pre_{tag}.csv"
    shutil.copy2(path, dst)
    return dst


def retire(path, why, replaced_by=""):
    """R4: never delete a file — move it to _retired/ and record why."""
    os.makedirs(RETIRED, exist_ok=True)
    dst = f"{RETIRED}/{os.path.basename(path)}"
    shutil.move(path, dst)
    with open(f"{RETIRED}/README.md", "a") as f:
        f.write(f"| {_now()[:10]} | `{os.path.basename(path)}` | {why} | {replaced_by or 'nothing'} |\n")
    audit({"ts": _now(), "op": "retire", "path": path, "why": why})
    return dst


def apply_edits(path, key_cols, edits, tag, reason, expect_delta=0,
                allow_measurement_loss=False, dry_run=True):
    """Apply cell edits to `path`.

    key_cols  list of column NAMES forming the row key (e.g. ["batch","chr_num"])
    edits     {(key tuple): {column: new_value}}
    reason    free text -> audit log; REQUIRED
    dry_run   True (default) prints the diff and writes nothing.

    Returns the list of changes. Raises on any rule violation.
    """
    if not reason:
        raise ValueError("R7: reason is required")
    rows = read(path)
    hi = header_row(path, rows)
    hdr = [c.strip() for c in rows[hi]]
    ci = {c: i for i, c in enumerate(hdr)}
    for kc in key_cols:
        if kc not in ci:
            raise KeyError(f"key column {kc!r} not in {path}")
    n_before = len(rows)

    index = {}
    for r in rows[hi + 1:]:
        if not r or not any(x.strip() for x in r):
            continue
        index[tuple(r[ci[k]].strip() for k in key_cols)] = r

    changes, violations = [], []
    for key, cols in edits.items():
        key = tuple(str(k) for k in key)
        r = index.get(key)
        if r is None:
            violations.append(f"R8: key {key} not found in {os.path.basename(path)}")
            continue
        for col, new in cols.items():
            if col not in ci:
                violations.append(f"R8: column {col!r} not in {os.path.basename(path)}")
                continue
            i = ci[col]
            while len(r) <= i:
                r.append("")
            old = r[i]
            new = "" if new is None else str(new)
            if old == new:
                continue
            if col in NOTE_COLS and old.strip() and not new.startswith(old):
                violations.append(f"R6: {key} {col!r} is a notes column — use append_note(), not replace")
                continue
            if old.strip() and col in MEASURED and not allow_measurement_loss:
                violations.append(
                    f"R5: {key} {col!r} would destroy a MEASUREMENT {old!r} -> {new!r}; "
                    f"pass allow_measurement_loss=True and say why, or supersede it elsewhere")
                continue
            changes.append({"key": key, "col": col, "old": old, "new": new})
            if not dry_run:
                r[i] = new
    if violations:
        raise ValueError("REFUSED — rule violations:\n  " + "\n  ".join(violations))

    if dry_run:
        for c in changes:
            print(f"   DRY {c['key']} | {c['col']}: {c['old'][:50]!r} -> {c['new'][:50]!r}")
        print(f"   ({len(changes)} cell changes, nothing written)")
        return changes

    if len(rows) != n_before + expect_delta:
        raise ValueError(f"R4: row count {n_before} -> {len(rows)} (expected delta {expect_delta})")

    bk = backup(path, tag)
    tmp = path + ".tmp"
    with open(tmp, "w", newline="") as f:
        csv.writer(f).writerows(rows)
    os.replace(tmp, path)

    # R3 VERIFY BY RE-READ
    rows2 = read(path)
    hdr2 = [c.strip() for c in rows2[header_row(path, rows2)]]
    ci2 = {c: i for i, c in enumerate(hdr2)}
    idx2 = {}
    for r in rows2[header_row(path, rows2) + 1:]:
        if r and any(x.strip() for x in r):
            idx2[tuple(r[ci2[k]].strip() for k in key_cols)] = r
    bad = [c for c in changes if idx2[c["key"]][ci2[c["col"]]] != c["new"]]
    if bad:
        shutil.copy2(bk, path)
        raise RuntimeError(f"R3: {len(bad)} change(s) DID NOT PERSIST — file restored from {bk}")
    if len(rows2) != n_before + expect_delta:
        shutil.copy2(bk, path)
        raise RuntimeError("R4: row count changed on disk — file restored")

    audit({"ts": _now(), "op": "apply_edits", "path": path, "tag": tag, "reason": reason,
           "backup": bk, "n_changes": len(changes), "changes": changes})
    print(f"   APPLIED {len(changes)} changes to {os.path.basename(path)} (verified by re-read; backup {os.path.basename(bk)})")
    return changes


def append_note(path, key_cols, key, col, text, tag, reason, dry_run=True):
    """R6: append to a free-text column, preserving the original wording verbatim."""
    rows = read(path)
    hi = header_row(path, rows)
    ci = {c.strip(): i for i, c in enumerate(rows[hi])}
    key = tuple(str(k) for k in key)
    for r in rows[hi + 1:]:
        if r and tuple(r[ci[k]].strip() for k in key_cols) == key:
            i = ci[col]
            while len(r) <= i:
                r.append("")
            cur = r[i]
            if text in cur:
                print("   note already present, skipping")
                return []
            new = (cur + " || " if cur.strip() else "") + text
            return apply_edits(path, key_cols, {key: {col: new}}, tag, reason, dry_run=dry_run)
    raise KeyError(f"key {key} not found")
