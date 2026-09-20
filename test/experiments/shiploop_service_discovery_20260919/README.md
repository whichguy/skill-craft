# ShipLoop service-discovery semantic fixtures

This small, opt-in offline fixture generator exercises the first ShipLoop
service-discovery guidance with four fresh-context cases: remote CRM discovery,
cold step planning from a maintained decision, local password-authentication
logging, and a local-only formatter control. It does not launch an agent, call an
MCP server, use a credential, or touch a remote account.

Run it from the skill-craft checkout with a new directory outside the source
checkout:

```sh
python3 -B test/experiments/shiploop_service_discovery_20260919/prepare.py \
  --output /tmp/shiploop-service-discovery-fixtures
```

The generator freezes the current ShipLoop packet scripts, SKILL.md, and Markdown
references under source-snapshot/. It deliberately copies only Python scripts,
the shiploop launcher, and Markdown references, so transient *.cover, bytecode,
and other generated files are excluded. It renders each packet through the active
Navigator v3 source at preparation time, but routes reference locators to that
frozen package snapshot so a later reader can inspect the exact guidance bytes
used for the packet.

Each cases/<name>/participant/LAUNCH.md tells a fresh participant which workspace
and rendered PACKET.md to use. Give that participant only the launch material, its
workspace, packet, and frozen source snapshot. The fixture is an ordinary
filesystem layout, so withholding the other cases and evaluation/ is an operating
discipline, not an access-control boundary. The expected outcomes live separately
in evaluation/expected-outcomes.json; they are for an independent evaluator and
must not be placed in a participant prompt.

The packets are saved/reloaded Navigator v3 states. Their preceding transitions
and Improve receipts are explicitly synthetic traversal setup used to reach a real
rendered discovery or step-plan packet. They do not prove an agent, callback,
Improve campaign, cache, authorization check, or remote operation ran.
Participants write only REPORT.md and stop; they must not submit a callback or
modify fixture product files. Every workspace has a tiny passing unittest baseline
to make the discovery duty concrete. That smoke check is intentionally narrow and
is not evidence of remote behavior or authorization correctness.

The generated manifest.json records the source revision/dirty state, hashes of the
frozen source and participant inputs, packet hashes, and fixture paths. It supports
a repeatable bounded exercise without adding a general benchmark runner or a new
ShipLoop runtime mechanism.

See [recorded results and limitations](RESULTS.md) for the eight actual reader
reports, prompt refinements, mechanical checks, and broader-suite failures.
Prepared cases are not counted as executed cases.
