import os
from _lib import *
p = f(HDR + row() + b"\xff\n")
c, o, e = run(p)
ok(o == "", o)
