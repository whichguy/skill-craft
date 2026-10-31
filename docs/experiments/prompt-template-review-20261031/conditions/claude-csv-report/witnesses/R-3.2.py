import os
from _lib import *
c, o, e = run(f(HDR + row()))
ok(o.endswith("\n") and o.count("\n") == 1, repr(o))
