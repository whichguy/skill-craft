import os
from _lib import *
c, o, e = run(f(HDR + row()))
ok(list(js(o)) == ["rows", "revenue", "by_region", "by_product"], o)
