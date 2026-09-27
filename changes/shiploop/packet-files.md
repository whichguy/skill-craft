---
bump: minor
---
Packets now live in files. For an active run, ShipLoop writes the complete packet to `<run>/packets/<action>.md` and prints only a short head: the callback, goal and done-when, the result contract, the packet file's path, recovery and pause commands, the keepalive marker and the status block (about 3 KB instead of 20-50 KB). The host reads the file on demand and consults only the reference sections a step needs, instead of printing whole packets that Grok cut at about 20 KB and reading whole reference files into context. Paused, blocked, awaiting, halted and done packets still print whole. `next` rewrites the file and reprints the head.
