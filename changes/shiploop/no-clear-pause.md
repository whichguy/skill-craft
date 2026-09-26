---
bump: minor
---
A run no longer stops at the start of each work item. The `select-work` packet
used to ask for a context clear and, since no host lets a packet, script or hook
clear the conversation, offered a "context-boundary" pause that left the user
to type `/clear` and two recovery commands before every item. Every inline
stage now continues in the same conversation and the host's own compaction
manages context; an ask-agent producer without a usable fresh worker runs in
the conversation too. No packet offers a pause for a clear, and serial chains
no longer have a manual-handoff route.
