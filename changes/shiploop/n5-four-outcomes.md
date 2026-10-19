---
bump: minor
---
- **Four outcomes:** a stage result is now `done`, `blocked`, `send-back` (was `revise`: a record an earlier stage wrote is
  wrong, and the item goes back to its step plan with this result as evidence) or `add-work` (was `replan`: product work
  is missing; the new items are built, then the run resumes at system-test-author). `repeat` is retired: it was unused,
  and `next` reprints a stage. A result that names a retired outcome is refused with the new names.
- **Blocked:** a blocked result carries `awaiting`, the thing it waits on, and `blocked_by` is retired and refused. It is
  one of three kinds:
  - a person's decision: `{"kind": "answer", ...}`;
  - a person's action, such as a sign-in or a grant: `{"kind": "present", ...}`;
  - new, an outside service: `{"kind": "service", "service", "check", "no_default"}`, where `check` is a read-only
    command that exits 0 once the service is back.

  Resuming a blocked run takes the reply: `--answer` or `--observed`.
- **Waiting on a service:**
  - The status line and the narrative show "Waiting on a service", not "Waiting on you".
  - The blocked packet tells the model to run the check only when the user says the service is back or asks, and to
    resume with the check's output once it exits 0. Answer and present waits still say "do not answer it yourself".
  - The status text keeps URLs whole. A check such as `curl https://host/health` used to print as `https:health`.
- **Improve:** it starts only on a `done` result. A blocked, send-back or add-work result goes straight to its route.
- **Send-back limit:** `complete --check-only` now refuses a send-back once the work item has used its two.
- **Loop text:**
  - The implement loop's stop rule routes a person's or a service's action (access, authority, a decision) to blocked,
    and a step that cannot be done as planned to send-back.
  - A loop still running from another contract is reported as still running, with its `next_argv`, instead of being
    told to start again, which the runtime would refuse.
- **Check-only:** its success line says to submit once the loop's receipt is complete or stopped.
- **State version 8:** a run saved at an older version is refused; start it again.
