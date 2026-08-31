#!/usr/bin/env python3
"""Assemble the Results and Discussion sections from HER OWN SENTENCES ONLY.

HER INSTRUCTION, 2026-08-21: *"i didnt want you writing anything yourself in the results or discussion
sections. i just wanted you to look through all of the things id written ... so as to then take the relevant
sentences and put them in paragraphs (and i also specifically said it [was fine] if the wording was choppy,
or if transitions between sentences was rough, as it was just most important to me that what was being
included was my own sentences."*  Results ~2000 words.

HOW THIS GUARANTEES IT. Nothing here retypes her prose -- retyping is where a paraphrase sneaks in. Every
brick is an (source file, start anchor, end anchor) triple, and the text is CUT OUT of her own file at build
time. If an anchor stops matching, the build FAILS rather than emitting something unverified. The output
therefore cannot contain a sentence that is not in one of her documents.

WHAT IS MINE, and it is only ever outside her prose: the section headings (taken verbatim from the figure
titles SHE typed on the publication artboards), the "Fig N" markers that key a paragraph to an artboard, and
the provenance table. No connective sentences, no smoothing, no rewriting -- the joins are left rough on
purpose, as she asked.

CORPUS (all hers, mirrored to 4_TABLES_AND_REPORTS/WRITING_CORPUS_20260821/):
  original_results_typeup.txt   her full Results draft in her own voice          (Google Doc + PDF export)
  paper_draft.txt               "Paper draft" -- contains `results V2` and `discussion`, her newest story
  results_working_document.txt  "Results working document" -- figure-by-figure plan
  condensed_results_typeup.txt  present for reference; DELIBERATELY NOT DRAWN FROM -- see NOT_USED below.
"""
import io, os, re, sys, unicodedata

ROOT = "/Volumes/4 MB"
CORP = f"{ROOT}/4_TABLES_AND_REPORTS/WRITING_CORPUS_20260821"
OUT  = f"{ROOT}/4_TABLES_AND_REPORTS/RESULTS_AND_DISCUSSION_20260821.md"
PROV = f"{ROOT}/4_TABLES_AND_REPORTS/RESULTS_AND_DISCUSSION_20260821_PROVENANCE.tsv"

# `condensed results type-up` is in her Drive but is written in a uniform explanatory register
# ("Rationale: This opening figure establishes the baseline biological state ...") that does not match her
# voice anywhere else, and reads as generated rather than typed. Pulling sentences from it would be the one
# way this file could end up containing prose she did not write, so it is excluded and the exclusion is
# recorded rather than left silent.
NOT_USED = ["condensed_results_typeup.txt"]

SRC = {
    "A": "original_results_typeup.txt",     # her full Results draft
    "B": "paper_draft.txt",                 # `results V2` + `discussion`
    "C": "results_working_document.txt",    # figure-by-figure plan
}


def flat(s):
    """Collapse to one line so an anchor matches across her line wraps; keep her characters as typed."""
    s = unicodedata.normalize("NFC", s)
    s = s.replace("\u00ad", "")
    s = re.sub(r"\\([\[\]#*_])", r"\1", s)      # paper_draft.txt is markdown-escaped; unescape
    s = re.sub(r"\[BM\d+\]", "", s)             # her Google-Docs comment anchors are markers, not prose
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"\s+([.,;:?!])", r"\1", s)      # removing an anchor can leave " ." where she wrote "."
    return s.strip()


CORPUS = {}
for k, fn in SRC.items():
    p = f"{CORP}/{fn}"
    if not os.path.isfile(p):
        sys.exit(f"missing corpus file: {p}")
    CORPUS[k] = flat(io.open(p, encoding="utf-8", errors="replace").read())


class Missing(Exception):
    pass


def cut(src, start, end):
    """Exact span of HER text, from `start` through the end of `end`. Raises if not found verbatim."""
    hay = CORPUS[src]
    i = hay.find(flat(start))
    if i < 0:
        raise Missing(f"[{src}] start anchor not found: {start[:70]!r}")
    j = hay.find(flat(end), i)
    if j < 0:
        raise Missing(f"[{src}] end anchor not found after start: {end[:70]!r}")
    return hay[i:j + len(flat(end))]


