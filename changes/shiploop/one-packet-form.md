---
bump: minor
---
There is one packet form. `next --brief`, the short repeat packet, the per-run `rules.md` and `last-packet.json` display records and the Claude `SessionStart` compaction hook (`shiploop-keepalive-compacted`) are removed: every packet, including every `next`, prints in full, so nothing depends on what a host kept from an earlier packet. The Improve change gate's check that a one-pass review really left the candidate unchanged now runs; it previously failed silently and never refused.
