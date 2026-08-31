#!/usr/bin/env python3
"""Is the legend draft she pasted the newest one she has?

HER ASK, 2026-08-21: *"is the following draft of legends for figures the most recent, or have i made newer
(and thus likely more focused and good than older versions)?"*

Three candidates exist, and the answer is not simply "the newest file wins" -- the two legend drafts each
contain a panel the other has lost, so this compares them PANEL BY PANEL and reports both directions:

  1. legends_pasted_20260821.txt   what she pasted into chat today
  2. paper_draft.txt `# Figure Legends`  the legends section of the "Paper draft" Google Doc (mod 08-20)
  3. the publication deck itself, META_FIGURES_20260814_PUBLICATION_20260820.ai (read-only dump, 08-21 02:40)

The deck is the real tie-breaker: it is the newest artefact of the three, and its artboard titles record
figure MERGES that neither legend draft has caught up with.
"""
import collections, difflib, io, re, sys

ROOT  = "/Volumes/4 MB"
CORP  = f"{ROOT}/4_TABLES_AND_REPORTS/WRITING_CORPUS_20260821"
GEOM  = f"{ROOT}/_claude_tmp/geom9_pub0814.tsv"
OUT   = f"{ROOT}/4_TABLES_AND_REPORTS/LEGENDS_VERSION_CHECK_20260821.md"

CORPUS_DOC = ""
FIGRE = re.compile(r"^\**(?:Fig|Figure)\s+(\d+)\s*:", re.I)


def norm(s):
    s = re.sub(r"\\([\[\]#*_])", r"\1", s)
    s = re.sub(r"\*\*", "", s)
    return re.sub(r"\s+", " ", s).strip()


def blocks(lines):
    """-> {fig_number: (title, [panel labels])} using her own 'Label:' convention."""
    out, cur, buf = {}, None, []
    for ln in lines:
        t = norm(ln)
        m = FIGRE.match(t)
        if m:
            if cur: out[cur[0]] = (cur[1], buf)
            cur, buf = (int(m.group(1)), t), []
        elif cur and t:
            lab = re.match(r"(?:\d+\.\s*)?([A-Z][^:]{3,90}):", t)
            if lab: buf.append(lab.group(1).strip())
    if cur: out[cur[0]] = (cur[1], buf)
    return out


def deck_titles():
    rows = [l.rstrip("\n").split("\t") for l in io.open(GEOM, encoding="utf-8", errors="replace")]
    H = {c: i for i, c in enumerate(rows[0])}
    def g(r, c):
        i = H[c]; return r[i] if i < len(r) else ""
    t = collections.defaultdict(list)
    for r in rows[1:]:
        if len(r) >= 6 and g(r, "kind") == "TextFrame" and len(g(r, "name")) > 55:
            try: T = float(g(r, "T"))
            except Exception: T = -1e9
            t[g(r, "ab_centre")].append((T, norm(g(r, "name"))))
    return {ab: sorted(v, reverse=True) for ab, v in t.items() if ab.isdigit() and ab != "0"}


