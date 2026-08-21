var d=app.activeDocument;
var opts=new ExportOptionsPNG24(); opts.artBoardClipping=true; opts.horizontalScale=18; opts.verticalScale=18;
d.artboards.setActiveArtboardIndex(0);
d.exportFile(new File("/Volumes/4 MB/_scratch/overflow_ab0.png"), ExportType.PNG24, opts);
d.artboards.setActiveArtboardIndex(1);
d.exportFile(new File("/Volumes/4 MB/_scratch/overflow_ab1.png"), ExportType.PNG24, opts);
"exported";
