import os
from _lib import *
# exact decimal sum 0.335 rounds to 0.34 (half-up and half-even agree); a float accumulation gives 0.33
c, o, e = run(f(HDR + row("1", "0.3") + row("1", "0.035")))
ok(js(o)["revenue"] == 0.34, o)
