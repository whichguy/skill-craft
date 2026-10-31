import os
from _lib import *
c, o, e = run(f(b""))
ok((c, o, e) == (0, EMPTY, ""), (c, o, e))
