import os
from _lib import *
ok(os.geteuid() != 0, "cannot test permissions as root")
p = f(HDR + row()); os.chmod(p, 0)
c, o, e = run(p)
os.chmod(p, 0o644)
ok(e.startswith("report.py: error: cannot read %s:" % p), e)
