---
bump: minor
---
A packet carries one progress block instead of the status block and the narrative side by side (packet review F6:
28 of 36 packets of a live run carried both, and they said the same).
- A milestone packet carries the run narrative only. Every other producer packet carries one status line,
  `Where: … · Next: …`, the status block's Where and Next rows. `status.md` and `shiploop status` keep the full block
  unchanged.
- An Improve packet carries neither. Before, 8 of 11 Improve packets repeated the narrative of the stage they reviewed:
  the milestone test reads the last accepted step, and an Improve child does not change it until it completes. An
  Improve child's packet is no longer a milestone; a stopped run still is.
- The Claude Code status hook reads the narrative or the status line from the packet. It shows the narrative at a
  milestone and a two-line summary otherwise (`ShipLoop ▶ <where>` and `Next: …`; `shiploop status` still adds what
  finished). Its shell gate now starts on a packet header or a status block.
- The last accepted transition in the packet file prints its summary even when it is as short as a headline. That
  summary was left out because the Done row showed it, and the Done row has left the packets.
