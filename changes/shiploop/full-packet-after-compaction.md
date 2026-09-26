---
bump: patch
---
On Claude, the plugin adds a `SessionStart` hook with the `compact` matcher. After the host compacts a bound session, the hook clears the run's last-packet record, so the next `next` prints the full packet with the run rules instead of the short repeat packet.
