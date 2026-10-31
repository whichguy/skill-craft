import os
from _lib import *
n = f(HDR + row()); h = f(HDR)
alone = run(n)
ok(alone[0] == 0 and run(n, h) == alone and run(h, n) == alone, (alone, run(n, h), run(h, n)))
