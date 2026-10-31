import os
from _lib import *
c, o, e = run(f(HDR + row("1", "1", "south") + row("1", "1", "north") + row("1", "1", "east")))
ok(list(js(o)["by_region"]) == ["east", "north", "south"], o)
