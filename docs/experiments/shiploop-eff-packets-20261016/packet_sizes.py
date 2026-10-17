"""Raw character sizes per packet of two dump dirs (full and printed, inline and ask-agent): packet_sizes.py BEFORE AFTER [--rows]"""
import sys
from pathlib import Path
b, a = Path(sys.argv[1]), Path(sys.argv[2])
tb = ta = 0
for kind in ("inline/full", "inline/printed", "ask-agent/full", "ask-agent/printed"):
    sb = sa = 0
    rows = []
    for f in sorted((b / kind).glob("*.txt")):
        x, y = len(f.read_text()), len((a / kind / f.name).read_text())
        sb += x; sa += y
        rows.append(f"{f.stem.split('-',1)[1][:16]:16s} {x:6d} {y:6d} {y-x:+5d}")
    print(f"== {kind}: total {sb} -> {sa} ({sa-sb:+d}, {100*(sa-sb)/sb:+.1f}%)")
    if "--rows" in sys.argv: print("\n".join(rows))
    tb += sb; ta += sa
print("ALL", tb, "->", ta, f"({ta-tb:+d}, {100*(ta-tb)/tb:+.1f}%)")
