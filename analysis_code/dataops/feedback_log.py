#!/usr/bin/env python3
"""Rebuild the running feedback record. Run this after any working session.

    python3 dataops/feedback_log.py                 # refresh all three documents
    python3 dataops/feedback_log.py --todo          # just list items still needing an annotation

Produces, in 4_TABLES_AND_REPORTS/_feedback_log/ :
    FEEDBACK_VERBATIM.txt        every message she sent, word for word, with status annotations
    A_OFF_DECK_QUESTIONS.txt     the ones that produced an answer, not a deck edit
    B_DECK_FEEDBACK_STATUS.txt   the ones that changed (or should change) a figure

WHY THIS FILE EXISTS AND WHY IT IS KEYED THE WAY IT IS
-----------------------------------------------------
Her messages are recovered from the Claude Code session transcripts in
~/.claude/projects/-Users-mblaauw/*.jsonl, which persist on disk and survive /clear. That is the
only reason a verbatim record exists at all.

Annotations live in annotations.json, keyed by the message TIMESTAMP - never by position.  The
first version of this keyed on item number, which meant every new message she sent silently shifted
every annotation after it onto the wrong message. Timestamps are stable, so re-running only ever
ADDS unannotated items; it can never re-point an existing one.

Anything new is listed under NEEDS ANNOTATION at the top of the verbatim document and by --todo,
so an un-annotated item is visible rather than quietly missing.
"""
import argparse, datetime, glob, io, json, os, re, sys

SRC   = os.path.expanduser("~/.claude/projects/-Users-mblaauw")
DEST  = "/Volumes/4 MB/4_TABLES_AND_REPORTS/_feedback_log"
ANNF  = DEST + "/annotations.json"
SINCE = datetime.datetime(2026, 8, 16, 12, 0, 0)
W     = 100

NOISE = ("mcp__claude-in-chrome","ToolSearch with query","<command-name>","Caveat:","# Harness",
         "# Memory","persistent file-based memory","claudeMd","IMPORTANT: If the Chrome browser tools",
         "local-command-stdout","This is how Claude Code surfaces","[SYSTEM NOTIFICATION",
         "<system-reminder>","The following MCP servers","Available agent types","user-invocable skills",
         "Below is a summary of the conversation","tool_use_id")

MARK = {"H":"[####]","R":"[    ]","N":"[-  -]","X":"[XXXX]"}
LBL  = {"H":"HIGH RELEVANCE","R":"reference","N":"NO LONGER RELEVANT","X":"DETACHED TOPIC"}
WHY  = {"H":"bears on what you are doing NOW: Results section, paper figures, committee source data",
        "R":"still true, not urgent - background, or a screenshot sent with another message",
        "N":"superseded, or the thing it referred to no longer exists - do not act on it",
        "X":"nothing to do with the paper or this data"}

def harvest():
    out = []
    for p in glob.glob(SRC + "/*.jsonl"):
        if datetime.datetime.fromtimestamp(os.path.getmtime(p)) < SINCE - datetime.timedelta(days=1):
            continue
        for ln in io.open(p, encoding="utf-8", errors="replace"):
            ln = ln.strip()
            if not ln: continue
            try: d = json.loads(ln)
            except Exception: continue
            if d.get("type") != "user": continue
            m = d.get("message") or {}
            if m.get("role") != "user": continue
            c = m.get("content"); txt = ""
            if isinstance(c, str): txt = c
            elif isinstance(c, list):
                txt = "\n".join(b.get("text","") for b in c if isinstance(b, dict) and b.get("type") == "text")
            txt = (txt or "").strip()
            if not txt or txt.startswith("<") or any(n in txt for n in NOISE): continue
            ts = d.get("timestamp") or ""
            try: dt = datetime.datetime.fromisoformat(ts.replace("Z","+00:00")).replace(tzinfo=None)
            except Exception: dt = None
            if dt and dt < SINCE: continue
            out.append({"ts": ts, "text": txt, "sess": os.path.basename(p)[:8]})
    out.sort(key=lambda r: r["ts"])
    seen, uniq = set(), []
    for r in out:
        k = r["text"][:150]
        if k in seen: continue
        seen.add(k); uniq.append(r)
    return uniq

