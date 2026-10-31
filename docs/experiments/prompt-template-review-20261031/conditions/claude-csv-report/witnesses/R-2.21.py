import os
from _lib import *
p = f(HDR + row(" 7 ", "1"))
c, o, e = run(p)
ok((c, e, js(o)["by_product"]) == (0, "", {"widget": 7}), (c, o, e))
