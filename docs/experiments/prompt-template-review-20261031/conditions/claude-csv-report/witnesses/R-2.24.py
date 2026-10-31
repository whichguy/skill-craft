import os
from _lib import *
p = f(HDR + row(region=""))
c, o, e = run(p)
ok((c, e, js(o)["by_region"]) == (0, "", {"": 7.5}), (c, o, e))
