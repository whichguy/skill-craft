---
bump: minor
---
New `improve-pass` verb: after each Improve review pass the model writes `review-<n>.md` and runs it; ShipLoop checks
the recorded improve-skill call before any runtime `done` exists, commits the pass's edits, writes `checks.md` for an
unchanged tree (and refuses one older than the last edit), composes the runtime report and prints the runtime's `done`
and the stage's `complete`, literal and absolute. `complete` writes `RUN/improve/<action>/passes.md` at import, and its
skill-call refusal of an ended loop names `improve-start --restart-stopped`, which now restarts such a loop. The
implement-step review focus gains a bullet for an unexercised language or library behaviour.
