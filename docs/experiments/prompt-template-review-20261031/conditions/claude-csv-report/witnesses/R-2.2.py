import os
from _lib import *
p = f(b"a,b\n" + row())
c, o, e = run(p)
ok((c, e, js(o)["rows"]) == (0, "", 1), (c, o, e))
