---
bump: minor
---
ShipLoop's Python minimum is now what its code needs, Python 3.9, instead of 3.15: Apple's `/usr/bin/python3` on macOS
and the Python of older Linux releases run it as they are. The skill card states no Python version any more (it asks
for `python3` and `git` on PATH, and the CLI says so if its Python is too old); below 3.9 the CLI and hooks still run
themselves again with a newer `python3` or `python3.N` on PATH when there is one.