def wrap(t, ind=""):
    lines = []
    for para in t.split("\n"):
        if not para.strip(): lines.append(""); continue
        cur = ind
        for w in para.split(" "):
            if len(cur) + len(w) + 1 > W and cur.strip(): lines.append(cur.rstrip()); cur = ind + w + " "
            else: cur += w + " "
        lines.append(cur.rstrip())
    return "\n".join(lines)

def banner(f, title, sub, counts, extra=""):
    f.write("="*W + "\n" + title + "\n" + sub + "\n")
    f.write("rebuilt %s   -   python3 dataops/feedback_log.py\n" % datetime.date.today().isoformat())
    f.write("="*W + "\n\nRELEVANCE KEY - read the left column\n\n")
    for k in ("H","R","N","X"):
        f.write("  %-8s %-20s %s\n" % (MARK[k], LBL[k], WHY[k]))
    f.write("\n  " + "   ".join("%s %d" % (MARK[k], counts.get(k,0)) for k in ("H","R","N","X")) + "\n")
    if extra: f.write("\n" + extra + "\n")
    f.write("="*W + "\n")

_DECK_VERBS = ("make ", "add ", "remove", "delete", "fix ", "place", "redraw", "re-draw", "change",
               "extend", "relink", "swap", "scale down", "include", "update", "rebuild", "re-render",
               "rerender", "plot ", "annotate", "highlight", "move ", "dont ", "don't ", "do not ",
               "need to", "should ", "make sure", "ensure")
_DECK_NOUNS = ("figure", "plot", "artboard", "deck", "ai file", "timestrip", "legend", "table", "panel",
               "axis", "axes", "violin", "bar", "strip", "annotation")


