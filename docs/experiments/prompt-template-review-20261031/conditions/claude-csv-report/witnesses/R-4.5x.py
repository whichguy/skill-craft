"""Extra probe (not a frozen condition): a bad record that itself spans two lines is reported on the line it starts on."""
import os
from _lib import *
p = f(HDR + row() + b'2024-01-01,"no\nrth",widget,abc,1\n')
c, o, e = run(p)
ok(e == "%s:3: non-numeric units 'abc'\n" % p, e)
