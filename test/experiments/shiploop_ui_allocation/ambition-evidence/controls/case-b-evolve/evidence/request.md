# Controlled request — B: consequential compatible evolution

Plan **W1 only** for Field Notes: evolve the read-only account-scoped export
activity companion into a highly legible, expressive mini-explorer. A person
should be able to move from a compact status summary to an expanded in-place
activity view with a sense of visual continuity, then return to their note
without losing selection, editor focus, dirty text, reading position, or an
important asynchronous change.

The desired quality bar is intentionally high: clear state hierarchy, polished
component composition, responsive narrow-layout behavior, purposeful feedback
when an authoritative status actually changes, and accessible keyboard and
reduced-motion paths. It must remain truthful about the supplied GET-only data;
it cannot fabricate progress, timestamps, delivery, an operation retry, or a
new server action. Errors and stale data need a persistent readable state and a
read-only refresh action rather than a disappearing toast.

The current manual DOM/CSS baseline has no accepted shared transition/motion
contract for this kind of compact-to-expanded view. Evaluate whether it should
be evolved with the existing primitives or whether a compatible native-platform
upgrade merits a target-fit probe. Do not assume that a prospective API,
framework, package, or hosted capability is available. The scope is still only
the supplied read-only GET status observer; export requests, downloads, drafts,
storage, sockets, a server, or an unrelated framework migration are outside W1.
