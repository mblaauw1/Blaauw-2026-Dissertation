#!/usr/bin/env python3
"""One-page visual index of her 2026-07-27 question list: every question, its N, its effect and its p, on a
single log-p axis with the 0.05 line drawn. Reads the two ANSWERS files so it can never drift from the
figures — if a question's numbers change, re-run those scripts and this board follows."""
import os, re
import numpy as np, matplotlib.pyplot as plt
import sys
sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import lib
lib.apply_style()
OUT = "/Volumes/4 MB/ablation_figures_20260625/group7_questions"

# (short question, effect string, p-value or None, figure it lives on)
ROWS = [
    ("Q1  polar chromosome length: single vs triple",        "5.84 vs 5.44 µm  (n=21/35)",      0.813,  "QNEW_q1"),
    ("Q2  rounder cells -> more lagging KTs?",                "rho=+0.04  (N=184 cells)",        0.63,   "QNEW_q2"),
    ("Q3a anaphase KT speed: single vs triple",              "1.17 vs 0.55 µm/min  (n=22/3)",   0.225,  "QNEW_q3a"),
    ("Q3b anaphase -> cytokinesis: single vs triple",         "6.7 vs 8.7 min  (n=60/31)",       0.00813, "QNEW_q3b"),
    ("Q3c anaphase toward-pole velocity: single vs triple",  "0.60 vs 0.18 µm/min  (n=22/3)",   0.587,  "QNEW_q3c"),
    ("Q4  'clean' cells: shorter sisterless chromosomes?",   "5.62 vs 5.32 µm  (n=12/82)",      0.799,  "QNEW_q4"),
    ("Q5  polar chromosomes at anaphase in triples",         "ZERO triple cells; singles 1 (12×), 2 (1×)", None, "QNEW_q5"),
    ("Q6  polar oscillations more jagged?",                  "rev 0.50 / 0.53 / 0.59 (pd/pl/lg)", None, "QNEW_q6"),
    ("Q7  chromosome size vs metaphase duration",            "rho=+0.01  (N=96 cells)",         0.9,    "QNEW_q7"),
    ("Q7b chromosome size vs cell rounding",                 "rho=−0.12 mean, +0.03 SD (N=89)", 0.26,   "QNEW_q7b"),
    ("Q8  sisterless fate: prophase vs prometaphase",        "chi-square  (n=78/124)",          0.154,  "QNEW_q8"),
    ("Q8b rounding: prophase vs prometaphase",               "0.609 vs 0.629  (n=54/85)",       0.923,  "QNEW_q8b"),
    ("Q8b′ rounding, 3-ablation cells only",                 "(n=15/17)",                       0.141,  "QNEW_q8b"),
    ("Q8c metaphase oscillation: prophase vs prometaphase",  "paired rev 0.50 vs 0.51 (n=28/24)", 0.73, "QNEW_q8c"),
]

fig, ax = plt.subplots(figsize=(12.4, 6.6))
y = np.arange(len(ROWS))[::-1]
SIG = "#2e8b57"; NS = "#9aa3ab"; NOP = "#c8a24a"
for i, (q, eff, p, _fig) in enumerate(ROWS):
    yy = y[i]
    if p is None:
        ax.scatter(1.0, yy, s=90, color=NOP, marker="s", zorder=3, edgecolor="white", lw=0.6)
    else:
        c = SIG if p < 0.05 else NS
        ax.scatter(p, yy, s=110 if p < 0.05 else 70, color=c, zorder=3, edgecolor="white", lw=0.6)
    ax.text(1.35, yy, eff, va="center", fontsize=8, family="monospace", color="#333")
ax.axvline(0.05, ls="--", color="#d1495b", lw=1.4)
ax.text(0.052, len(ROWS) - 0.4, "p = 0.05", color="#d1495b", fontsize=8, va="top")
ax.set_xscale("log"); ax.set_xlim(0.004, 30)
ax.set_yticks(y); ax.set_yticklabels([r[0] for r in ROWS], fontsize=8.5)
ax.set_xlabel("p value (log scale)   ·   square = descriptive, no test")
ax.set_xticks([0.005, 0.01, 0.05, 0.1, 0.5, 1.0]); ax.set_xticklabels(["0.005", "0.01", "0.05", "0.1", "0.5", "1"])
ax.set_title("Question set, 2026-07-27 — what the existing data can and cannot answer",
             loc="left", fontweight="bold", fontsize=12)
from matplotlib.lines import Line2D
ax.legend([Line2D([], [], marker="o", ls="", color=SIG), Line2D([], [], marker="o", ls="", color=NS),
           Line2D([], [], marker="s", ls="", color=NOP)],
          ["significant", "not significant", "descriptive / underpowered"], fontsize=8, loc="upper left", framealpha=0.9)
ax.grid(axis="y", alpha=0.15)
fig.tight_layout(); fig.savefig(f"{OUT}/QNEW_summary_board.png", dpi=200, bbox_inches="tight"); plt.close(fig)
try:
    lib.record_plot("QNEW_summary_board", ["x"], [], {"family": "questions_20260727"}, script=__file__,
                    caption="question set 2026-07-27: effect and p per question", source=[], key_column=None, fig=fig)
except Exception:
    pass
print(f"  QNEW_summary_board  ({len(ROWS)} questions)")
