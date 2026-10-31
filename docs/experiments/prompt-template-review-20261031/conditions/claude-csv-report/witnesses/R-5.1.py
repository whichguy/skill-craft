import os
from _lib import *
m = os.path.join(D, "missing.csv")
c, o, e = run(m)
ok(e.startswith("report.py: error: cannot read %s:" % m), e)
