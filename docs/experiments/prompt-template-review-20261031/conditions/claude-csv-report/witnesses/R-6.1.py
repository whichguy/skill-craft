import os
from _lib import *
c, o, e = run(f(HDR))
ok(o == EMPTY, repr(o))
