import os
from _lib import *
p = f(HDR + row('-1', '1'))
c, o, e = run(p)
ok(e == "%s:2: negative units '-1'\n" % p and c == 2, (c, e))
