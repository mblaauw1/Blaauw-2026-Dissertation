#!/usr/bin/env python3
"""Shared thorough-statistics helpers rendered ONTO each plot (user 2026-07-23).
Grouped: Kruskal-Wallis omnibus + all pairwise Mann-Whitney with Holm correction + Cliff's delta effect
size + per-group N. Correlation: Spearman + Pearson + N. Draw as a compact text box on the axes."""
import numpy as np
from scipy import stats as st
import itertools


def cliffs_delta(a, b):
    a = np.asarray(a, float); b = np.asarray(b, float)
    if len(a) == 0 or len(b) == 0: return np.nan
    gt = sum((a[:, None] > b[None, :]).sum(1)); lt = sum((a[:, None] < b[None, :]).sum(1))
    return (gt - lt) / (len(a) * len(b))


def grouped_stats_lines(groups, order=None):
    order = order or [k for k in groups]
    labs = [k for k in order if len(groups.get(k, [])) >= 3]
    lines = []
    if len(labs) < 2:
        return ["n/a (need ≥2 groups with N≥3)"]
    arrs = {k: np.asarray(groups[k], float) for k in labs}
    lines.append("  ".join(f"{k}:N={len(arrs[k])}" for k in labs))
    if len(labs) >= 3:
        H, p = st.kruskal(*[arrs[k] for k in labs])
        lines.append(f"Kruskal–Wallis H={H:.1f}, p={p:.2g}")
    pairs = list(itertools.combinations(labs, 2))
    raw = []
    for a, b in pairs:
        try:
            U, pp = st.mannwhitneyu(arrs[a], arrs[b], alternative="two-sided")
        except Exception:
            pp = 1.0
        raw.append((a, b, pp, cliffs_delta(arrs[a], arrs[b])))
    # Holm step-down
    idx = sorted(range(len(raw)), key=lambda k: raw[k][2])
    m = len(raw); adj = [1.0] * m; prev = 0.0
    for rank, k in enumerate(idx):
        v = min(1.0, (m - rank) * raw[k][2]); v = max(v, prev); prev = v; adj[k] = v
    for k, (a, b, pp, d) in enumerate(raw):
        star = "***" if adj[k] < 0.001 else "**" if adj[k] < 0.01 else "*" if adj[k] < 0.05 else "ns"
        lines.append(f"{a}–{b}: p={adj[k]:.2g}{star} δ={d:+.2f}")
    return lines


def add_group_stats(ax, groups, order=None, loc="upper right", fontsize=6.6):
    txt = "\n".join(grouped_stats_lines(groups, order))
    xa = 0.98 if "right" in loc else 0.02
    ya = 0.98 if "upper" in loc else 0.02
    ax.text(xa, ya, txt, transform=ax.transAxes, ha=("right" if "right" in loc else "left"),
            va=("top" if "upper" in loc else "bottom"), fontsize=fontsize, family="monospace",
            bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="#bbb", alpha=0.82), zorder=10)


def corr_text(x, y):
    x = np.asarray(x, float); y = np.asarray(y, float)
    m = np.isfinite(x) & np.isfinite(y); x, y = x[m], y[m]
    if len(x) < 4:
        return f"N={len(x)} (too few)"
    rho, ps = st.spearmanr(x, y)
    r, pp = st.pearsonr(x, y)
    return f"Spearman ρ={rho:.2f}, p={ps:.2g}\nPearson r={r:.2f}, p={pp:.2g}\nN={len(x)}"


def add_corr_stats(ax, x, y, loc="upper left", fontsize=7.0):
    xa = 0.98 if "right" in loc else 0.02
    ya = 0.98 if "upper" in loc else 0.02
    ax.text(xa, ya, corr_text(x, y), transform=ax.transAxes, ha=("right" if "right" in loc else "left"),
            va=("top" if "upper" in loc else "bottom"), fontsize=fontsize, family="monospace",
            bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="#bbb", alpha=0.82), zorder=10)
