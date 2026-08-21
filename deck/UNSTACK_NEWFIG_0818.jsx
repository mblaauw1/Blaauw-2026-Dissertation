// Two figures on NEW_FIGURES_20260804.ai were sitting EXACTLY on top of another figure (100% overlap),
// so one of each pair was completely hidden. They were off every artboard until the 2026-08-18 artboard
// pass, which is why the overlap audit had never seen them. Both are moved — same size, same artboard,
// into a free slot found with a 20 pt occupancy grid (30 pt margin). Nothing else is touched.
// Traps honoured: no var named `path`/`open`/`L`; doc name captured BEFORE close; alerts suppressed.
#target illustrator

var AIP = "/Volumes/4 MB/1_DECKS/NEW_FIGURES_20260804.ai";
var HB  = new File("/Volumes/4 MB/_claude_tmp/unstack_heartbeat.txt");
function beat(m){ try{ HB.open("a"); HB.writeln(m); HB.close(); }catch(e){} }

// [linked basename, new left, new top]
var MOVES = [
  ["G6six_polar_paired_20250404_ptk_yfpcdc20_11", -5998.4, -5708.4],
  ["G6perkt_paired_anisotropy",                   -5320.6,  110.1]
];

app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS;
beat("open");
var doc = app.open(new File(AIP));
var docName = doc.name;
var moved = 0, seen = 0;
for (var i = 0; i < doc.placedItems.length; i++) {
  var pi = doc.placedItems[i], base = "";
  try { base = pi.file.name.replace(/\.(pdf|png|ai|eps)$/i, ""); } catch (e) { continue; }
  for (var j = 0; j < MOVES.length; j++) {
    if (base === MOVES[j][0]) {
      seen++;
      var before = pi.left + "," + pi.top;
      pi.left = MOVES[j][1]; pi.top = MOVES[j][2];
      moved++;
      beat("moved " + base + " from " + before + " to " + pi.left + "," + pi.top);
    }
  }
}
beat("saving");
doc.save();
doc.close(SaveOptions.SAVECHANGES);
app.userInteractionLevel = UserInteractionLevel.DISPLAYALERTS;
beat("DONE moved=" + moved + " seen=" + seen);
"moved=" + moved + " seen=" + seen;
