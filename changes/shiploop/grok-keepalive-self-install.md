---
bump: minor
---
Keepalive now works on Grok without an installer. Grok lists a plugin's hooks but
never runs them, so the marketplace install left Grok runs with no keepalive. Any
`shiploop` command that runs under Grok now writes
`~/.grok/hooks/shiploop-keepalive.json` when it is missing, or repairs it when its
script is gone, and says so once on stderr. New Grok sessions load it; an open
session picks it up from `/hooks`, then `r`. `SHIPLOOP_KEEPALIVE=off` skips it.
