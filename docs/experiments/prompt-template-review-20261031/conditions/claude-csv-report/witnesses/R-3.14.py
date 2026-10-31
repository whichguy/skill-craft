import os
from _lib import *
c, o, e = run(f(HDR + row("3", "1") + row("1", "1")))
ok('"by_product": {"widget": 4}' in o, o)
