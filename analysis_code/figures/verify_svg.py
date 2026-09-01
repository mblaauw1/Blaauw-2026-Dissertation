"""SVG-based effect verifier — inspects the editable SVG each plot saves (text preserved) to check:
  (1) CONTENT: expected label/legend/paragraph strings are present (or forbidden ones absent) — encodes
      the visual feedback items that can't be seen in the numeric data.
  (2) TEXT OVERLAP: parses every <text> element's position + font size, computes its bounding box, and
      flags pairs of DIFFERENT text labels whose boxes overlap (the 'means labels collide with significance
      labels / legend' problem). Rotated (y-axis) labels handled by swapping box w/h.
Run standalone or import. Prints PASS/FAIL for content and lists overlapping label pairs per plot."""
import re, glob, os
ROOT="/Volumes/4 MB/ablation_figures_20260625"
def svg_path(png): return f"{ROOT}/{os.path.dirname(png)}/illustrator/{os.path.basename(png)[:-4]}.svg"

def texts(svgfile):
    """[(x,y,fs,rot,anchor,content)] for every <text>. Two matplotlib encodings handled:
       (a) transform="translate(X Y)"  (legend/free text, anchor=start)
       (b) x="X" y="Y" text-anchor:middle|end  (tick labels/titles, transform=rotate(A x y))."""
    if not os.path.isfile(svgfile): return None
    s=open(svgfile).read()
    out=[]
    for m in re.finditer(r'<text ([^>]*?)>([^<]*)</text>', s):
        attrs,content=m.group(1),m.group(2)
        content=re.sub(r'\s+',' ',content).strip()
        if not content: continue
        fsm=re.search(r'font-size:\s*([\d.]+)',attrs); fs=float(fsm.group(1)) if fsm else 10.0
        tr=re.search(r'translate\(([-\d.]+)\s+([-\d.]+)\)',attrs)
        if tr: x,y=float(tr.group(1)),float(tr.group(2))
        else:
            xm=re.search(r'\bx="([-\d.]+)"',attrs); ym=re.search(r'\by="([-\d.]+)"',attrs)
            x,y=(float(xm.group(1)) if xm else 0.0),(float(ym.group(1)) if ym else 0.0)
        rm=re.search(r'rotate\(([-\d.]+)',attrs); rot=float(rm.group(1)) if rm else 0.0
        am=re.search(r'text-anchor:\s*(\w+)',attrs); anchor=am.group(1) if am else "start"
        out.append((x,y,fs,rot,anchor,content))
    return out

def bbox(x,y,fs,rot,anchor,content):
    w=len(content)*fs*0.55; h=fs*1.0
    if abs(rot)>45: w,h=h,w
    if anchor=="middle": x0=x-w/2
    elif anchor=="end":  x0=x-w
    else:                x0=x
    return (x0, y-h*0.8, x0+w, y+h*0.2)

def overlaps(svgfile, min_frac=0.18):
    """pairs of DIFFERENT labels whose boxes overlap by >= min_frac of the smaller box's area."""
    ts=texts(svgfile)
    if not ts: return []
    # Only consider SHORT labels (<=22 chars): tick / legend / mean / significance / annotation labels.
    # Long strings are axis titles / paragraphs positioned outside the data area — not the overlap the user
    # means ('mean labels collide with significance labels / legend'), and their approximate rotated boxes
    # cause false positives against ticks.
    # HORIZONTAL short labels only. Rotated tick labels (|rot|>5°) are rotated BY matplotlib specifically to
    # avoid overlap, so they aren't the problem the user means and their slanted boxes cause false positives.
    ts=[t for t in ts if len(t[5])<=22 and abs(t[3])<=5]
    bs=[(bbox(*t),t[5],t[0],t[1],t[2]) for t in ts]         # + raw anchor x,y,fs
    hits=[]
    for i in range(len(bs)):
        (ax0,ay0,ax1,ay1),at,axr,ayr,afs=bs[i]
        aa=max(1e-6,(ax1-ax0)*(ay1-ay0))
        for j in range(i+1,len(bs)):
            (bx0,by0,bx1,by1),bt,bxr,byr,bfs=bs[j]
            if at==bt: continue                             # identical strings (e.g. repeated tick) skip
            # skip the two LINES of one multi-line label: same anchor x (center-aligned), stacked vertically
            if abs(axr-bxr)<2.0 and abs(ayr-byr)<2.5*max(afs,bfs): continue
            ix=max(0,min(ax1,bx1)-max(ax0,bx0)); iy=max(0,min(ay1,by1)-max(ay0,by0))
            inter=ix*iy
            if inter<=0: continue
            ba=max(1e-6,(bx1-bx0)*(by1-by0))
            if inter>=min_frac*min(aa,ba):
                hits.append((at[:32],bt[:32],round(inter/min(aa,ba),2)))
    return hits

