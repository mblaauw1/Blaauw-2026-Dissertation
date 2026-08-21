#target illustrator
// Export ONLY the kinetochore-shape artboard (30) to a standalone PDF. Does NOT modify the .ai on disk.
try { app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS; } catch(e){}
while (app.documents.length>0){ app.documents[0].close(SaveOptions.DONOTSAVECHANGES); }
var d=app.open(new File("/Volumes/4 MB/ablation_plots/_superseded_decks/ablation_figures_grouped copy.ai"));
var idx=-1;
for (var a=0;a<d.artboards.length;a++){ if(d.artboards[a].name.indexOf("Kinetochore shape")>=0){ idx=a; break; } }
var opt=new PDFSaveOptions();
opt.compatibility=PDFCompatibility.ACROBAT5;
opt.preserveEditability=false;
opt.saveMultipleArtboards=true;
opt.artboardRange=""+(idx+1);
d.saveAs(new File("/Volumes/4 MB/_scratch/kinetochore_shape_family.pdf"), opt);
d.close(SaveOptions.DONOTSAVECHANGES);
"exported artboard "+(idx+1);
