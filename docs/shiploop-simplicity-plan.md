# ShipLoop KISS/YAGNI review and implementation constitution

Baseline: `21535144152ea19c4cd43676de3dc59534156656`. Scope: reduce avoidable
instruction complexity and make inner-loop coding decisions explicit without
adding a new workflow, authority, dependency, or result schema.

**Implementation status (2026-09-12):** delivered by `c548bc9` and retained at
`414b3e9`. The constitution, all eight routes, and compact iteration table are
implemented. The [combined quality-review closeout](shiploop-quality-review-closeout.md)
records current checks and the narrow follow-up recovery/regression work. The
verification section below preserves the original implementation evidence.

## Decision

Adopt one short, stack-neutral implementation constitution in the existing
`testing-and-documentation.md` reference. Route that section through the existing
packet guidance for initial/Improve planning, plan review/revision, implementation,
product review, and verification repairs. Keep observations in existing Markdown results and findings.
Condense the reference's repeated iteration narrative into a phase/record table.

The constitution is a default decision aid, not a new policy engine or an
instruction that supersedes the user's requirements, approved contracts, or
applicable repository conventions. It must remain usable after context loss.

## Evidence and alternatives

Research checked 2026-09-12. These are primary engineering sources; older guidance
below describes stable design practices, not a claim about current model quality.