# ---- CONTENT assertions per plot: (png, [must_contain...], [must_NOT_contain...]) ----
# substrings matched anywhere in the SVG text (case-insensitive).
CONTENT=[
 # --- violins / survival / roundness / area / start-rounded ---
 ("group1/G1_survival.png", ["unmodified","1-Sisterless","off-target"], ["Double Chromosome","All off-target"]),
 ("group1/G1_violin2_sisterless_1234.png", ["Sisterless"], ["Double Chromosome"]),
 ("group1/G1_violin2_mitotic_duration.png", ["1-Sisterless","N="], ["Double Chromosome"]),
 ("group1/G1_violin1_attempts_vs_duration.png", ["N=47","N=13","N=26"], []),
 ("group1/G1_roundness_combined.png", ["NEBD","median time to anaphase"], ["Double Chromosome"]),
 ("group1/G1_roundness_combined_trendscaled.png", ["median time to anaphase"], ["Double Chromosome"]),
 ("group1/G1_area_combined.png", ["NEBD"], ["Double Chromosome"]),
 ("group1/G1_area_combined_trendscaled.png", ["NEBD"], ["Double Chromosome"]),
 ("group1/G1_roundness_split.png", ["NEBD"], []),
 ("group1/G1_area_split.png", ["NEBD"], []),
 ("group1/G1_start_rounded_vs_duration.png", ["All off-target"], ["1-Sisterless off-target"]),
 ("group1/G1_start_rounded_metaphase.png", ["All off-target"], ["1-Sisterless off-target"]),
 ("group1/G1_start_rounded_metaphase_statgrid.png", ["metaphase"], []),
 # --- duration / phase-split / dynamics / kk ---
 ("group2/G2_phase_split_violin.png", ["Sisterless"], ["2-Sisterless","unmodified"]),
 ("group2/G2_phase_split_statgrid.png", [], ["2-Sisterless","unmodified"]),
 ("group2/G2_metaphase_dynamics_prometa.png", ["prophase","prometaphase"], []),
 ("group2/G2_abl_to_meta_1sis_prophase.png", ["11"], []),
 ("group2/G2_prophase_dynamics.png", ["Sisterless"], ["2-Sisterless"]),
 ("group2/G2_kk_distance_by_phase.png", ["phase"], []),
 # --- Group 3 ---
 ("group3/G3_kt_fate.png", ["remains at pole","moves to plate","metaphase plate the entire time"], []),
 ("group3/G3_origin_position.png", ["metaphase duration"], []),
 ("group3/G3_congression_fraction.png", ["Sisterless"], []),
 ("group3/G3_chromo_length_bysister.png", ["Sisterless"], []),
 # --- movement / tracking ---
 ("group4/G4_oscillation.png", ["1-Sisterless","3-Sisterless"], []),
 ("group4/G4_kt_intensity_time.png", ["Sisterless"], ["unassigned"]),
 ("group4/G4_kt_intensity_time_scaled01.png", ["normalized"], ["unassigned"]),
 ("group4/G4_velocity.png", ["plate","pole"], []),
 ("group4/G4_velocity_vs_distance.png", ["plate","pole"], []),
 ("group4/G4_plate_distance_time.png", ["metaphase","anaphase"], []),
 ("group4/G4_oscillation_tracking.png", ["500 of"], []),
 ("group4/G4_plate_distance_tracking.png", ["single","triple"], []),
 ("group4/G4_oscillation_chronological.png", ["metaphase onset"], ["20250401"]),
 ("group4/G4_plate_distance_chronological.png", ["single","triple","anaphase"], ["20250401"]),
 # --- fluor / cdc20 / drug ---
 ("group4/G4_fluor_over_time_metaphase.png", ["metaphase"], []),
 ("group4/G4_fluor_over_time_scaled01_metaphase.png", ["metaphase"], []),
 ("group4/G4_fluor_vs_duration.png", [], []),
 ("group4/G4_cdc20_intensity_sanitycheck.png", ["TrackMate"], []),
 ("group4/G4_distance_vs_fluor_paired.png", ["paired"], []),
 ("group4/G4_zm_full.png", ["Control"], []),
 # --- polar-lagging / exhaustion / prepost ---
 ("group4/G4_polar_lagging_vs_duration.png", ["Sisterless"], ["2-Sisterless"]),
 ("group4/G4_polar_lagging_vs_duration_byphase.png", ["single","triple"], ["Metaphase","2-Sisterless"]),
 ("group4/G4_exhaustion_violin.png", ["censored"], []),
 ("group4/G4_lagging_position.png", ["anaphase"], []),
 ("group4/G4_prepost_intensity_nolines.png", [], []),
 # --- combined FRAP/ablation traces ---
 ("group4/G4_frap_combined.png", ["start=1"], []),
 ("group4/G4_frap_both_combined.png", ["start"], []),
 ("group4/G4_ablation_intensity_selected_combined.png", ["open circle"], []),
]

