import os
from _lib import *
m = os.path.join(D, "adir"); os.mkdir(m)
c, o, e = run(m)
ok(e.startswith("report.py: error: cannot read %s:" % m), e)
