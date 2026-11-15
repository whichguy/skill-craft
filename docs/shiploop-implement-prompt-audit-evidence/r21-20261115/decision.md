# R21 implementation decision

The authorized scope is stale external-state receipt reuse. Preserve R08's single v2 format, existing whole-record reuse, count floors, provenance and scheduling. No compatibility layer or new receipt field is needed.

One shared eligibility predicate excludes release verification and command rows with an explicit target, a host dependency or an existing platform-card remote match. Proof strings lack target metadata, so a current declared target or unsafe item command also excludes Proof reuse. Apply this before whole-answer, candidate, Proof and mutation cache selection, using actual command overrides where supplied. Mutation checks inspect the focused set before remote rows are excluded. Pure checkout cases retain their current behavior.

The independent Astra/high advice identified mutation reuse as a fourth route and distinguished receipt reuse from document/Improve scheduling; both points are adopted. Its suggestion to permit named `keeps_state=no` targets is not adopted. The existing navigator tells checkout commands to omit `target` and describes an empty target list when every test runs on the checkout. `keeps_state` says whether a target retains state, not whether its response is determined by the Git tree. Rerunning all named targets is a smaller and safer rule than inferring locality or adding declarations.

The regressions must change a sibling fixture outside the checkout while retaining action, draft, command and repository identity. They exercise actual callbacks and shell execution, current local reuse controls, and a distinct permission-denied result after an earlier allowed check. This is live-result freshness at the receipt boundary; it does not implement a general authority-expiration engine or prove arbitrary undeclared shell dependencies are hermetic. The declarations remain a contract.

The rule can repeat more work for a local command with an unnecessary target, and for a local Proof in a mixed local/external strategy. That is the deliberate conservative choice within R21. No performance gain is claimed. No platform deployment or live-host certification is part of this change.

Relevant decisions read in full: a3b2f975487ebb7ede6987628c4a931941f9b057, f04cbdde94b118f9bc9f4810024afd714928a57f, 5086baf688a611172003e0fac4417dba06bb4e0c, 1e4e04c2f72670e5d8395945f5249aec709ff608 and 33843698f0731cb637dea281491fe35e6c3eeaa7. The retained run measurements do not justify per-command caching or a broader evidence-reuse redesign.
