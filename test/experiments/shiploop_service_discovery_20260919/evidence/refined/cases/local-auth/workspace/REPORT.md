# Local password-auth diagnostics and logging discovery

## Observed scope and flow

The visible authentication flow is local and synchronous: a caller supplies
`username`, `password`, and a precomputed `valid` result to
`PasswordAuth.authenticate`. When `valid` is false, `PasswordAuth` emits
`login_failed` through its injected logger with `subject` and `method=password`,
then raises `PermissionError`; it does not issue a session. On success it calls
`sessions.issue(username)` and returns that result. The class is therefore the
observed owner of the application-level failure event and session transition,
but the fixture does not establish who validates credentials or binds the
logger. See `src/auth_service.py:1-11`.

The only operations contract says the structured `app.audit` logger is already
collected by an operator event sink; failed password attempts are ordinary auth
outcomes unless incident rules say otherwise, and passwords, tokens, and
session contents must not be logged. See `docs/operations.md:1-5`. No visible
source connects the injected `logger` to `app.audit`, configures the collector,
or exposes retrieval, retention, access control, or incident rules.

## Decisions and handoff

- **Reuse the present application event path.** Do not propose a new logger,
  audit store, broker, cache, or remote prerequisite. This follows the frozen
  service guidance's reuse-first rule and its warning against creating logging
  infrastructure merely for discovery
  (`source-snapshot/skills/shiploop/references/service-discovery.md:3-10,
  143-151`).
- **Preserve the current failure contract.** Any future instrumentation work
  should retain `login_failed`, `method=password`, the original
  `PermissionError`, and the no-session-on-failure behavior unless an accepted
  requirement changes them. `test_fixture.py:26-32` currently asserts only the
  event name and absence of issued sessions, so it does not characterize the
  structured fields or redaction.
- **Do not assume a success event is missing.** The frozen guidance calls for
  successful and failed login coverage, while warning against duplicating an
  identity provider's authoritative event. First probe the actual logger
  binding, identity-provider/platform coverage, and operator retrieval route.
  Only if that shows no adequate success coverage should a distinct,
  application-owned event be considered after successful session creation
  (`service-discovery.md:153-178`).
- **Treat safe diagnostic data as an explicit contract.** Passwords, tokens,
  and session credentials remain prohibited. `username` is currently recorded
  as `subject`; whether it needs sanitization, pseudonymization, or a retention
  limit is unresolved. Correlation identifiers, required-event filtering,
  sink-failure behavior, and any fail-closed audit rule are also unobserved
  (`service-discovery.md:162-172`).
- **No cache, async worker, remote API, or browser flow is evidenced here.**
  They are not applicable to this local fixture observation, not proven absent
  from the real service.

Likely future file roles are: `src/auth_service.py` for owned event emission;
`docs/operations.md` for the operational event/retrieval and redaction contract;
`test_fixture.py` for local characterization; `README.md:1-4` for the baseline
runner; and `SHIPLOOP.md:1-3` for linking a maintained decision when one is
accepted. This exercise made none of those product edits.

## Baseline and limits

Before any proposed edit, I ran from this workspace:

```
python3 -B -m unittest discover -v
```

Python `3.14.7` reported `Ran 1 test ... OK` (one passing failed-login test).
This is the deliberately narrow fixture smoke command required by
`README.md:3-4`, not service, identity-provider, sink, or consumer evidence.
The directory is not a Git repository (`git rev-parse` exited 128), so the
starting content identity is the SHA-256 values recorded below rather than a
revision:

```
README.md af10253f368d861c504ef2022ffc1b4516aed491c21d41a871a2f91ad403ebc2
SHIPLOOP.md 11502e8716a2ee70e75e5330f970f37f6b1b6c3b096fa129ab5c656ea8b54367
src/auth_service.py ae008e30cfb18d678d285194bdd1a2938349bb02b6f1e82bc6741bf8c741775b
docs/operations.md 4fad9670c7b435cde04d0115b627e85cc02f7b52db796e9198c0de2f2f67c0f6
test_fixture.py 834c51c4158f394a2ea59a2015e72f16f6b1ff8848bb4e6b7456f4bb9364d2e9
```

This complies with the frozen initial-baseline guidance's requirement to record
the command, content identity, outcome, and coverage limit when Git is
unavailable (`source-snapshot/skills/shiploop/references/execution-planning.md:3-30`).

## Required revalidation checks

1. Characterize the failure event's exact structured fields and prove a
   sentinel password/token/session value cannot reach the emitted details.
2. Establish the real `app.audit` binding, authorized operator retrieval path,
   retention/access policy, and whether provider coverage already records login
   success.
3. If an application-owned success event is justified, test it occurs only
   after successful session creation and does not duplicate the provider event.
4. Test required-event filtering and sink failure while preserving the original
   authentication error; the frozen guide identifies redaction, safe retrieval,
   and sink failure as distinct observability evidence
   (`service-discovery.md:209-227`).

No network, credentials, product edits, callbacks, or run-state changes were
used.
