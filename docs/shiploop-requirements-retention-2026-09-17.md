# Preserve product requirements across repeated ShipLoop runs

> Superseded 2026-09-26 by the owner's decision to keep each run's spec and environment knowledge in `docs/shiploop/`, committed at planning closes (see `skills/shiploop/references/project-knowledge.md#repository-knowledge-home` and `docs/shiploop-run-feedback-plan-2026-09-26.md`, S7).

## Decision and evidence

Use **one maintained product contract**, not a permanent copy of every run spec.
Reuse existing requirements/living-spec/API/policy homes. A tiny repository's
explicit README contract is sufficient; otherwise the fallback is
`docs/requirements.md`, linked from README and `SHIPLOOP.md`. Code describes
implementation; tests provide evidence against expected outcomes; neither may
silently redefine approved intent. Run-local specifications remain change plans.

This follows the bounded [initial incremental dry-run findings](shiploop-feature-contract-dryrun-2026-09-17.md):
retention matters when intent cannot be recovered from implementation, but that
pilot did not establish a need for a new workflow engine or prove repeated-run
retention. The default filename is a local design choice, not a standard.

Relevant primary references:

- [GitHub README guidance](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-readmes)
  treats README as the project entry point and supports links to longer docs.
- [Spec Kit spec-persistence models](https://github.github.com/spec-kit/concepts/spec-persistence.html)
  distinguish spec lifetime choices, including living intent with disposable plans.
- [OpenSpec existing-project guidance](https://github.com/Fission-AI/OpenSpec/blob/main/docs/existing-projects.md)
  supports documenting a touched slice and accumulating explicit feature deltas,
  rather than reverse-engineering an entire brownfield codebase first.

Do not install those tools. Contrary considerations: an extra doc can drift, a
README-only contract can work for a small project, and existing API/policy specs
may already be authoritative. Reuse first, keep accepted intent compact, update
only affected rules, retain verification gaps, and review via existing Improve.

## Inline audit and remediation plan

| Question / information value | Finding | Remediation / verification |
| --- | --- | --- |
| Does the script need another state store? High | Shared navigator render already supplies project knowledge/index to producer and actual Improve packets. | No state/DAG changes. Add a specific maintained-requirements section locator; test selected-package, current/cold and all-stage routing. |
| Can later work mistake old request scope for current product rules? High | Cross-run policy rejects replay, but "silently inherited old requirements" could also discourage preserving approved behavior. | Distinguish historical task queues from unaffected accepted product conditions. |
| Can documentation legitimize a bug? High | `document` describes updating docs from observed code/test results without explicitly separating normative intent. | Separate descriptive facts, accepted behavior, proposals and evidence; do not alter intent merely because implementation/tests agree. |
| Where do conditions survive deleted run folders? High | Existing persistence/index guidance does not name a durable behavioral home. | Existing contract first; otherwise `docs/requirements.md`, linked through README/index, outside transient state. |
| Are subclauses and supersession considered? High | A headline-only feature summary can lose cancel/error/privacy conditions. | Preserve/add/modify/retire affected conditions with source summaries and test locators; deliberate supersession, not wholesale rewrite. |
| Should every step reread every product feature? Medium | That increases token and maintenance burden without proportional evidence. | Relevant affected plus cross-cutting requirements; retain locators in step context and child reviews. |

Implementation order:

1. Freeze a candidate policy and independent four-invocation dry-run oracle.
2. Add failing regression assertions for fresh/cold packet reference delivery.
3. Add canonical policy, narrow navigator/Improve cues, legacy reference routes,
   and current README explanation. Preserve unrelated dirty work.
4. Run four fresh documentation-only trials, copying only prior repo files.
   Independently judge retention; replan only on observed failures/limitations.
5. Run focused tests, static checks, plugin parity and hermetic aggregate;
   independent review, repair justified findings, and report limits honestly.

## Longitudinal dry run (preregistered before trials)

The [reproduction procedure](../test/experiments/shiploop_feature_contracts/longitudinal-plan.md)
describes fresh-context inputs, copy-forward boundaries and scoring.
External evidence root during trials: `/tmp/shiploop-requirements-retention.Sqjcex`.
Retained archive: sibling workspace directory
`../.shiploop-experiments/requirements-retention-2026-09-17-Sqjcex`.
Raw packets preserve original runtime paths; `evidence-index.md` records the
relocation rule and selected source hashes. Evidence is outside product commits.
No product code, real SDLC traversal, Improve campaign or deployment is executed.
Four fresh host-default Codex agents receive one current request, a fixed policy,
and a synthetic repository. Only resulting repository files pass to the next
agent; no prior conversations, prompts, run folders or private oracle. Parent
does not repair between rounds. This is one chain, not statistical or cross-host
proof; tool access is instructed, not sandbox-enforced.

| Invocation | Accepted delta | Retention challenge |
| --- | --- | --- |
| 1 | Browser-local notes | Establish plain text, no network, confirm/cancel, reject empty without mutation, reset on refresh. |
| 2 | Case-insensitive search | Recover all initial conditions solely from durable product files. |
| 3 | Retain notes across reload in the same tab | Supersede reset only; retain search and unrelated negative/security conditions. |
| 4 | Sort matching results newest-updated first | Retain accumulated intent; reject explicitly unapproved deletion/empty-input relaxations in a design note. |

Frozen candidate SHA-256:
`5332d1927b8ee29d1ba87e6b3556f4fa5b92b1b7a52fac5e3fea3eac9937de6a`.
Frozen oracle SHA-256:
`49c622d6d306f20b4aacad3bfe934c11be9eec0f9ddaa08b635fcc324b21f8ca`.
An independent judge scores durable home, full condition retention, supported
delta, no unapproved expansion, usable source summary/test pointers and honest
unrun evidence as PASS/FAIL/UNKNOWN. Unknown is not a pass.

### Observed result and replan

The independent judge scored rounds 1, 3 and 4 PASS, and round 2 UNKNOWN on
approval provenance only. All four retained the accepted conditions, detailed
negative cases, durable home, source summaries, useful test pointers and honest
unrun status. The unapproved round-4 deletion/empty-input relaxations were not
adopted. The initial chain was **not** an all-pass result.

Round 2 selected reasonable substring/no-match/clear-order semantics, but labeled
them as accepted intent without establishing whether the request approved those
precise defaults. That ambiguity is not a demonstrated product failure. It is a
reason to distinguish **in-scope design choices** from **explicit requirements**,
without making ordinary choices require another user approval.

Replan: add one paragraph to the retention policy to make that distinction
explicit and prevent later agents from treating earlier chosen defaults as
binding solely because they were documented. Repeat only the ambiguous search
case with identical prior repo files and current request, a fresh agent and a
new frozen oracle. Do not repair or relabel the original chain. This is a
bounded follow-up, not a statistical prompt-comparison claim.

Follow-up policy SHA-256:
`b2da1873d3bd8a082cf820f3c5a08db10485185c4596b10b1dfff899d746815d`.
Follow-up oracle SHA-256:
`db4a91b7ea449ae7431d5a89b9e68485ce5b498167b623cdb2f7e44faa70dca8`.
The revised paragraph is implemented. The fresh follow-up passed all six frozen
criteria under a second independent judge: initial conditions survived, the
explicit search requirement was retained, inferred defaults were labeled as
design choices, home/test locators remained useful, verification stayed unrun,
and no redundant approval was required for ordinary in-scope choices. The raw
`judge.md` and `followup-judge.md` retain the original UNKNOWN and follow-up result.
This supports the narrow clarification; it does not prove arbitrary-repeat,
cross-model, full-workflow or deployed-application reliability.

## Implementation and verification

Implemented in existing components, with no state fields, graph nodes, counters,
or new required skill/tool:

- Canonical home/retention policy in
  `skills/shiploop/references/project-knowledge.md#maintained-product-requirements`.
- Shared navigator policy locator; v1/v2 and v3 producer guidance; actual v3
  Improve guidance. Selected product requirement/test locators travel through
  existing result `evidence_refs`, work-item context and child review notes.
- Existing classic behavioral-reference sections link the same policy without
  changing their frozen-baseline or correction rules.
- The current ShipLoop README explains artifact authority, repeated-run flow,
  deliberate supersession and the limits of script-provided locators.

Test-first observations: the initial new cross-run assertions failed for the
missing locator (v1/v2/v3 cold packets and successive requests); the v3 additions
also failed for missing producer/child cues. After implementation the focused
cross-run suite passed 11 tests and v3 passed 12, including a complete 34-stage
synthetic traversal and exact requirement/test locators surviving a bound,
current and cold child packet without state mutation. These tests prove routing,
not semantic compliance or a real Improve campaign.

Independent review found one useful omission: the generic policy locator did
not itself ensure the producer handed on the selected product-section locators.
Producer guidance now explicitly requests them in existing `evidence_refs`, and
a synthetic propagation check covers that path and work-item context. The
reviewer confirmed this resolved the finding. No semantic importer or required
path field was added; authors still must provide and use truthful locators.

Focused legacy checks also passed: reference routing (5), discovery (22), scoped
Ruff, and Git diff whitespace checks. The first invocation of the legacy tests
hit the host's Xcode-license Git wrapper; reruns used the existing command-line
tools via command-only `DEVELOPER_DIR`, without changing repository/test config.
The optional skill-creator quick validator could not load PyYAML from either
installed Python runtime; no dependency was installed. Repository-native
frontmatter/package checks run in the core suite instead.

The existing real-Git filtered-return regression now also returns
`docs/requirements.md` intact, excludes the transient HTML report, and starts a
later isolated workspace with that untracked requirements document explicitly
included. It passed. This uses the existing untracked-input selection policy;
it does not pretend an uncommitted document is automatically in every checkout.

The first hermetic aggregate encountered a pre-existing untracked Improve
`__pycache__` (mtime before this task). It was moved recoverably to the external
evidence directory, not deleted. The complete **core group rerun passed**.
The ShipLoop aggregate subsequently exposed a stale exact legacy reference-map
fixture that predated the actor-interaction and separately requested NFR routes.
That fixture was corrected to retain exhaustive route and no-guidance checks,
not to weaken them; its complete 35-test suite passed. The remaining catalog
suites ran three at a time after the interrupted point. **78 of the 79 ShipLoop
suites passed across the original run and reruns.** The last suite,
`shiploop-action-walk.test.py`, repeats 13 full legacy scenarios and was stopped
after about seven minutes without a result. It is **unfinished, not passed**.
The overall hermetic aggregate is therefore not claimed green. Given the narrow
prompt/reference change, the focused, protocol, core and other catalog checks
form the completed verification; the optional full action-walk remains a limit.

Final combined focused checks after the NFR edits passed **90 tests**: navigator
(36), v3 (14), cross-run (11), discovery (23), reference routing (5), and the
filtered-return/next-workspace case (1). The final design-choice clarification
only adds policy/README prose; cross-run was rerun successfully afterward.
Final source/plugin parity, scoped Ruff and Git diff whitespace checks pass.

Concurrent work: a separately user-requested task, "Add ShipLoop NFR spec phase",
added `requirements-definition.md` and related procedural guidance while these
checks ran. Its edits are preserved and coordinated, not attributed to this
retention experiment. It reuses the maintained product home rather than creating
a second product contract. The final focused checks cover the combined checkout.

Read-only installation check: both the existing Grok and Codex `shiploop` skill
entries resolve to this source package. Generated plugin parity passes. These
facts establish availability of updated files, not a live host/model execution.

## Reference correlation follow-up

Scope: the canonical skill at `skills/shiploop/SKILL.md`, its navigator and
compatibility prompts, package references, and the selected Improve handoff.
Alignment harnesses are `test/shiploop-reference-routing.test.py`,
`test/shiploop-cross-run.test.py`, `test/shiploop-navigator-v3.test.py`, and
`test/shiploop-actual-improve-cli.test.py` in this repository. Source skill
packages are authoritative; `plugins/shiploop/skills/shiploop` is generated.

| Audit question | Finding and chosen correction |
| --- | --- |
| Which root owns a reference? | Package policy, product intent, run evidence and child state are different destinations. Document one shared handoff policy and route current packets to it; use relative links in maintained product docs and explicit roots in task handoffs. |
| Does v3 planning actually expose Backchain guidance? | Its planning prose mentions dependencies but has no guide locator. Route the packaged adaptation into relevant producer and Improve prompts without importing legacy schemas or invoking a second scheduler. |
| Does the actual child preserve references? | Synthetic parent tests prove delivery into a packet, not into the real Until Loop contract. Extend the actual CLI composition fixture to perform the host-owned transfer through existing contract prose and verify cold recovery/import. This does not enforce model compliance. |
| Are legacy files a second product specification? | Their run spec and system-test catalog have distinct frozen/derived roles. Label their compatibility scope and link the maintained product home; do not change old state contracts. |
| Must standalone skills acquire a ShipLoop dependency? | No. Improve consumes its existing parent contract and bound Until Loop runtime. Backchain is an incorporated planning adaptation here. Keep product policy in ShipLoop and carry source locators rather than copying policy into upstream skills or changing pins. |

Implementation plan: add failing destination/routing assertions; add the shared
policy and missing routes; exercise the real child contract with fixture-host
inputs; validate local file/anchor links from relocated packages; synchronize the
generated ShipLoop view; run focused protocol tests, lint, and independent review.
No graph, state-schema, counter, installed integration, or commit/push change.

### Implemented result and focused checks

- One [reference handoff map](../skills/shiploop/references/project-knowledge.md#reference-handoffs-and-destinations)
  now correlates package guidance, product requirements/code/tests/reusable skills,
  run notes and actual Improve child artifacts with their writers and readers.
  The entry card, README, requirements/test guides and current/cold packets link
  to that map. Product links remain portable; moved targets require corresponding
  incoming-link updates, without rewriting immutable historical receipts.
- V3's spec, plan, step-plan, carry-forward and product-acceptance producers and
  Improve handoffs now select the packaged Backchain planning adaptation. An
  independent review identified ambiguous legacy fields in the shared guide;
  those instructions are explicitly segregated from v3 notes/evidence/context.
  The reviewer confirmed the conflict resolved. Scoped tests prevent legacy
  carrier names from leaking into the navigator entry section or v3 prompts.
- Fixed the entry card's genuinely missing README compatibility anchor. The
  README's older managed anchor remains a valid explicit HTML alias, not a broken
  link. The bounded Markdown checker recognizes that alias and includes negative
  controls for missing files/fragments; it does not claim to be a general Markdown
  parser or to verify external URLs. A package under an `experiments` ancestor
  cannot bypass the containment/link checks.
- The real child CLI fixture explicitly transfers a non-default product contract,
  test selector and separate run note through the existing contract prose. Exact
  references survive child cold `next`, parent recovery, accepted import and the
  archived child contract. This proves fixture-host transfer/storage, not automatic
  injection, model compliance, actual Improve reviews or product-test execution.

**159 focused tests passed**: navigator 36, v3 15, cross-run 11, actual Improve CLI
4, reference routing 8, classic packets 39, protocol 35, Backchain guidance 4,
and navigator dry-run 7. Commands are `python3 -B test/<suite>.test.py`, with
`PYTHONDONTWRITEBYTECODE=1`; this host additionally used command-only
`DEVELOPER_DIR=/Library/Developer/CommandLineTools` for Git's Xcode-license wrapper.
New route assertions were observed failing before their production fixes.
Final scoped Ruff, whitespace checks and generated ShipLoop plugin parity pass.
The full hermetic aggregate and a live model/product run were not rerun for this
follow-up; the preceding section's unfinished broad-suite limit remains unchanged.
