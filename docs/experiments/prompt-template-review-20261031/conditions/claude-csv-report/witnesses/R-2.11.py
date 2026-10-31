import os
from _lib import *
p = f(HDR + row('', '1'))
c, o, e = run(p)
ok(e == "%s:2: non-numeric units ''\n" % p and c == 2, (c, e))
