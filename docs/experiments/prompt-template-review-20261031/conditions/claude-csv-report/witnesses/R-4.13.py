import os
from _lib import *
p = f(HDR + row() + b"2024-01-01,north,widget,x,1")
c, o, e = run(p)
ok(e == "%s:3: non-numeric units 'x'\n" % p and c == 2, (c, e))
