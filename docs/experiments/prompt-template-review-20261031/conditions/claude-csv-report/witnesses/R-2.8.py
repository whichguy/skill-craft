import os
from _lib import *
p = f(HDR + row('1.5', '1'))
c, o, e = run(p)
ok(e == "%s:2: non-numeric units '1.5'\n" % p and c == 2, (c, e))
