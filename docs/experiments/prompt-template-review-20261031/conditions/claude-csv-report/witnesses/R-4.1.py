import os
from _lib import *
import re
p = f(HDR + row() + b"2024-01-01,north,widget,3\n")
c, o, e = run(p)
ok(re.fullmatch(re.escape(p) + r":[0-9]+: expected 5 columns, got 4\n", e), e)
