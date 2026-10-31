import os
from _lib import *
a = f(HDR + row())
c, o, e = run(a, a)
j = js(o)
ok(c == 0 and j["rows"] == 2 and j["revenue"] == 15.0 and j["by_product"] == {"widget": 6}, (c, o, e))