# ---------------------------------------------------------------------------------------------------
# STRUCTURE.  Headings are the figure titles SHE typed on the publication artboards, and the artboard each
# one names is the one that carries that figure today (dumped from META_FIGURES_20260814_PUBLICATION_
# 20260820.ai). Fig 7 and Fig 8 have her title but NO artwork placed yet -- see the coverage report.
# ---------------------------------------------------------------------------------------------------
RESULTS = [
 ("Fig 1 · AB1", "Laser ablation of kinetochores in prometaphase produces sisterless kinetochores with "
                 "enduring incorrect attachments, and sisterless kinetochores retain Spindle Assembly "
                 "Checkpoint component Mad1 longer than paired kinetochores.", [
   ("A", "To ask how we could create a forced state", "or (2) disappearance into the metaphase plate."),
   ("A", "Localization at poles indicated that the kinetochore", "reside further from the pole its attached to."),
   ("A", "Disappearance into the metaphase plate indicated", "supporting the abnormal single kinetochore state)."),
   ("B", "In cells with fluorescently labeled Mad1", "than paired kinetochores capable of bioriented attachment."),
   ("A", "In imaging this cell line with fluorescent markers", "consistent with formation of a merotelic attachment when at the metaphase plate."),
 ]),

 ("Fig 2 · AB2", "More than one sisterless kinetochore must be created in prometaphase to increase "
                 "metaphase duration.", [
   ("B", "It has been shown that forcing an incorrect attachment", "when all chromosomes aligned at the metaphase plate"),
   ("A", "To do this, we created sisterless kinetochores on 1, 2, or 3", "ablations was also created."),
   ("A", "We observed that while a single on-target ablation did not create", "scaled metaphase duration response in the targeted cell."),
   ("A", "To test how long it would take a cell in our population", "We then imaged these cells for 8+ hours."),
   ("A", "We also repeated this experiment with nocodazole", "on the order of tens of minutes at the most severe."),
   ("A", "However, the cells with two kinetochores destroyed on the same chromosome",
         "continued production of MCC through prometaphase."),
   ("A", "These results indicate that while cells with increased forced permanent",
         "this is not due to mitotic slippage."),
 ]),

 ("Fig 3 · AB5", "Sisterless kinetochore localization at time of anaphase onset differs with number of "
                 "sisterless kinetochores.", [
   ("B", "By the time of anaphase onset in cells with three sisterless kinetochores",
         "the jagged, unsteady oscillation of polar kinetochores."),
   ("A", "While targeted kinetochores would often localize to poles initially",
         "move into the metaphase plate is by obtaining a merotelic connection."),
   ("A", "Once a chromosome with a. sisterless kinetochore is lost in the metaphase plate",
         "and even more so with a sisterless kinetochore."),
   ("A", "Finally, in imaging the cell through anaphase", "as the unmodified chromatids are pulled poleward."),
 ]),

 ("Fig 4 · AB7", "Through metaphase, polar sisterless kinetochores exhibit deformations resembling that of "
                 "paired, plate-aligned kinetochores in the same cell, indicating similar tension "
                 "application.", [
   ("A", "In one method of investigating if merotelic attachments were forming",
         "a hallmark trait of merotelic attachments."),
   ("A", "The sisterelss kinetochroes we created were unable to ever achieve",
         "but also stably satisfying the SAC."),
   ("A", "Merotelic attachments are corrected in paired kinetochores",
         "the global SAC would compute that only correct attachments existed."),
 ]),

 ("Fig 5 · AB8", "Paired kinetochore movement patterns are not preserved across cells with increased number "
                 "of incorrect attachments.", [
   ("C", "Both paired and sisterless kinetochore movement patterns are not preserved",
         "number of incorrect attachments."),
   ("B", "Spindle instability and delays in healthy spindle formation is indicated",
         "moving to the metaphase plate and possibly achieving merotelicity."),
 ]),

 ("Fig 6 · AB4", "Cell-scale mitotic movement patterns are preserved across number of incorrect "
                 "attachments.", [
   ("B", "Triple ablation cells round more", "fooling its local SAC mechanism."),
   ("B", "During prolonged time in metaphase, triple and double sisterless kinetochore conditions",
         "without changing the search ability of k-fibers."),
 ]),

 ("Fig 7 · AB6", "Polar sisterless kinetochores may join the metaphase plate before anaphase onset, trending "
                 "with length and metaphase duration in triple sisterless kinetochore samples.", [
   ("B", "Chromosome size can aid sisterless kinetochores on long chromosomes",
         "allowing the achievement of merotelic attachments."),
   ("A", "We believe this is the situation we\u2019ve created by forcing sisterless kinetochores that localize to poles.",
         "beyond the time range of the localization of other unmodified kinetochores to poles."),
 ]),

 ("Fig 8 · AB3", "Single sisterless kinetochores, if created before metaphase onset, don\u2019t cause metaphase "
                 "delay; greater than one sisterless kinetochores do cause metaphase delay.", [
   ("A", "To test if the SAC causes different delays in response", "near, but not on, a kinetochore."),
   ("A", "Previous literature prompted us to expect that ablations at metaphase",
         "if the cell had not yet passed the \u201cpoint of no return\u201d."),
   ("A", "Moving backwards in mitosis, when we performed ablations at prometaphase",
         "as if they had passed a \u201cpoint of no return\u201d."),
   ("A", "Finally, we performed ablations at the very start of mitosis",
         "there was not a longer metaphase compared to controls."),
 ]),

 ("Fig 9 · AB9", "Creation of sisterless kinetochores before spindle formation lessens metaphase duration.", [
   ("B", "The metaphase time required by sisterless kinetochores in cells with 2 or 3",
         "able to more easily evade the SAC and divide with aneuploidy."),
 ]),
]

