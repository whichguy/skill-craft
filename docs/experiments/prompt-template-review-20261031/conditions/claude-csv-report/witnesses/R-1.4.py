import os
from _lib import *
c, o, e = run()
ok(e.startswith("usage:") and e.count("\n") == 1, e)
