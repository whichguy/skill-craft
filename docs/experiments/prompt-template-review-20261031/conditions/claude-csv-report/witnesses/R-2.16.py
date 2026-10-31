import os
from _lib import *
p = f(HDR + row('1', '1e3'))
c, o, e = run(p)
ok(e == "%s:2: non-numeric unit_price '1e3'\n" % p and c == 2, (c, e))
