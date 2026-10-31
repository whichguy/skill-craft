import os
from _lib import *
c, o, e = run(f(HDR + row("1", "1.234")))
ok(js(o)["by_region"] == {"north": 1.23}, o)
