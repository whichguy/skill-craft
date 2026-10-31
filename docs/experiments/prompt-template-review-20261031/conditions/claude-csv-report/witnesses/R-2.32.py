import os
from _lib import *
p = f(HDR + row('1', '-.5'))
c, o, e = run(p)
ok(e == "%s:2: negative unit_price '-.5'\n" % p and c == 2, (c, e))
