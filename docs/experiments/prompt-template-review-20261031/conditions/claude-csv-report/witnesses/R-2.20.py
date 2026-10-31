import os
from _lib import *
p = f(HDR + row(" abc ", "1"))
c, o, e = run(p)
ok(e == "%s:2: non-numeric units 'abc'\n" % p, e)
