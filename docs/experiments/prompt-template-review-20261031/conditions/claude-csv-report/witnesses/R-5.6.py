import os
from _lib import *
m = os.path.join(D, "missing.csv")
c, o, e = run(m)
ok("Traceback" not in e and "cannot read" in e, e)
