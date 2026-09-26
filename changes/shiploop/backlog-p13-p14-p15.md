---
bump: patch
---
A saved run without a recorded `lint` option is now refused with the fresh-run hint instead of being read as `off`; new runs always record the option. Run records containing U+2028, U+2029 or U+0085 in any text now read back correctly (the reader split lines on those characters). An isolated workspace's source fingerprint now hashes the index's staged entries rather than the raw index file, so a timestamp-only index rewrite no longer looks like a source change. Workspace manifests written with the old fingerprint are refused with instructions. Git commands in workspace operations honour `SHIPLOOP_GIT_TIMEOUT` (seconds, default 45).
