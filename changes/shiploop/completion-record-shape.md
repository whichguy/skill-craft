---
bump: patch
---
The Improve child's `parent-return.md` now shows the completion evidence record's shape (a Markdown file with one `shiploop-state` JSON fence), as the packet already did. A record without that fence is refused with its path, the fence count, and the expected shape, instead of a bare "exactly one fence" message.
