import os
from _lib import *
p = f(HDR + row(product=""))
c, o, e = run(p)
ok((c, e, js(o)["by_product"]) == (0, "", {"": 3}), (c, o, e))
