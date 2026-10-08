---
bump: patch
---
The pass-log line in every packet and in the run context index is now one conditional rule that stays true whether or not the log exists: create it when the pass starts, append after each pass what you checked and what is left, and after a reset open it first if it exists. The durable-files reference now says which source is authoritative for the notes, inbox and results copies and for test commands.
