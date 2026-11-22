# Fix pass

`npm test` before the pass: 123 tests, 123 pass, 0 fail. After it: 127 tests, 127 pass, 0 fail. Every shortfall was
reproduced first. The four new tests are in `test/assignee.test.js`; each fails on the delivered source and passes with
the fix. No existing test was changed.

## Shortfalls

- **Repeated assignee filters return tickets that fail the second filter**: fixed, test `a filter given more than once
  lists only the tickets that match every value`. A filter given more than once must now match each of its values
  (`src/tickets/query.js`), for `status` and `priority` as well as `assignee`, following the request's "a ticket must
  match every filter given".
- **Operators have no documented route from an agent name to a notification destination**: product not changed. The
  request makes an agent a name and asks that the agent be notified; turning a name into a mailbox would need a
  directory of agents, a new feature. Documented instead (below).
- **The CLI displays an accepted assignee as unassigned**: fixed, test `refuses the em dash the command line shows for an
  unassigned ticket`. The API refuses `—` as a name (`src/tickets/validate.js`, marker named `UNASSIGNED` in
  `src/format.js`), so `—` in `list` and `show` always means unassigned.
- **Unicode line breaks pass the single-line check and split raw CLI records**: fixed, test `refuses an assignee holding a
  Unicode line break, so list --raw keeps one line per ticket`. U+0085, U+2028 and U+2029 are refused in assignee names.
  Titles and requesters keep the 1.4.0 rule, since saved data files may already hold such titles.
- **An accepted assignee can be impossible to filter for**: fixed, test `refuses an assignee that is not well-formed
  Unicode, so every assignee can be listed by name`. A name with an unpaired surrogate is refused.

## Choices documented

Each was watched on the running service before it was written down.

- An impossible assignee search value (65 characters, a tab, `—`) answers 200 with no tickets; a bare `?assignee` is
  `?assignee=`; the value is not trimmed and case counts: `docs/api.md`, "List tickets".
- The assignee is kept through resolving, closing and reopening, and reopening sends no new assignment notification:
  `docs/api.md`, "Set a ticket's assignee"; `CHANGELOG.md`, 1.5.0.
- Unassigning sends no notification, and a notification already enqueued still goes to the agent it named when the
  ticket is unassigned or reassigned before the worker runs: `docs/api.md`, "Set a ticket's assignee";
  `docs/operations.md`, "Notifications".
- A delayed notification quotes the title as it was at the assignment: `docs/api.md`, "Set a ticket's assignee";
  `docs/operations.md`, "Notifications".
- The shortfall not changed: an assignment notification's `to` is the agent's name as assigned, the relay has to resolve
  it (or tickets are assigned by address), and `sent` means the line was written to `NOTIFY_FILE`, not that a mailbox
  received it: `docs/operations.md`, "Notifications"; `CHANGELOG.md`, 1.5.0.

The documents also describe the assignment change as it now behaves: the name rules and the refusals (`docs/api.md`),
the `—` marker and the raw fields (`README.md`, "Command line"), the start-up check of a ticket's assignee and the
assignment notification's key (`docs/operations.md`), and the release record (`CHANGELOG.md` 1.5.0, `package.json`
version 1.5.0, as `CONTRIBUTING.md` asks).
