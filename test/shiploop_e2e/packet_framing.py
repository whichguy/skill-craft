"""Shared print markers used by the E2E packet readers.

The closing marker describes the observed tail only; its presence does not prove that the middle of a host view remained
visible. In particular, historical host views could retain a tail marker after eliding middle text.
"""

import re

# The closing line of every print (shiploop_navigator.HEAD_END; independent tests pin the production value). Since R4 of
# the run-5 batch (2026-10-24), the spelling is "print"; saved runs from 2026-10-16 through then keep the prior spelling.
HEAD_END = "=== end ShipLoop print ==="
HEAD_END_UNTIL_R4 = "=== end ShipLoop head ==="

# Match either closing marker only as a complete line. A packet's second pointer line names a marker in a sentence near
# the top of every print, so substring search can report a closing marker that a cut reply never actually reached.
HEAD_END_LINE = re.compile(r"^(?:" + re.escape(HEAD_END) + "|" + re.escape(HEAD_END_UNTIL_R4) + r")$", re.M)
