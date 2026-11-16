---
bump: major
---
ShipLoop now requires stable Python 3.15 or newer instead of Python 3.9.
Unsupported interpreters still get one CLI error (exit 2), while host hook
events remain silent (exit 0). CI follows the latest stable Python with
`3.x` and `check-latest: true`, without pinning a patch release.
