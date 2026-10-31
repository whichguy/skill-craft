import os
from _lib import *
os.makedirs(os.path.join(D, "sub"), exist_ok=True)
f(HDR + row() + b"2024-01-01,north,widget,3\n", "sub/a.csv")
c, o, e = run("sub/a.csv", cwd=D)
ok(e == "sub/a.csv:3: expected 5 columns, got 4\n", e)
