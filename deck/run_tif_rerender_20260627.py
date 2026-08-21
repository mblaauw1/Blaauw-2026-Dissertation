#!/usr/bin/env python3
"""Re-render all fluorescence plots on the 16-bit cropped TIF (lib.FluorTif) at r=5, then rebuild the deck.
Non-fluorescence plots (roundness, KK distance, oscillation, velocity, plate distance) are scale/coordinate
based and unaffected — not re-run here. Everything on /Volumes/4 MB."""
import os, sys, subprocess, datetime
FIG="/Volumes/4 MB/ablation_figures_20260625"
LOG=open("/Volumes/4 MB/ablation_plots/tif_rerender.log","w")
def log(m):
    line=f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {m}"; print(line,flush=True); LOG.write(line+"\n"); LOG.flush()

# fluorescence scripts (now measure on 16-bit TIF) + the negatives tally
SCRIPTS=["negatives_by_radius.py","group4_ablation_intensity.py","group4_cdc20_poles.py",
         "group4_frap.py","group4_movement.py","group4_prepost.py","group4_tracking_dist.py","group4_fluor.py"]
log(f"=== TIF re-render: {len(SCRIPTS)} scripts at r=5 ===")
for scr in SCRIPTS:
    log(f"{scr} ...")
    p=subprocess.run([sys.executable,f"{FIG}/{scr}"],env=dict(os.environ,MPLBACKEND="Agg"),capture_output=True,text=True)
    tail=(p.stdout.strip().splitlines() or [""])[-1]
    if p.returncode!=0:
        log(f"{scr} FAILED rc={p.returncode}: {(p.stderr.strip().splitlines() or [''])[-1]}")
    else:
        log(f"{scr} ok :: {tail}")

# rebuild deck
for scr in ["deck.py","deck_compact.py"]:
    log(f"{scr} ...")
    p=subprocess.run([sys.executable,f"{FIG}/{scr}"],env=dict(os.environ,MPLBACKEND="Agg"),capture_output=True,text=True)
    tail=(p.stdout.strip().splitlines() or [""])[-1]
    log(f"{scr} {'ok :: '+tail if p.returncode==0 else 'FAILED: '+(p.stderr.strip().splitlines() or [''])[-1]}")
log("=== TIF RE-RENDER DONE ===")
LOG.close()
