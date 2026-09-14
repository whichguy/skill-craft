# ShipLoop research-pilot fixes

Status: implemented and reviewed; deliberate deferrals remain listed below.
Implementation baseline: `e1184ee`, 2026-09-13. Scope: the user-approved
recommendations from the two-scenario research pilot, not a game implementation
or a new investigation engine. Current operator guidance lives in the
[README](../skills/shiploop/README.md#research-packets-unanswered-decisions-and-safe-revisions).
The original pilot records remain unchanged under the local directory
`/Users/dadleet/src/shiploop-research-pilot.VAOtEA/` (`REPORT.md`,
`evaluator/REPRODUCED-PACKET-FINDINGS.md`, `evaluator/INTERVENTIONS.md`).

## Prompt audit and approved plan

### Q1 — Is the failure semantic or a mismatched submission contract?

**Info-gain: 0.95.** At the baseline, `_planning_template`
(`shiploop_packets.py:762–787`) renders only the legacy question/source shape,
while `_base_research_state` (`shiploop_system_context.py:125–180`) requires
question links and system context for new runs. Both pilot draft workers needed
schema assistance. Invalid scope lists also escape the intended error class at
`shiploop_system_context.py:545`.

**Answer:** make the rendered shape version-correct, supply a required complete
schema reference, and normalize malformed enum diagnostics. Keep the existing
validators, identity/link gates, result transport and state transitions.

### Q2 — Does more investigation resolve an unavailable owner decision?

**Info-gain: 0.90.** All four pilot arms retained open questions. At baseline,
the research commit/finalize handlers (`shiploop_protocol.py:4039–4130`) treat
unresolved questions as a convergence blocker regardless of new discovery.

**Answer:** clarify the next useful action in existing fields: inspect a missing
fact, request an owner decision/authority, or carry an established requirement
to its later consumer. A future implementation is not a substitute for an
unanswered prerequisite. Preserve blocking semantics and safety expectations.

| Priority | Remediation | Acceptance |
|---|---|---|
| HIGH | Version-correct draft/apply examples and complete selected schema reference | Current/legacy shape tests; current examples validate structurally but remain unresolved; public-CLI submission, rejection/retry and apply coverage. |
| HIGH | Safe field-specific enum errors | String/list/object/null negatives across every enum in the affected module; expected type/values without raw payload leakage. |
| MEDIUM | Immutable identity, reciprocal-link and decision-boundary guidance | Executable example/transition tests; existing open-question and two-pass gates remain intact; independent prompt/contract review. |
| MEDIUM | Register tests and synchronize derived ShipLoop package | Scoped CI entrypoint, package parity and regression checks. |

The last seven commits informed the plan: retain reset-safe references, separate
record acceptance from semantic success, preserve legacy contracts, keep total
packet size advisory, and do not reopen deliberately deferred integrations.
Use native Python/CLI tests rather than the illustrative npm commands in the
prompt-migration guidance. Test before changing prompts, then align the prompt,
documented shape and real validator. No new dependency is needed.

## Dispositions

- **Implement:** the reproduced schema/diagnostic fixes and narrow generic
  decision guidance. Keep review → history-informed plan → apply → verify →
  verbose learning commit under the embedded Until policy.
- **Retain as candidate:** universal consequence-expansion wording. One tie and
  one narrow preference do not establish a general improvement, especially with
  seeded setup, operator assistance, source-label contamination and memory
  exposure. This change does not silently roll out that experimental paragraph.
- **Local validation:** exercise intake/survey/research with the fully specified
  existing hermetic fixture, rejected-callback non-advancement and the successful
  two-trivial-pass finalization path. These are deterministic contract checks,
  not an unaided live-environment discovery claim.
- **Deferred experiment:** explicitly scoped existing product repo plus read-only
  live target/tool registry, controlled memory-isolated inputs and downstream
  consumption. A selected target and authority are not supplied here. No new
  MCP server, credentials, remote deployment or account configuration is added.

## Validation closeout

### Deterministic checks and review

The new regressions were written first: the current-version template failed the
real validator; legacy shape passed. The enum matrix reproduced malformed
string/list/object/null failures, including raw type errors, before the guard.
The implemented direct-template suite has five methods; the public-CLI suite
has three, and the system-context suite has eight (including 28 malformed-enum
subcases). The CLI fixture exercises real intake, approach and survey before
research, fills the printed result, submits its exact callback, refuses malformed
scopes without advancing, preserves a blocked owner question after an audited
pass, and reaches behavior after two verified trivial passes plus final checks.
It does not infer a final delivery from reaching behavior.

An early snapshot `ed67211` caught a test-harness learning-string mismatch: the
test's audit commit did not include its actual apply learning verbatim. The
production gate correctly rejected it. The corrected test and otherwise
unchanged source are pinned at `c0487f9c8a3684a937afff6ef58bed3b46d4fb53` for the
broader regression run. Detached-checkout index initialization was also repaired;
that repair changed no source bytes or user checkout. No passing claim is based
on the early failed aggregate run. Logs are retained under the local temporary
directory `/tmp/shiploop-research-validation.JWMZnQ/`.

Independent review caught the initial test fence-parser escape and an overbroad
README claim about enum errors. Both were corrected; the second scoped review
found no remaining material issue. Prompt/validator alignment preserves all
phase names, version gates, immutable identity and reciprocal-link checks.

The dedicated full-workflow entrypoint `bash test/shiploop-walk-journal.test.sh`
passed all 13 methods, with its trailing `EXIT=0`, on `ed67211`. Its entire
runtime, fixtures and walk test are identical to `c0487f9`; the only tree delta
is the unrelated new CLI test's corrected audit-learning string. Count this
walk once, not again if the aggregate reaches the same suite.

Final coverage is **487 distinct passing test methods across all 46 ShipLoop
suites**, assembled from two source-matched runs:

| Run | Verified result |
|---|---|
| Main regression, `c0487f9` | The first 45 suites completed successfully: 474 methods, including all research, planning, Until, local-plan, recovery and contract checks. |
| Dedicated walk, `ed67211` | 13 workflow methods passed with `EXIT=0`; runtime and walk inputs match the main snapshot exactly. |
| Combined-log/source audit | Verified every expected suite name, successful unittest summary, method total and the single unrelated snapshot delta; `combined-validation.log` ends `EXIT=0`. |

After those 45 main suites completed, the aggregate started the same walk
already passed by the dedicated command. That duplicate was intentionally
interrupted; `verified-shiploop.log` preserves its `KeyboardInterrupt` and
`EXIT=130`. This is **split suite coverage, not an uninterrupted successful
`bash test/shiploop.test.sh` invocation**. No failed or interrupted test is
counted as passing. The earlier failed harness run is retained separately.

Scoped Ruff, shell syntax, native metadata validation (17 skills), 133 local
Markdown link destinations and ShipLoop plugin parity passed. The optional
skill-creator validator cannot start because PyYAML is absent; no dependency
was installed. The final implementation differs from the main tested snapshot
only in audit-closeout prose; runtime, prompts, references and tests are unchanged.

### Fresh-reader forward test

One fresh conversation received only the isolated run locator and CLI entry,
then followed the actual research packet and its selected materials. It needed
no operator schema hints and did not inspect validators. The first callback
was rejected because one `origin` did not name prompt/spec/discovery. The host
corrected that field using the existing diagnostic and selected schema guide;
the second callback was accepted, and the host stopped at `research-review`.
The accepted v1 record retained an open owner question rather than fabricating
the fixture's domain, entity vocabulary or acceptance examples.

The corrected origin was
`discovery: selected testing and documentation guidance requires concrete lifecycle risk-policy decisions.`
Before the error it began `selected testing and documentation guidance:` without
the required origin category. This is a self-corrected instruction-following
miss, not evidence for loosening the origin gate or claiming first-try success.

The durable smoke fixture is temporarily retained at
`/var/folders/_n/cth41tgs171367b_gghs0kgm0000gn/T/shiploop-planning-evt0kd6c/repo/.shiploop/`.
`state.md` records accepted research action
`20260914T011825Z-0b9ce5e2-14b3269c618d`, result digest
`4a57896d58ac3cd1eb901ab1c056abea17978129c4b6d04ecefec1b2f37aefcb`,
and current stage `research-review`. The result is in that action's inbox file
and `research-evidence.md`; no research certificate or game exists.

Automatic memory-summary material was supplied despite the no-lookup brief.
The host reported no memory lookup; that does **not** establish memory-isolated
inputs. This one local attempt is not a live-environment discovery experiment,
A/B superiority claim, complete delivery test or universal semantic oracle.

## Contract, alignment and interoperability review

**Classification:** script-backed. **Contract (Layer 0):** the existing
versioned result schemas and exact callback remain authoritative; no transition
or permission is added. **Prompts (Layer 1):** packet, research guide and schema
reference now describe the selected validator. **Scripts (Layer 2):** one
packet-local template helper and a small type-safe enum helper, not a second
scheduler. **Binding:** package-relative readers and the existing CLI family;
no host-specific prompt copies or transport assumptions.

| Host | Verification scope |
|---|---|
| Grok | Installed ShipLoop path resolves to the canonical package; not a live Grok runtime test. |
| Codex | Installed ShipLoop path resolves to the canonical package; local CLI checks only. |
| Claude | Derived plugin view is synchronized and checked; no Claude runtime certification. |
| Hermes | No installation, refresh or runtime test performed; materialized-copy policy unchanged. |

**Findings/migration:** remove the legacy-only shape from the shared research
prompt, select the exact reference for both writers, and preserve the unchanged
review/plan/apply/verify/commit/finalize phase names and gates. The validator
selects schema authority; the prompt and tests are its consumers. No universal
prompt-expansion rollout, new runtime state or plugin installation is warranted.

## Learnings

1. A strict script-owned transition is only usable when the packet explains the
   exact selected input contract. Do not ask a fresh host to infer versioned fields.
2. An example can be structurally valid and intentionally unresolved. Never
   supply invented evidence just to make a template look ready.
3. Immutable identity is different from mutable semantics: improve error/state
   details without silently repurposing the operation or source.
4. An unchanged owner blocker and a newly discovered risk both prevent exit, but
   they call for different next actions. Repeated citations cannot grant authority.
