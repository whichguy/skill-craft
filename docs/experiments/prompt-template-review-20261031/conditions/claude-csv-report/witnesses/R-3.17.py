import os
from _lib import *
c, o, e = run(f(HDR + row() + row("1", "0.10", "south")))
ok(o == '{"rows": 2, "revenue": 7.6, "by_region": {"north": 7.5, "south": 0.1}, "by_product": {"widget": 4}}\n', repr(o))
