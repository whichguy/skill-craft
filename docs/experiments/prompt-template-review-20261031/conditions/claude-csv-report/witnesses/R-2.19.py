import os
from _lib import *
p = f(HDR + row('abc', 'xyz'))
c, o, e = run(p)
ok(e == "%s:2: non-numeric units 'abc'\n" % p and c == 2, (c, e))
