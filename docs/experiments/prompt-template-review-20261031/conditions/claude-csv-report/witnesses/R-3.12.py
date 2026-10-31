import os
from _lib import *
c, o, e = run(f(HDR + row("3", "2.50", "north", "widget") + row("1", "0.10", "south", "gadget") + row("2", "1.00", "north", "gadget")))
ok(js(o)["by_region"] == {"north": 9.5, "south": 0.1}, o)
