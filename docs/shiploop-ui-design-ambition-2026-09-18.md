# Ambitious UI planning without parallel systems

Status: implemented; both bounded planning controls and scoped Improve completed.
Published-commit CI is verified separately from these local records.
Base: `3d45d186e8caf605660e1f49efded1fb3d31dffa` (UI ownership allocation).
Candidate: ShipLoop `0.15.2`. This is a follow-up decision, not a revision of the
frozen evidence in the [allocation study](shiploop-ui-planning-allocation-2026-09-18.md).

## Decision

Adopt a stronger default: aim for the most polished, elegant and richly
interactive experience feasible within user goals, accepted scope and the actual
host. Reuse excellent existing work as a foundation; a merely adequate current
screen is not the quality ceiling. Richness must improve the intended experience,
retain usability and state correctness, and respect the existing product system.

At a consequential UI decision, record the intended experience and compare
viable reuse, compatible evolution and upgrade/adoption options in the existing
Design basis. Estimate effort or cost with ranges or relative size, assumptions
and uncertainty; connect that estimate to user benefit, accessibility,
performance, maintenance and target compatibility. A new package or capability
remains a candidate until its existence and fit are established. Reuse current
components, tokens, assets, state/interaction mechanisms, design/build/test and
browser facilities. Do not introduce a parallel UI stack or duplicate harness.

Initial architecture owns shared decisions and readiness prerequisites. Feature
planning reuses them, estimates its affected delta, and reopens a shared choice
when evidence or a worthwhile new opportunity warrants it. Existing automatic
Improve reviews the decision and its evidence at that planning level. No new
workflow stage, schema, controller, provider integration or mandatory design
service is added.

## Primary research and boundaries

Sources inspected 2026-09-18:

- [Google Material expressive-design research](https://design.google/library/expressive-material-design-google-research)
  supports deliberate hierarchy, shape, color and motion that make actions easier
  to understand. Its contrary examples matter: unusual navigation and removed
  labels can make a visually exciting design less usable. Apply principles to
  the product's established journeys and identity, not a mandatory Material skin.
- [The Gemini design team's visual-language account](https://design.google/library/gemini-ai-visual-design)
  describes evolving established brand shapes and responsive containers into a
  more dynamic experience while preserving familiarity and trust. This supports
  reuse with intentional evolution rather than copying Gemini's gradients or
  requiring a Gemini dependency.
- [Google Research on generative UI](https://research.google/blog/generative-ui-a-rich-custom-visual-interactive-user-experience-for-any-prompt/)
  provides examples of interfaces tailored to user intent and audience, supported
  by tools and detailed instructions. The reported preference comparison excludes
  generation speed, and the authors identify latency and occasional inaccuracies.
  This is inspiration for specific useful interactions; it does not justify a
  new generative-UI runtime, provider integration, or an assumption of live product
  correctness.
- [Apple's motion guidance](https://developer.apple.com/design/human-interface-guidelines/motion)
  favors purposeful, brief, optional and interruptible feedback, often supplied
  by existing system components. This reinforces reuse, reduced-motion support
  and preserving user control rather than increasing animation volume.

Adopt these planning principles. Pilot an actual new toolkit only when a run's
product gap, rough cost/benefit and compatibility evidence justify it. Defer any
specific integration until those conditions exist; no installation is implied.

## Implementation

- Strengthen `behavioral-requirements.md`'s existing UI-specific planning section
  and link it from the ownership section.
- Add compact ambition/estimate/reuse cues to the existing global-plan, step-plan
  and Improve packets. Preserve existing decision locators and result fields.
- Bump to `0.15.2` and regenerate shared plugin views.
- Exercise two isolated fresh-producer controls using the existing ShipLoop
  packet/callback apparatus. Preserve frozen inputs, synthetic predecessor labels,
  actual plan outputs, callbacks and observed state separately from oracle judgments.
- Run the existing routing/recovery checks, actual scoped Improve through two
  qualifying reviews, plugin parity and exact published-commit CI.

The controls evaluate elicited planning decisions. They cannot establish visual
beauty, live host compatibility, implementation performance or deployment quality.
Those require the selected product's later rendering, interaction and target checks.

## Validation

The existing guidance/recovery suite passes 18 tests, and generated plugin views
match the source. A new actual standalone Improve run reviewed only the 0.15.2
candidate on base `3d45d18`, completed two distinct qualifying reviews, and
returned terminal `complete` with a 2/2 streak. No material source repair was
needed. The earlier 0.15.1 review and CI run remain separate evidence; they do not
establish this follow-up's published-commit CI result.

## Observed planning controls

Both fresh producers used the frozen `0.15.2` package and the available
frontend-design card (its actual digest is retained in their plans). Each
submitted one real callback and stopped at the normal unrun Improve handoff;
eight explicitly synthetic predecessors supplied the cold cursor. The original
fixture files remain unchanged. This is not a whole-workflow or application build.

| Control | Observed decision | Limit |
| --- | --- | --- |
| Existing supported primitives | A persistent Export activity folio; evolve the existing DOM/CSS, tokens and state path; compare unchanged reuse and package adoption with assumption-bound relative sizes and effort ranges. | Zero existing Node test cases; the proposed browser check and estimates are unverified. |
| Compatible enhancement opportunity | A compact-to-expanded explorer; preserve a DOM/CSS baseline and gate native View Transitions on an intended-target probe; defer unsupported package adoption. | No target support, browser behavior or migration benefit was measured. |

An [independent review](../test/experiments/shiploop_ui_allocation/ambition-evidence/independent-review.md)
found the declared planning criteria present in both outputs. The controller's
own rubric assessments are also retained but are not independent review. The
[manifest](../test/experiments/shiploop_ui_allocation/ambition-evidence/manifest.json)
records source and tokenized content-copy digests separately; these archives are
not executable/resumable state or direct evidence-reader inputs.

The controls also expose an authorization-error policy boundary. A forbids an
old account response remaining current after 403, and its plan chooses clearing.
B leaves the invalidation policy unspecified and its plan retains a same-account
snapshot marked stale. These inputs do not establish a universal purge rule. Preserve that ambiguity for
the normal contract, Improve and test-spec work before implementation. Stronger
visual planning does not substitute for domain-contract or security review.

The scoped implementation review's [exact terminal packet](../test/experiments/shiploop_ui_allocation/ambition-evidence/implementation-review/12-action2-done.stdout.raw.json)
records two qualifying reviews. This is separate from the two producer controls'
unrun Improve handoffs.
