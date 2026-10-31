import os
from _lib import *
c, o, e = run(f(HDR + row() + row("1", "0.10", "south")))
ok('"revenue": 7.6,' in o and '"north": 7.5,' in o and "7.60" not in o and "7.50" not in o, o)