def run():
    print("=== CONTENT CHECKS (from SVG text) ===")
    cpass=cfail=0
    for png,must,mustnot in CONTENT:
        sv=svg_path(png)
        ts=texts(sv)
        if ts is None: print(f"[SKIP] {os.path.basename(png)} (no SVG)"); continue
        blob=" || ".join(t[5] for t in ts).lower()
        # SHORT labels only (<=25 chars) = tick/legend/group labels; long strings = titles/axis labels.
        # A 'forbidden group' counts only if it's a standalone label, not a word inside a descriptive title.
        labels=[t[5].lower() for t in ts if len(t[5])<=25]
        miss=[m for m in must if m.lower() not in blob]
        # forbidden group present only if it appears as a WHOLE WORD in a short standalone label
        # (so 'Metaphase' does NOT match inside 'Prometaphase', and titles are excluded).
        bad=[m for m in mustnot if any(re.search(r'(?<![a-z])'+re.escape(m.lower())+r'(?![a-z])',lab) for lab in labels)]
        ok=not miss and not bad
        cpass+=ok; cfail+=not ok
        if not ok: print(f"[FAIL] {os.path.basename(png)}"+(f" MISSING {miss}" if miss else "")+(f" FORBIDDEN {bad}" if bad else ""))
        else: print(f"[PASS] {os.path.basename(png)}")
    print(f"content: {cpass} pass / {cfail} fail\n")

    print("=== TEXT-OVERLAP CHECK (all placed plots' SVGs) ===")
    ns={}; exec(open(f"{ROOT}/deck.py").read().split('# ---------------- PPTX')[0],ns)
    placed=set()
    SWAPPED_OUT={'20250501_ptk_yfpcdc20_12_frap0'}  # build_pdfs swaps these out; not in final PDF
    for g in ns["GROUPS"]:
        for s in g["slides"]:
            if "img" in s and s["img"].endswith(".png") and not any(x in s["img"] for x in SWAPPED_OUT): placed.add(s["img"])
    total_ov=0; plots_with_ov=0
    for png in sorted(placed):
        sv=svg_path(png)
        if not os.path.isfile(sv): continue
        ov=overlaps(sv)
        if ov:
            plots_with_ov+=1; total_ov+=len(ov)
            print(f"  {os.path.basename(png)}: {len(ov)} overlapping label pair(s)")
            for a,b,f in ov[:4]: print(f"      '{a}'  <>  '{b}'   ({int(f*100)}% of smaller)")
    print(f"\noverlap: {plots_with_ov} plots with overlapping labels, {total_ov} pairs total")
    return cfail,total_ov

if __name__=="__main__":
    run()
