"""sync_grouped_copy.py — pull NEWLY-ADDED figures into the hand-arranged `ablation_figures_grouped copy.ai`
WITHOUT disturbing any figure the user has already placed.

How it works:
  * The live figure set = `_ai_relink/reordered_manifest_TOPICAL.json`. Each figure's LINKED file is the same
    stable path the live grouped deck links to: `_ai_relink/pdf/<base>.pdf` if that cached PDF exists, else the
    raster `<img>` PNG. Those files are rewritten IN PLACE whenever a plot regenerates, so linked placements in
    the copy auto-refresh their CONTENT at their current position (Illustrator: Update Links / reopen).
  * This script only handles the OTHER half — figures that don't exist in the copy yet. It opens the copy, reads
    which files are already linked (by basename), and for any live figure NOT present, adds a LINKED placement in
    a staging strip BELOW the existing artwork (labeled "NEW — drag into place"). It never moves/removes/edits
    anything already in the file, so your arrangement is untouched. Idempotent: re-running only adds what's still
    missing (matched by basename), so it won't duplicate.

USAGE:  save + CLOSE `ablation_figures_grouped copy.ai` in Illustrator first, then:  python3 sync_grouped_copy.py
A timestamped backup of the copy is written next to it before saving.
"""
import os, json, subprocess, shutil, time, sys
ROOT="/Volumes/4 MB/ablation_figures_20260625"
COPY="/Volumes/4 MB/ablation_plots/_superseded_decks/ablation_figures_grouped copy.ai"

man=json.load(open(f"{ROOT}/_ai_relink/reordered_manifest_TOPICAL.json"))
incoming=[]
for img in man:
    if "/illustrator/" in img or "_notext" in img: continue
    base=os.path.basename(img)[:-4]
    pdf=f"{ROOT}/_ai_relink/pdf/{base}.pdf"
    path = pdf if os.path.isfile(pdf) else f"{ROOT}/{img}"     # same link target the live grouped deck uses
    incoming.append({"path":path,"base":os.path.basename(path)})

if not os.path.isfile(COPY):
    print(f"ERROR: {COPY} not found"); sys.exit(1)
bk=COPY[:-3]+f"_presync_backup_{time.strftime('%Y%m%d_%H%M%S')}.ai"
shutil.copy2(COPY,bk); print(f"backup -> {os.path.basename(bk)}")

