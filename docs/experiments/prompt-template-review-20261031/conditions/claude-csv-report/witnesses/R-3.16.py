import os
from _lib import *
c, o, e = run(f(HDR + row("1", "1", "north", "zeta") + row("1", "1", "north", "alpha") + row("1", "1", "north", "mid")))
ok(list(js(o)["by_product"]) == ["alpha", "mid", "zeta"], o)