def _infer_deck(text, entry):
    """Did this message ask for a CHANGE (goes in B), or ask a question that produced an answer (A)?

    2026-08-18, her correction: `deck` defaulted to False, so every annotation that did not set it
    explicitly landed in A - including plain instructions ("extend/add artboards", "redraw legend
    bullets"), which belong in B with a status.
    """
    t = (text or "").lower()
    note = ((entry.get("note") or "") + " " + (entry.get("status") or "")).lower()
    if entry.get("status") in ("STANDING RULE", "DO NOT REDO", "CORRECTED", "SUPERSEDED", "DECLINED"):
        return True
    verby = any(v in t for v in _DECK_VERBS)
    nouny = any(n in t for n in _DECK_NOUNS)
    asked = t.strip().endswith("?") or t.lstrip().startswith(("what", "why", "how", "is ", "are ", "do ",
                                                              "does ", "can ", "could ", "should i", "which"))
    if verby and nouny:
        return True
    if "done" in note and nouny:
        return True
    return not asked and verby


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--todo", action="store_true")
    a = ap.parse_args()

    os.makedirs(DEST, exist_ok=True)
    msgs = harvest()
    ann  = json.load(io.open(ANNF)) if os.path.exists(ANNF) else {}

    missing = [m for m in msgs if m["ts"] not in ann]
    print("%d messages since %s   |   annotated %d   |   NEEDS ANNOTATION %d"
          % (len(msgs), SINCE.date(), len(msgs) - len(missing), len(missing)))
    if a.todo or missing:
        for m in missing:
            print("   %s  %s" % (m["ts"][5:16].replace("T"," "), " ".join(m["text"].split())[:90]))
    if a.todo: return 0

    for m in msgs:
        e = ann.get(m["ts"]) or {}
        m["rel"]    = e.get("rel", "R")
        m["status"] = e.get("status", "")
        m["note"]   = e.get("note", "")
        # 2026-08-18, HER CORRECTION ("i dont know if youre keeping A and B fully updated"): `deck`
        # defaulted to FALSE, so every annotation that did not set it explicitly landed in A - including
        # plain instructions like "extend/add artboards" and "redraw legend bullets", which belong in B.
        # Infer it when it was not set: an INSTRUCTION (imperative, or a status that says something was
        # built/changed) goes to B; a question that produced an answer stays in A.
        m["deck"]   = bool(e["deck"]) if "deck" in e else _infer_deck(m["text"], e)
        m["new"]    = m["ts"] not in ann

    # ---------- verbatim, with annotations
    counts = {}
    for m in msgs: counts[m["rel"]] = counts.get(m["rel"], 0) + 1
    crit = [m for m in msgs if m["status"] in ("DO NOT REDO","SUPERSEDED","CORRECTED","DECLINED")]
    with io.open(DEST + "/FEEDBACK_VERBATIM.txt", "w", encoding="utf-8") as f:
        extra = ""
        if missing:
            extra = ("!! %d MESSAGE(S) NOT YET ANNOTATED - they appear below with no status. "
                     "Run: python3 dataops/feedback_log.py --todo" % len(missing))
        banner(f, "FEEDBACK FROM MADELINE - VERBATIM, WITH STATUS",
               "recovered from the session transcripts; these survive /clear", counts, extra)
        f.write("\nEvery message is exactly as she typed it. Annotations are mine, prefixed >>.\n")
        f.write("="*W + "\n\nREAD FIRST - %d ITEMS NO LONGER SAFE TO ACT ON AS WRITTEN\n\n" % len(crit))
        for m in crit:
            f.write("  [%s] %s\n" % (m["status"], m["ts"][5:16].replace("T"," ")))
            f.write(wrap(" ".join(m["text"].split())[:140] + "...", "      ") + "\n")
            f.write(wrap(">> " + m["note"], "      ") + "\n\n")
        f.write("="*W + "\nFULL RECORD\n" + "="*W + "\n")
        cur = None
        for m in msgs:
            if m["ts"][:10] != cur:
                cur = m["ts"][:10]; f.write("\n" + "-"*W + "\n" + cur + "\n" + "-"*W + "\n")
            f.write("\n%s %s" % (MARK[m["rel"]], m["ts"][11:16]))
            if m["status"]: f.write("   ---  %s" % m["status"])
            if m["new"]:    f.write("   *** NEEDS ANNOTATION ***")
            f.write("\n\n" + wrap(m["text"], "    ") + "\n")
            if m["note"]: f.write("\n" + wrap(">> " + m["note"], "    ") + "\n")
        f.write("\n" + "="*W + "\nEND - %d messages\n" % len(msgs) + "="*W + "\n")

    # ---------- A and B
    for fname, want, title, sub in (
        ("A_OFF_DECK_QUESTIONS.txt", False,
         "A - QUESTIONS THAT DID NOT CHANGE A FIGURE",
         "what you asked that produced an answer rather than a deck edit"),
        ("B_DECK_FEEDBACK_STATUS.txt", True,
         "B - FEEDBACK THAT CHANGED (OR SHOULD CHANGE) A FIGURE",
         "every instruction, with what actually happened to it")):
        sel = [m for m in msgs if m["deck"] == want]
        c = {}
        for m in sel: c[m["rel"]] = c.get(m["rel"], 0) + 1
        with io.open(DEST + "/" + fname, "w", encoding="utf-8") as f:
            banner(f, title, sub, c,
                   "STATUS: DONE / SUPERSEDED / DO NOT REDO / CORRECTED / STANDING RULE / ANSWERED / DECLINED"
                   if want else "")
            cur = None
            for m in sel:
                if m["ts"][:10] != cur:
                    cur = m["ts"][:10]; f.write("\n" + "-"*W + "\n" + cur + "\n" + "-"*W + "\n")
                f.write("\n%s %s" % (MARK[m["rel"]], m["ts"][11:16]))
                if m["status"]: f.write("   ---  %s" % m["status"])
                if m["rel"] in ("H","N","X"): f.write("   <<< %s" % LBL[m["rel"]])
                if m["new"]: f.write("   *** NEEDS ANNOTATION ***")
                f.write("\n")
                q = " ".join(m["text"].split())
                if q.startswith("[Image"): q = "(screenshot)"
                f.write(wrap("Q: " + q[:400], "       ") + "\n")
                if m["note"]: f.write(wrap("A: " + m["note"], "       ") + "\n")
            f.write("\n" + "="*W + "\nEND - %d items\n" % len(sel) + "="*W + "\n")
        print("wrote %s (%d items)" % (fname, len(sel)))
    print("wrote FEEDBACK_VERBATIM.txt (%d messages)" % len(msgs))
    return 0

if __name__ == "__main__":
    sys.exit(main())
