import os
from _lib import *
p = f(HDR + row('1_0', '1'))
c, o, e = run(p)
ok(e == "%s:2: non-numeric units '1_0'\n" % p and c == 2, (c, e))
