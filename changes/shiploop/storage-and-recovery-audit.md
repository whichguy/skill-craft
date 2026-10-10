---
bump: patch
---
Reject conflicting transaction destinations, case/Unicode aliases and journal
aliases before writes; sync nested directory entries during writes and recovery;
and consistently reject malformed JSON/UTF-8 records. Keepalive status reads
now refuse busy or unrecovered runs without mutating them. Callback errors
point to durable recovery without assuming the run is active or unchanged.
Document the persistence boundaries and supported runtime requirements.
