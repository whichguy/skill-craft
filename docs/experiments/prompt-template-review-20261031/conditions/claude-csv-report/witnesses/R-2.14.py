import os
from _lib import *
p = f(HDR + row('1', 'nan'))
c, o, e = run(p)
ok(e == "%s:2: non-numeric unit_price 'nan'\n" % p and c == 2, (c, e))
