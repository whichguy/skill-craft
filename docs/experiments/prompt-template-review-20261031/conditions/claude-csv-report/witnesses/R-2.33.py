import os
from _lib import *
big = "9" * 5000
p = f(HDR + row() + row(big, "1") + row("1", "0.10", "south"))
c, o, e = run(p)
ok(e == "%s:3: units too large '%s'\n" % (p, big) and c == 2 and js(o)["rows"] == 2, (c, e[:200]))
