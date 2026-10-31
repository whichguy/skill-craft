import os
from _lib import *
n = f(HDR + row()); z = f(b"")
alone = run(n)
ok(alone[0] == 0 and run(n, z) == alone and run(z, n) == alone, (alone, run(n, z), run(z, n)))
