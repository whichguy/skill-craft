---
bump: minor
---
Below its Python minimum (3.15), ShipLoop no longer refuses when a newer Python is installed: the CLI and its hook
entries run themselves again with the newest `python3` or `python3.N` on PATH that is 3.15 or newer, keeping their
arguments, interpreter options and stdin, and refuse only when there is none (the CLI with one line and exit 2, a hook
event silently). This is the ordinary case in a macOS login shell, which puts Apple's `/usr/bin/python3` 3.9.6 first.
The skill card now says to start the CLI with `python3` even when `python3 --version` is older, instead of checking the
version and stopping.