DISCUSSION = [
 ("Summary", [
   ("B", "creation of a sisterless kinetochore incapable of bioriented kinetochore-fiber attachment",
         "well before mitotic exhaustion?"),
   ("B", "Overall, this shows that chromosomes are resilient in finding attachment states",
         "was advantageous to the chromosome."),
   ("B", "However, correct attachments aid in building a robust spindle",
         "just on a much more severe scale)"),
 ]),
 ("Novel findings", [
   ("B", "If created before metaphase onset, a kinetochore with a forced incorrect attachment",
         "not sufficient to cause a metaphase delay."),
   ("B", "Interestingly, conditions of greater than one incorrect attachment do cause a prolonged metaphase.",
         "This delay can be eliminated with the addition of ZM."),
   ("B", "As in literature where incorrect attachments are forced on the kinetochores of a single chromosome",
         "potentially indicating an unsatisfied local sac on that kinetochore."),
 ]),
 ("Mechanism", [
   ("A", "In sharp contrast with work in the field showing a single kinetochore was capable of delaying metaphase",
         "caused by that specific type of incorrect attachment."),
   ("B", "Sisterless kinetochores are prone to achieving merotelic connections and not being able to resolve these connections.",
         "either without becoming a polar chromosome at all or after a brief period of being polar."),
   ("A", "This force imbalance forces attachments of any type to become unstable",
         "replaced with no, or lateral, k-fiber attachment."),
   ("A", "This implies that the SAC is sensitive to when incorrect attachments are made",
         "starts this process over from the time of manipulation."),
 ]),
 ("Overall theory", [
   ("B", "Errors in kinetochore attachment that allow full attachment of only one kinetochore",
         "(possible causes could be chromosome replication or condensing error, building error)."),
 ]),
 ("Future directions", [
   ("B", "Investigation in different cell types with different chromosome and kinetochore characteristics",
         "much as muntjac"),
 ]),
 ("Conclusion", [
   ("B", "the SAC is efficient in preventing or stalling anaphase onset",
         "could cause missegregation / aneuploidy exist before NEBD"),
 ]),
]


UNFINISHED = []      # her own sentences that stop without punctuation and run into the next brick


def render(blocks, prov, kind):
    body, nwords = [], 0
    for item in blocks:
        if kind == "results":
            key, title, bricks = item
            body.append(f"### {key} — {title}\n")
        else:
            key, bricks = item
            title = key
            body.append(f"### {key}\n")
        para = []
        for i, (src, a, b) in enumerate(bricks):
            t = cut(src, a, b)
            # She left a few sentences unfinished. Joined to the next brick they read as a run-on, and adding
            # a full stop would be editing her text, so flag them instead and let her close them.
            if i < len(bricks) - 1 and not t.rstrip().endswith((".", "?", "!", ")")):
                UNFINISHED.append((kind, key, t.rstrip()[-60:]))
            para.append(t)
            nwords += len(t.split())
            prov.append((kind, key, SRC[src], str(len(t.split())), t[:120]))
        body.append(" ".join(para) + "\n")
    return "\n".join(body), nwords


def main():
    prov = []
    try:
        res, nres = render(RESULTS, prov, "results")
        dis, ndis = render(DISCUSSION, prov, "discussion")
    except Missing as e:
        sys.exit(f"REFUSING TO WRITE — a brick no longer matches her text verbatim:\n  {e}")

    hdr = (
        "# Results and Discussion — 2026-08-21\n\n"
        "**Every sentence below is hers, cut verbatim out of her own files by "
        "`dataops/assemble_results_discussion.py`; the build fails rather than emit anything it cannot "
        "find in one of them.** Nothing is rephrased and no connective sentences have been added, so the "
        "joins are rough on purpose. Sources: `original results type-up`, the `results V2` and `discussion` "
        "sections of `Paper draft`, and `Results working document`. `condensed results type-up` was NOT "
        "drawn from — it does not read as her voice. Her Google-Docs comment anchors (`[BM1]`…) are "
        "stripped; her parenthetical notes are left in.\n\n"
        "**Mine, and only outside her prose:** the headings — which are the figure titles she typed on the "
        "publication artboards — the `Fig N · ABn` keys, and this paragraph.\n\n"
    )
    if UNFINISHED:
        hdr += ("**One thing to close:** these sentences of yours stop without punctuation, so they run into "
                "the next one. Adding a full stop would be editing your text, so they are left as you wrote "
                "them:\n\n"
                + "".join(f"- *{k}*, {f} — \u201c…{t}\u201d\n" for k, f, t in UNFINISHED) + "\n")
    hdr += "---\n\n"
    io.open(OUT, "w", encoding="utf-8").write(
        f"{hdr}## Results\n\n*{nres} words*\n\n{res}\n---\n\n## Discussion\n\n*{ndis} words*\n\n{dis}")
    with io.open(PROV, "w", encoding="utf-8") as fh:
        fh.write("section\tfigure\tsource_file\twords\topening\n")
        for r in prov:
            fh.write("\t".join(r) + "\n")
    print(f"Results   {nres} words")
    print(f"Discussion {ndis} words")
    print(f"bricks {len(prov)}  (every one verified verbatim against her files)")
    print(f"not drawn from: {', '.join(NOT_USED)}")
    print(f"wrote {OUT}\nwrote {PROV}")


if __name__ == "__main__":
    main()
