import os
from _lib import *
c, o, e = run(f(HDR + row("1", "2.675")))
ok(js(o)["by_region"] == {"north": 2.68}, o)
