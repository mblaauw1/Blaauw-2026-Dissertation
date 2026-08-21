# When units go on an axis, and how to abbreviate a long cohort name

Answers to her two questions of 2026-08-17, plus the canonical tables the publication decks now enforce.
The rules below are implemented in `ablation_figures_20260625/canon_labels.py`, so the figures follow them
mechanically rather than by remembering.

---

## 1. When do units belong on an axis?

**Put a unit on the axis whenever the quantity is dimensional — and never otherwise.**

| the axis shows | unit? | write it as |
|---|---|---|
| a time, a length, an area, a speed, an angle | **yes** | `Metaphase duration (min)`, `k–k distance (µm)`, `Cell cross-sectional area (µm²)`, `Kinetochore speed (µm/min)`, `Cumulative plate rotation (°)` |
| a ratio of two like quantities (roundness, aspect ratio, near/far area ratio) | **no** — it is dimensionless | `Cell roundness`, `Aspect ratio` |
| a fraction or a probability | **no** | `Fraction of metaphase elapsed`, `Fraction of kinetochores that stayed polar` |
| a normalised or scaled value | **no unit — give the BASIS instead** | `Normalized intensity`, or `Fluorescence (normalized to metaphase onset)` |
| a count | **no** | `Ablation targets per cell` |
| a fluorescence intensity with no calibration | **yes, as arbitrary units** | `Kinetochore eYFP–Cdc20 (a.u.)` |
| a percentage | **yes, in the label, not on every tick** | `Cells reaching anaphase (%)` |

**Formatting, so every axis matches:**

1. Quantity first, unit in parentheses, one space before the bracket: `Metaphase duration (min)`.
2. Sentence case. Only proper nouns and gene/protein names keep their capitals.
3. **One glyph per unit, everywhere**: `µm`, `µm²`, `µm/min`, `min`, `s`, `a.u.`, `°`.
   Never `um`, `um^2`, `microns`, `sec`, `deg`, `AU`.
4. **One time representation per quantity.** Decimal **minutes** on any axis a reader might do arithmetic
   with. `mm:ss` **only** for the burned-in clock on a timestrip frame, where they are reading a movie.
   The same quantity must not be `(min)` on one figure and `(MM:SS)` on the next — that was the single
   biggest inconsistency on the decks (36 axes said `(MM:SS)`, 20 said `(min)`, for the same measurement).
5. **No explanatory clause inside a label.** Inclusion criteria, binning notes and caveats go in the figure
   legend. `PUB=1` strips them from the artwork automatically.
6. A log axis keeps the unit on the quantity; only the tick spacing changes.

---

## 2. Defining a long cohort name once, then abbreviating

Yes — this is standard, and reviewers expect it. The valid pattern has three parts:

**(a) Define it once, at first use, with the abbreviation in parentheses.**
Do it in the place the reader meets the cohort first — the schematic panel of Figure 1 and/or the first
Results sentence that introduces the groups:

> "…kinetochores were destroyed by laser ablation, generating cells with one, two or three sisterless
> kinetochores (1-sis, 2-sis, 3-sis) alongside off-target ablation controls (off-target) and unmanipulated
> controls (unmod)."

**(b) Use only the abbreviation after that — everywhere.** Axis tick labels, legends, figure legends,
Results text, supplementary. Mixing the long and short forms is worse than using either consistently.

**(c) Give the reader one place to look it up.** Either a small key panel on the Figure 1 cartoon, or an
"Abbreviations" line at the head of the figure legends. Both are accepted; the cartoon is better here
because the groups are defined by a physical manipulation that the cartoon is already drawing.

**Rules for the abbreviations themselves**
* short — 8 characters or fewer, so they fit under a violin without wrapping;
* one abbreviation per group, forever, in one capitalisation;
* no plural variants (`3-sis`, never `3-sis cells` in one place and `3-sis` in another);
* don't repeat what is true of every group. Every sisterless cohort here is on-target by construction, so
  "on-target" is said **once at definition** and never again — which is exactly the "triple sisterless
  kinetochores, on-target" problem you raised.

### The canonical set for this project

| abbreviation | defined once as | note |
|---|---|---|
| `unmod` | unmanipulated control | |
| `1-sis` | one sisterless kinetochore | on-target |
| `2-sis` | two sisterless kinetochores | on-target |
| `3-sis` | three sisterless kinetochores | on-target |
| `4-sis` | four sisterless kinetochores | on-target |
| `off-target` | off-target ablation control | |
| `dbl-KT` | two ablations on one kinetochore | |
| `dbl-chr` | two kinetochores destroyed on one chromosome | |
| `collagen` | collagen-plated, sisterless | plating substrate, not a drug |
| `meta-abl` | ablation performed during metaphase | excluded from the main cohorts by default |

Before this, the same three cohorts appeared as `3-Sister`, `3-Sisterless`, `3-sisterless`, `3 sisterless`
and `Destruction of two kinetochores on one chromosome` (a three-line tick label that collided with its own
N). All of those now map to one name.

---

## How this is enforced

`canon_labels.py` holds three tables — `AXIS` (every wording seen on the decks → the one canonical label),
`GROUP` (every cohort wording → the short name), and `UNIT_FIX` (glyph-level repairs applied to anything not
in the tables, so a NEW figure cannot reintroduce `um` or `deg` just by being written later).

`lib.apply_style()` applies them whenever `PUB=1`, at the same time as it strips figure titles and the
explanation sentences. That means the publication copies of the two main decks are standardised by
construction, and the working decks keep the fuller wording you use while building.
