import os
from _lib import *
# a first line that looks like a valid data row is still the header: skipped, not counted
p = f(b"a,b,c,5,5.00\n" + row())
c, o, e = run(p)
ok((c, e, js(o)["rows"]) == (0, "", 1), (c, o, e))
