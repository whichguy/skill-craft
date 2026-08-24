# Validate the spec

Before interpolating `/devloop` argv, prove the ask has a **machine-checkable
done** sentence. This is the Before overlay. It is **not** the `c-plan`
clarifier and **not** c-thru `/cplan`.

**Checkable** means a later `verify_cmd exactly [...]` can pass or fail
without a human judging: exact file contents, a hosted module + live
oracle, or an executable test the user named.

**Not checkable:** “make it better”, “fix the bug” with no observable,
subjective design, or a missing success signal.

**If not checkable:** **stop and ask**, or run optional `define-done` /
`backchain` to write a done sentence, then re-enter `/devloop`. Do not
invent `pytest`, a path, or a cwd. Do not invoke `c-plan` or `/cplan` as
this overlay.

**If checkable:** continue the handshake (MCP → dest → interpolate → exec).
Do not require `define-done` on every run.
