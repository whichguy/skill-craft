import os
from _lib import *
c, o, e = run(os.path.join(D, "missing.csv"))
ok(o == "", o)
