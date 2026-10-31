import os
from _lib import *
p = f(HDR + b'2024-01-01,"no\nrth",widget,1,1.00\n2024-01-01,north,widget,abc,1\n')
c, o, e = run(p)
ok(e == "%s:4: non-numeric units 'abc'\n" % p and js(o)["rows"] == 1, (e, o))
