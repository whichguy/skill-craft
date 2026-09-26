---
bump: patch
---
The keepalive no longer lets a busy run stop. Its progress check now counts
refused callbacks (the model is fixing and resubmitting) and each pass of an
active Improve review, not only accepted results, and a still-running host
background task (a deploy, an install) keeps the turn going with "wait for it in
this turn". Each stop counts the turn's continuations: near Grok's cap of 8 the
reason asks harder not to stop, and the log records "continuation N/8". A
refused callback now says the run is still active, and a second session gets a
notice naming the owner instead of a silent stop.
