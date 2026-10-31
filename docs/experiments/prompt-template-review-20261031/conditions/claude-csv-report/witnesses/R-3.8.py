import os
from _lib import *
# 1.005 rounds half up to 1.01 (half-even would give 1.0)
c, o, e = run(f(HDR + row("1", "1.005")))
ok(js(o)["revenue"] == 1.01, o)
