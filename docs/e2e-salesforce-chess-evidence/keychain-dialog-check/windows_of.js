// usage: osascript -l JavaScript windows_of.js <pid> [<pid> ...]
// The windows (on screen or not) that the given processes own, as JSON. The window server lists every window's owner
// without Screen Recording access; only window titles are withheld.
ObjC.import('CoreGraphics');
function run(argv) {
  var want = argv.map(Number);
  var info = ObjC.deepUnwrap(ObjC.castRefToObject(
    $.CGWindowListCopyWindowInfo($.kCGWindowListOptionAll, $.kCGNullWindowID)));
  return JSON.stringify(info.filter(function (w) { return want.indexOf(w.kCGWindowOwnerPID) >= 0; })
    .map(function (w) {
      return {owner: w.kCGWindowOwnerName, pid: w.kCGWindowOwnerPID, layer: w.kCGWindowLayer,
              onscreen: !!w.kCGWindowIsOnscreen, alpha: w.kCGWindowAlpha,
              size: Math.round(w.kCGWindowBounds.Width) + 'x' + Math.round(w.kCGWindowBounds.Height)};
    }));
}
