import os
from _lib import *
a = f(HDR + row()); m = os.path.join(D, "nope.csv")
c, o, e = run(a, m)
ok(o == "" and c == 1, (c, o))
