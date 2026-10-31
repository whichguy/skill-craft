import os
from _lib import *
c, o, e = run(f(HDR))
ok(e == "", e)
n = f(HDR + row()); h = f(HDR)
c, o, e = run(n, h)
ok(e == "", e)
