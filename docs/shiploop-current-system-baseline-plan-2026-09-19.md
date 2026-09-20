# Current-system baseline implementation plan

## Outcome and scope

An existing repository or identified remote system without an adequate spec gets
a README-led recovered baseline during discovery. Research resolves consequential
gaps; the incoming change spec and plans reference that baseline. Maintained
product knowledge survives later requests without promoting observations to
approved requirements. Default navigator v3 keeps its existing graph, result
schema, Improve ownership and authority boundaries.

The preceding isolated pilot used a pinned public scheduler library, independent
extraction and cold-planning contexts, and two synthetic remote trials. It showed
useful preservation of concrete behavior and exposed an observation-to-requirement
overclaim. This implementation includes the strengthened evidence rule. Those
trials do not establish live MCP or full ShipLoop semantic execution.

## Dependency-ordered work

1. **Baseline and isolation.** Snapshot the current dirty checkout into an isolated
   worktree, retaining required untracked ShipLoop/Improve sources. Run existing
   v3 guidance and navigator tests before edits. Preserve original file copies
   for returning only this feature delta.
2. **Contract.** Add `references/current-system-baseline.md` for classification,
   README-first extraction, evidence/authority, remote-only documentation roots,
   prior/current/delta records, planning handoffs and persistence. Link it from
   the skill entrypoint, README, project-knowledge and requirements-definition.
3. **Consumers.** Add stage-selected guide locators and compact producer reminders
   in `shiploop_navigator_v3_prompts.py`: discovery, research, spec, test strategy,
   global/step plans, document/carry-forward, product acceptance and handoff.
   Improve reopens the selected prior baseline and delta with ordinary references.
   Do not change legacy schemas or synthesize semantic evidence in the runtime.
4. **Verification.** Add cold save/reload and relocated-package guidance tests,
   including the producer/Improve boundary and work-item context. Exercise
   existing runtime/packet and discovery regressions. Use a fresh model reader
   for the new guide's new/existing/stale/remote decisions; label this semantic
   smoke separately from deterministic tests and full E2E.
5. **Review and return.** Independently review the owned diff, reconcile findings,
   generate the ShipLoop plugin view with the repository script, and verify parity.
   Return only owned changes, preserving concurrent work and the source index.

## Definition of ready

- Existing README/spec/requirements roles and v3 stage ordering are located.
- Current smoke suites pass before implementation; failures remain prerequisites.
- The new contract uses existing Markdown notes, `evidence_refs`, work-item
  `context`, and actual Improve handoffs; no added state machine is needed.

## Definition of done

- Missing or inadequate baseline triggers bounded recovery; a new system does not
  acquire invented legacy behavior. Reuse is conditioned on scope and freshness.
- README promises remain distinct from code/tests/remote observations, including
  documented conflicts, access limits, skipped tests and synthetic evidence.
- Prior as-of evidence remains retrievable, the requested delta has explicit
  preservation decisions, and durable docs/indexes retain current knowledge.
- Cold producer and Improve packets expose valid selected guide paths; plan
  context carries the selected product baseline/delta, not just package guidance.
- Tests, scoped semantic checks, independent review and generated-package parity
  pass with limitations recorded. No live integration, publication or installation
  claim is inferred from these checks.

## Initial isolated validation

Baseline before edits: v3-guidance 19 tests passed; navigator-v3 22 passed.
Implemented the guide, source entrypoints, ten selected stage routes, producer
consumer reminders and actual Improve handoff. Added three focused guidance tests
and one bound-child runtime test. Independent review found no remaining actionable
findings after strengthening concrete artifact transfer and clarifying scattered
source facts versus a maintained account.

Checks against the initial implementation snapshot:

| Command | Result |
| --- | --- |
| `python3 -B test/shiploop-v3-guidance.test.py` | 22 passed; includes new lifecycle/relocation coverage |
| `python3 -B test/shiploop-navigator-v3.test.py` | 22 passed |
| `python3 -B test/shiploop-packet-bounds.test.py` | 7 passed |
| `python3 -B test/shiploop-discovery.test.py` | 27 passed |
| `python3 -B test/shiploop-reference-routing.test.py` | 8 passed |
| `python3 -B test/shiploop-actual-improve-cli.test.py` | 9 passed; includes real child cold recovery/import with distinct baseline/delta refs |
| `python3 -B test/shiploop-full-runtime.test.py` | 3 passed; full graph and package composition, synthetic review judgments |
| `python3 -B test/marketplace-package.test.py` | 27 passed after completing the isolated current harness/package snapshot |
| `bash scripts/sync-plugin-views.sh --check shiploop` | passed |

The initial expanded-runtime attempt lacked the working checkout's relocated E2E
harness; snapshot completion resolved that import failure. Package checks likewise
needed generated views for the current untracked Improve/E2E fixture sources. Those
setup corrections are not product changes and are not part of the returned delta.

Fresh-reader smoke covered existing/scattered, stale/conflicting, genuinely new and
remote-only hypothetical inputs. The first reader treated scattered facts as an
adequate baseline while still requiring a discovery record; the guide now explicitly
requires synthesis unless a reopenable account already exists. A separate fresh
follow-up correctly required the baseline before dependent planning. The guide also
makes current-request authority and ordinary in-scope design decisions explicit,
so missing historic approval cannot become a redundant request-confirmation gate.

That initial validation was scoped, not the entire monorepo aggregate, a live MCP read, a
model-driven full ShipLoop run, or multi-host runtime certification. Full-runtime
and Improve CLI tests prove transport/traversal using synthetic judgments; a
receipt does not prove semantic review. No commit, publication or installation was
performed during that phase. Source/index preservation was checked separately
during return.

Commands, before copies, owned diff, semantic decisions and review evidence are
retained in the external `shiploop-recovered-spec-impl-evidence-20260919` bundle;
none are run state inside the product package.

## Publication qualification

The owned feature delta was ported to a clean worktree at upstream commit
`0e6db6d8ade4ef3bf1593ded0d01f3259f57d78c`, then merged with upstream
`b6486f7a09eeafd5bd1e8478e4d4211a4ed3747a` to retain the newly published remote
test obligations. Unrelated shared-checkout changes remain excluded. ShipLoop is
versioned `0.18.8` with
generated plugin views, manifests and repository inventory synchronized. The
recovery guide uses the current upstream platform-discovery reference for remote
observations; it does not depend on an unpublished service-discovery guide.

Current-candidate checks:

| Command | Result |
| --- | --- |
| `python3 -B test/shiploop-v3-guidance.test.py` | 26 passed |
| `python3 -B test/shiploop-actual-improve-cli.test.py` | 10 passed |
| `bash scripts/sync-plugin-views.sh --check` | passed for all generated views |
| `python3 scripts/check-marketplace-packages.py` | 20 of 20 passed; offline payload validation |

Independent publication review found no remaining source/prompt behavior issue or
unrelated feature addition; source and generated ShipLoop payloads match. These
checks retain the earlier live-MCP, model-driven E2E and multi-host certification
limitations.
