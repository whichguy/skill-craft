import os
from _lib import *
p = f(HDR + row('1', 'inf'))
c, o, e = run(p)
ok(e == "%s:2: non-numeric unit_price 'inf'\n" % p and c == 2, (c, e))
