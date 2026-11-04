---
bump: patch
---
The entry card no longer asks the model to paste a status line. Measured over 116 recorded runs, no run ever did
(0 of 116): the status line reaches the user from the packet and the host status hook, or from the next narrative, so
asking for ~17 pastes per run was an instruction nobody could follow. The card now says to show the narrative at a
milestone as its first line says, leave the status line to the host hook, and compose no progress sentence of its own;
the detail moved to the status-display reference, which also now states the narrowed milestone set so it matches the
code again.
