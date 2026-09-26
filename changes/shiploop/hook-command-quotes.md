---
bump: patch
---
The generated plugin hook commands are no longer wrapped in quotes. Grok runs
the ShipLoop plugin's hooks once its leader restarts, but it does not strip
quotes: it read `"…/shiploop-keepalive-observe"` as a file name inside the
plugin's hooks folder and failed every hook with "command not found". Commands
are now `${CLAUDE_PLUGIN_ROOT}/skills/shiploop/scripts/<script>` (and the Codex
and Cursor equivalents).
