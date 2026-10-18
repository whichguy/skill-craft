---
bump: minor
---
A check command now runs from the step that finishes its criteria, not after every step. In the Salesforce chess run
the step plan had three steps (engine, controller, board); the only check was a grep for the board files, it was
listed on the first step's implement packet, it could not pass there, and the revise merged all three steps into one,
so one implement and one Improve review ran instead of three of each. A check naming `criteria` is now due from the
last step that lists one of them, and later checks are named on the packet as due at their step; a check with no
criteria (lint, type, build) still runs after every step. The step-plan duty and the implement exit condition say so.