| Candidate / source | Benefit and fit | Cost / counterevidence | Decision |
| --- | --- | --- | --- |
| [Google code-review guidance](https://google.github.io/eng-practices/review/reviewer/looking-for.html) | Review present-day complexity, useful comments, project style and relevant tests together. | A large universal checklist would duplicate ShipLoop's existing rubric; personal style preferences should not obstruct delivery. | Adopt the small decision-changing subset. |
| [Fowler's YAGNI analysis](https://martinfowler.com/bliki/Yagni.html) | Avoid unused extension points and speculative features; prefer today's concrete requirement. | YAGNI is not a reason to skip tests or useful refactoring. Some extra structure reduces current complexity or protects a real boundary. | Adopt current-need justification, not a ban on abstraction. |
| [OWASP input validation](https://cheatsheetseries.owasp.org/cheatsheets/Input_Validation_Cheat_Sheet.html) | Check input shape and domain rules at untrusted entry points before downstream effects. | Validation is not authorization or a substitute for attack-specific controls; checking the same trusted value everywhere adds noise. | Adopt boundary-focused checks and negative tests. |
| [GitHub Spec Kit constitution template](https://raw.githubusercontent.com/github/spec-kit/main/templates/constitution-template.md) | Demonstrates a concise project-principle artifact. | Its library-first, CLI, mandatory TDD and governance examples are customizable examples, not generic requirements. They would conflict with ShipLoop's chosen post-code test-refinement flow if copied wholesale. | Borrow the short-principles idea; reject another framework, mandatory library/CLI architecture, or governance layer. |

Token-efficient comments here means compact, useful contracts and explanations,
not abbreviated identifiers, per-function boilerplate, machine-only tags, or a
claimed measured token/performance improvement. No comparative model benchmark
was performed. The separate skill-creation guidance also favors decision-changing
instructions and progressive disclosure over restating general programming advice.

## KISS/YAGNI findings

| Finding | Action now | Why not a larger change? |
| --- | --- | --- |
| Testing/documentation iteration prose repeats the ordered workflow already supplied by stage prompts and the activity guide. | Replace the repeated narrative with a compact routing/record table; retain exact test-oracle, evidence, and permission rules in their canonical sections. | Removing cold-packet reminders altogether would make the caller depend on memory. |
| Prompts cover test adequacy and docs, but do not consistently ask whether a new abstraction or defensive check is justified. | Add the small shared constitution and one short inline reminder on the eight relevant routes. Reuse existing findings and result fields. | A style score, new pass counter, mandatory exception object, or separate constitution file per run creates new state without a demonstrated need. |
| Packet rendering and the completion dispatcher are large and have parallel routing tables. | Retain their behavior; add routing regressions for this narrow change. | A universal stage registry or handler framework is a cross-cutting refactor, not a proven simplification for this change. Defer until an actual routing defect or focused module change justifies it. |
| Receipts, identity checks, bounded paging, legacy compatibility, and explicit phase boundaries look verbose. | Retain them, including lint/tests and the two-trivial-pass convergence policy. | They implement explicit user requirements and demonstrated safety/recovery cases, not speculative flexibility. Line count alone does not establish overengineering. |

## Implementation and acceptance plan

1. Add routing tests first: the eight selected routes resolve one constitution
   section in the actual package; unrelated actions do not load it. Exercise the
   existing cold-packet renderer without a new test harness or schema.
2. Add the shared section, concise prompt reminder and existing-map routing.
   Cover scope, local conventions, justified abstraction, input/error boundaries,
   concise comments/contracts, evidence and materiality. Keep source of truth
   single, with a direct reference from the activity guide and README.
3. Condense repeated iteration guidance without changing the state machine or
   dropping test selection, independent oracles, required lint, carry-forward,
   commit, or broader-plan obligations.
4. Independently review the diff and forward-test realistic coding decisions.
   Verify packet/protocol suites, relevant plan and action-walk regressions,
   syntax/lint, Markdown links/anchors, frontmatter and derived plugin parity.
5. Record actual results and limits below. No claim that a prompt or string
   assertion proves software quality, semantic simplicity or live platform safety.

## Verification

The route/anchor and cold-render tests first failed because the selected section
was not routed. After implementation, the packet suite passed 29 tests and the
protocol suite passed 34 in the working checkout. A separate review found no
lost required duty in the condensed iteration section or new schema/loop.

An independent forward evaluation of three hypothetical requests chose a focused
negative-count parser guard, reuse of an existing boundary validator with required
exported-function docstrings, and no speculative retry framework for a no-change
pass. This is a limited qualitative check, not a model benchmark.

Measured text size: the repeated Iteration section decreased from 506 to 380
whitespace-delimited words; the shared constitution is 326 words. Total guidance
did not shrink by 126 words: selected coding routes also acquire the constitution.
The benefit is centralized, explicitly selected guidance, not a claimed tokenizer
or performance improvement.

The first isolated protocol run caught an Improve-plan packet exceeding its
existing 7,000-character fixture bound under the longer checkout path. The inline
reminder was shortened; the bound was not raised and the shared detail was kept.

Final review also identified `verify` as an eighth source-repair route: failed
checks remain in that action, so no intervening plan/review guarantees reloading
style guidance. A new failing route assertion preceded the addition. No recovery
transition changed; late edits still invalidate trivial convergence. Final-verify
continues to use its existing repair path rather than acquiring new edit authority.

Passing evidence covers 81 distinct affected tests across the isolated snapshot
and final targeted reruns: packet 29, protocol 34, step planning 17, and one full
terminal action walk. The final eight-route packet/protocol rerun ended `EXIT=0`.
The initial 81-test snapshot remained unchanged during execution and retains its
honest exit 1 for the subsequently fixed packet-size regression. Its planning and
terminal-walk results passed; those runs preceded the final text shortening and
verify guidance addition. No state-machine behavior changed in this increment.

Evidence is retained under `/tmp/shiploop-simplicity.Lh5yAz/`: `inputs.json`,
`summary.json`, individual logs, and `final-eight-routes-packets.log` /
`final-eight-routes-protocol.log`. New README/activity links and the target anchor
were checked; routing tests cover the selected section in the actual package.
This is focused regression coverage, not a full repository or live-platform test.

Static checks passed: Ruff `F,E9`, 17 repository package-frontmatter checks,
whitespace and canonical/plugin parity. The generic skill-creator validator could
not start under the default Python (PyYAML absent); an existing system Python
ran it and rejected the unchanged `version`/`platforms` metadata. Those keys are
required by this repository's portable packaging contract, so this is a known
validator mismatch, not a reason to remove them or install another dependency.