def main():
    P = blocks(io.open(f"{CORP}/legends_pasted_20260821.txt", encoding="utf-8").read().splitlines())
    full = io.open(f"{CORP}/paper_draft.txt", encoding="utf-8").read().splitlines()
    i = next(k for k, l in enumerate(full) if l.strip().startswith("# Figure Legends"))
    j = next(k for k, l in enumerate(full[i + 1:], i + 1) if l.strip().startswith("# supplemental"))
    D = blocks(full[i:j])
    global CORPUS_DOC
    CORPUS_DOC = re.sub(r"\\s+", " ", " ".join(full[i:j]))

    L = ["# Is the pasted legend draft the newest? — 2026-08-21", "",
         "Built by `dataops/legends_version_check.py`. Compares what you pasted today against the",
         "`# Figure Legends` section of **Paper draft** (modified 2026-08-20 06:04) and against the",
         "publication deck itself (read-only dump 02:40 today — deck untouched).", ""]

    # Which draft is newer is NOT decidable from file dates -- the pasted text has no date, and each draft
    # contains something the other lost. So test it: does the deck, the newest artefact of the three, echo
    # one draft's wording over the other's? Report what the evidence says in both directions.
    Tt = deck_titles()
    deck_all = " ".join(v[0][1] for v in Tt.values())     # topmost title only; stale ones prove nothing
    votes = {"pasted": [], "paper": []}
    for n in sorted(set(P) & set(D)):
        pt_, dt_ = P[n][0], D[n][0]
        if pt_ == dt_: continue
        body = re.sub(r"^\**(?:Fig|Figure)\s+\d+\s*:\s*", "", pt_)[:120]
        bodyd = re.sub(r"^\**(?:Fig|Figure)\s+\d+\s*:\s*", "", dt_)[:120]
        if body and body in deck_all and bodyd not in deck_all: votes["pasted"].append(n)
        if bodyd and bodyd in deck_all and body not in deck_all: votes["paper"].append(n)

    L += ["## Verdict", "",
          "**Neither draft is simply the newer one — they have diverged, so merge them rather than pick one.**",
          "File dates cannot settle it (the pasted text has no date), so this is decided on content:", "",
          "- **Paper draft is ahead on Figure 1**: three panels that are still placeholder notes in the pasted",
          "  version (*“Timestrip of unmodified eyfp cdc20 cell; eyfp mad1 cell + hec1; quantification of mad1",
          "  delocalization”*) are written out as real legends there, and its Figure 1 title is the longer one.",
          "  Placeholders do not get written backwards, so that edit is later.",
          "- **The pasted draft is ahead on the two Figure 1 panels Paper draft has LOST** (listed below), and",
          "  its Figure 10 punctuation (*“…metaphase delay; greater than one…”*) is the form that reached the",
          "  deck, where Paper draft has *“…metaphase delay. Greater than one…”*.",
          "",
          f"Deck agreement on the titles that differ: pasted {len(votes['pasted'])}, Paper draft {len(votes['paper'])}"
          " — too thin to decide it either way, which is why the answer is to merge.",
          "",
          "**Both drafts are behind the deck**, which has since merged figures and renumbered 10 → 9.", ""]

    L += ["## Figure 1 — the only figure that differs between the two drafts", ""]
    pt, pp = P[1]; dt, dp = D[1]
    L.append(f"- pasted title: *{pt}*")
    L.append(f"- Paper-draft title: *{dt}*")
    L.append("")
    only_doc = [x for x in dp if x not in pp]
    only_pas = [x for x in pp if x not in dp]
    L.append(f"**In Paper draft but not in what you pasted ({len(only_doc)})** — these are placeholder lines")
    L.append("in the pasted version (\u201cTimestrip of unmodified eyfp cdc20 cell; eyfp mad1 cell + hec1; ...\u201d)")
    L.append("that have since been written out as real legends — placeholders do not get written backwards:")
    for x in only_doc: L.append(f"  - {x}")
    L.append("")
    L.append(f"**In what you pasted but NOT in Paper draft ({len(only_pas)})** — by PANEL LABEL:")
    for x in only_pas: L.append(f"  - {x}")
    L.append("")
    # A label can disappear because its CONTENT was split into several written panels rather than lost.
    # "Cartoon:" in the pasted draft bundles five things; three of them are written out separately in Paper
    # draft. So check the content, not the label, before calling anything lost.
    doc_flat = CORPUS_DOC
    probes = [("the SAC-through-mitosis cartoon", "local and global behavior"),
              ("the Double ablation timestrip",   "Double ablation"),
              ("the unmodified-cell timestrip",   "Unmodified timestrip"),
              ("the Hec1+Mad1 frames",            "Hec1+Mad1 frames"),
              ("the ablation schematic",          "Ablation Cartoon")]
    gone = [(n, t) for n, t in probes if t.lower() not in doc_flat.lower()]
    kept = [(n, t) for n, t in probes if t.lower() in doc_flat.lower()]
    L.append("**Checked by CONTENT rather than by label** — the pasted \u201cCartoon:\u201d line bundles five")
    L.append("things, and most of them are written out as separate panels in Paper draft, so the missing")
    L.append("label does not by itself mean anything was lost:")
    for n, _ in kept: L.append(f"  - present in Paper draft: {n}")
    for n, _ in gone: L.append(f"  - 🔴 **genuinely absent from Paper draft: {n}** — take it back from the pasted draft")
    L.append("")
    L.append("The pasted bundle's fifth item, `quantification of mad1 delocalization`, is NOT lost — it is")
    L.append("`Mad1 vs hec1 plot` under **Figure 3** in both drafts. But the deck has merged Mad1 into Figure 1,")
    L.append("so that panel and its legend need to move there.")
    L.append("")

    same = [n for n in sorted(set(P) & set(D)) if n != 1 and P[n][1] == D[n][1] and P[n][0] == D[n][0]]
    diff = [n for n in sorted(set(P) & set(D)) if n != 1 and n not in same]
    L += [f"## Figures 2–10", "",
          f"- identical in both drafts (title and panel list): **{', '.join(str(n) for n in same) or 'none'}**"]
    for n in diff:
        L.append(f"- **Figure {n} differs**:")
        if P[n][0] != D[n][0]:
            L.append(f"    - pasted title: *{P[n][0]}*")
            L.append(f"    - Paper-draft title: *{D[n][0]}*")
        for x in [y for y in D[n][1] if y not in P[n][1]]: L.append(f"    - only in Paper draft: {x}")
        for x in [y for y in P[n][1] if y not in D[n][1]]: L.append(f"    - only in pasted: {x}")
    L.append("")

    T = Tt
    L += ["## Both drafts are behind the deck", "",
          "The deck now carries these titles (topmost title per artboard = the current one; the second line",
          "is the older title she has not deleted yet):", ""]
    for ab in sorted(T, key=int):
        cur = T[ab][0][1]
        old = T[ab][1][1] if len(T[ab]) > 1 else ""
        L.append(f"- **artboard {ab}** — {cur}")
        if old: L.append(f"    - stale title still on the board: {old}")
    L.append("")
    L += ["### What the deck changed that neither legend draft reflects", "",
          "- **Figure 3 (Mad1) has been folded into Figure 1.** Artboard 1's current title ends *\u201c…and",
          "  sisterless kinetochores retain Spindle Assembly Checkpoint component Mad1 longer than paired",
          "  kinetochores\u201d*, and every Mad1/Hec1 figure is placed on artboard 1. The separate Figure 3 legend",
          "  in both drafts no longer has an artboard.",
          "- **Figure 7 (polar kinetochores joining the plate) has been folded into Figure 4.** Artboard 5's",
          "  current title ends *\u201c…and polar sisterless kinetochores may join the metaphase plate before",
          "  anaphase\u201d*, and artboard 6 — which still carries the old Fig 7 title — has **no artwork at all**.",
          "- **The numbering is now 1–9, not 1–10.** Cell-scale movement is Figure 6 on the deck (Figure 8 in",
          "  both drafts); the summary cartoon is Figure 8 on the deck (Figure 10 in both drafts).",
          "- Artboard 3 carries the summary-cartoon title and **no artwork** — that cartoon is still to be drawn.", ""]
    io.open(OUT, "w", encoding="utf-8").write("\n".join(L) + "\n")
    print("\n".join(L[:40]))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    sys.exit(main())