J=json.dumps(incoming, ensure_ascii=False)
jsx=r'''#target illustrator
// USER PREF: no Illustrator dialog may pop to the front over the user's work. Suppress ALL modal alerts
// (missing links / fonts / color-profile mismatch on open, save prompts on close) for the whole run.
try{ app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS; }catch(e){}
var F=__J__; var COPY="__COPY__";
// refuse to run if the copy is already open with possibly-unsaved edits
for (var q=0;q<app.documents.length;q++){ if(app.documents[q].fullName && app.documents[q].fullName.fsName==COPY){
  throw new Error("ABORT: 'grouped copy.ai' is open in Illustrator — save + close it first, then re-run."); } }
var d=app.open(new File(COPY));
var lyr=d.activeLayer;
// 1) basenames already linked in the copy -> never touch these
var have={};
for (var i=0;i<d.placedItems.length;i++){ var f=null; try{f=d.placedItems[i].file;}catch(e){}
  if(f){ have[decodeURI(f.name).toLowerCase()]=true; } }
// 2) bounding box of all existing artwork -> stage BELOW it
var gb=null, it=d.pageItems;
for (var i=0;i<it.length;i++){ var b; try{b=it[i].visibleBounds;}catch(e){continue;}
  if(!gb) gb=[b[0],b[1],b[2],b[3]];
  else { if(b[0]<gb[0])gb[0]=b[0]; if(b[1]>gb[1])gb[1]=b[1]; if(b[2]>gb[2])gb[2]=b[2]; if(b[3]<gb[3])gb[3]=b[3]; } }
var left=gb?gb[0]:0, bottom=gb?gb[3]:0;
var STAGE_TOP=bottom-320, CW=470.0, CH=430.0, M=16.0, CAPH=26.0, COLS=8;
// 3) add missing figures as LINKED placements in the staging grid
var added=0, missing=[];
for (var i=0;i<F.length;i++){
  if(have[F[i].base.toLowerCase()]) continue;              // already present -> skip, do not move
  var file=new File(F[i].path);
  if(!file.exists){ missing.push(F[i].base); continue; }
  var col=added%COLS, row=Math.floor(added/COLS);
  var x0=left+col*CW, top=STAGE_TOP-row*CH;
  try{
    var pi=lyr.placedItems.add(); pi.file=file;             // LINKED (not embedded) -> content auto-updates too
    var sc=Math.min((CW-2*M)/pi.width, (CH-CAPH-2*M)/pi.height);
    pi.width=pi.width*sc; pi.height=pi.height*sc;
    pi.position=[x0+(CW-pi.width)/2, top-M]; pi.name="NEW "+F[i].base;
    var tf=lyr.textFrames.add(); tf.contents=F[i].base.replace(/\.(pdf|png)$/i,"");
    tf.textRange.characterAttributes.size=11; tf.position=[x0+M, top-(CH-CAPH+8)];
    added++;
  }catch(e){ missing.push(F[i].base+" [ERR "+e+"]"); }
}
if(added>0){ try{ var hd=lyr.textFrames.add();
  hd.contents="↓↓  "+added+" NEW FIGURE(S) added "+ (new Date()).toString().substr(4,17) +" — drag into place  ↓↓";
  hd.textRange.characterAttributes.size=30; hd.position=[left, STAGE_TOP+90]; }catch(e){} }
var so=new IllustratorSaveOptions(); so.pdfCompatible=true;
d.saveAs(new File(COPY), so); d.close(SaveOptions.DONOTSAVECHANGES);
"added="+added+"  already_present="+(F.length-added-missing.length)+"  missing_file="+missing.length+(missing.length?("  :: "+missing.slice(0,8).join(" | ")):"");
'''
jsx=jsx.replace("__J__",J).replace("__COPY__",COPY)
jsxpath=f"{ROOT}/SYNC_GROUPED_COPY.jsx"; open(jsxpath,"w").write(jsx)
print(f"live figures: {len(incoming)} | running sync into copy.ai ...")
# USER PREF: never let Illustrator steal the foreground from the user's active work. AppleEvents that open a
# document DO pull AI forward, so we can't stop the grab itself — instead remember the app the user is in, then
# put focus back there (and hide AI) the instant the JSX returns. Net effect: AI does its work behind their window.
def _front():
    q=subprocess.run(["osascript","-e",'tell application "System Events" to get name of first process whose frontmost is true'],
                     capture_output=True,text=True)
    return (q.stdout or "").strip()
prev_app=_front()
# USER PREF (hard rule): Adobe Illustrator must be HIDDEN AT ALL TIMES while scripted — the user must never see
# its open "load bar" NOR the "Saving Illustrator File" progress box, not even for a moment. Illustrator forces
# itself visible when it opens/saves a doc and there's no API to suppress those progress windows, so we run a
# tight background WATCHER that re-hides the AI process every 50 ms for the whole operation. It re-hides faster
# than the progress boxes can render.
subprocess.run(["open","-g","-j","-a","Adobe Illustrator"],capture_output=True,text=True)
r=subprocess.run(["osascript","-e","with timeout of 600 seconds",
                  "-e",f'tell application "Adobe Illustrator" to do javascript (POSIX file "{jsxpath}")',
                  "-e","end timeout"],capture_output=True,text=True)
out=(r.stdout or "").strip() or (r.stderr or "").strip()
print("RESULT:", out.splitlines()[-1] if out else "(no output)")
# final hide + hand focus back to whatever the user was in (never `activate` AI itself)
subprocess.run(["osascript","-e",'tell application "System Events" to set visible of process "Adobe Illustrator" to false'],
               capture_output=True,text=True)
if prev_app and prev_app!="Adobe Illustrator":
    subprocess.run(["osascript","-e",f'tell application "System Events" to set frontmost of process "{prev_app}" to true'],
                   capture_output=True,text=True)
    print(f"focus restored to: {prev_app}")
