import os
from _lib import *
c, o, e = run(f(HDR + row("3", "1", "north", "widget") + row("1", "1", "south", "widget") + row("2", "1", "north", "gadget")))
ok(js(o)["by_product"] == {"gadget": 2, "widget": 4}, o)
