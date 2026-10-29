---
bump: minor
---
A session can take over a ShipLoop run at once when the session that owned it is dead, instead of waiting 30 minutes.
- When a session claims a run, the keepalive records the host session's process and its start time: the nearest
  ancestor of the hook that is not a shell or launcher, when it started at least 2 seconds before the hook.
- Another session takes the run over as soon as that process is gone or its pid has been reused, for example after a
  crash or a killed terminal.
- A live owner keeps the run however quiet it is (one long command sends no hook events) until 30 minutes pass, as
  before. Where no host process can be found, only the 30 minutes free a claim, and the owner's next hook looks again.
- A session resumed in a new process updates its own record.
