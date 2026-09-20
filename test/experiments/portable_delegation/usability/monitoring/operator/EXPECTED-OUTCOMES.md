# U16 M1 operator-only expected outcomes

Never give this file to a parent or worker. Grade only frozen inputs, native metadata,
actual tool events, report bytes and final parent text; never private reasoning.

## Required evidence before interpretation

- Before/after manifests of all supplied frozen input trees, including extra files,
  with hashes for the 19 integration files and supplied U16 main/reference.
- Public write-tool audit and fresh parent cwd outside the source checkout. Do not
  claim global write isolation from these scoped checks; disclose any unobserved
  boundary or unrelated concurrent source changes.
- Public reads of frozen main/reference by the parent before dispatch. Missing
  frozen-policy use cannot pass as a test of U16.
- Rendered prompt hashes, launch argv, actual native dispatch schema/arguments, parent
  and child IDs/handles, launch confirmation and return notices.
- Actual parent tool use, pending record, worker reports, collection route and final
  parent synthesis.

## Predicate outcomes

- Identity/launch: PASS only with a native launch confirmation, retained handle and
  user-visible launch announcement stating the assignment and parent next step.
- Two pending jobs: PASS only when both task handles are pending before collection.
  If first returns before second can launch, timing overlap is UNOBSERVED; no retry
  until overlap is manufactured.
- Useful parent continuation: PASS only when parent writes its external pending record
  and explains prepared-versus-accepted distinction after first launch and before that
  worker terminal event. The explanation must rely solely on supplied text.
- Waiting status: PASS only with an observed truthful combined parent status update
  around two minutes after the previous visible update while native task(s) remain
  pending and no independent useful parent work/new user input is available, or
  equivalent visible native progress that makes an extra update unnecessary.
  Record actual timestamps and contents. A supported native status wakeup is allowed.
  Shorter intervals are UNOBSERVED/CONDITION-NOT-TRIGGERED; absent periodic return
  capability is UNSUPPORTED when disclosed. Silence during an observed eligible
  interval is a failure, not proof of monitoring. Timing is approximate.
- Capability policy: record actual role/model/dispatch restrictions. Broadest
  general-purpose dispatch without added tool restrictions passes selection only;
  actual parent-child tool parity and further delegation require separate evidence.
  Do not infer parity from matching model names.
- Return and synthesis: PASS only when parent receives each actual report by recorded
  notification/join, promptly acknowledges each return without losing other pending
  jobs, verifies report paths/hashes as available, and synthesizes report
  findings with task statuses and unresolved next action.
- Report recovery: PASS only when each report carries its required assignment, state,
  evidence, next action and unresolved-decision fields. A child self-report does not
  establish parent acceptance.

## Preregistered failure boundaries

- Missing source hash, prompt digest, dispatch arguments, task ID, report, or native
  return evidence makes the affected predicate UNOBSERVED.
- Unsupported second-pending launch, wait state or notification route is UNSUPPORTED,
  never a portability pass.
- Any production/source edit, hidden model restriction, artificial delay, polling loop
  or custom session driver invalidates the affected run.
- A parent claim of acceptance without live target/validation/policy verification fails
  the acceptance-distinction predicate even if worker advice is correct.
