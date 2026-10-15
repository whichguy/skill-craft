---
bump: patch
---
Second script quality pass: `shiploop_quality` no longer lists in `__all__` (or its
docstring) helpers it does not define, so `from shiploop_quality import *` works again.
Progress-data read errors now name the file and its size limit, and a malformed dry-run scenario
reports its type.
19 more private functions have docstrings that were checked against their code by two
independent reviewers.
