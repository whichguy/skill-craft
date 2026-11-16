1. **Goal**

Qualify whether the two existing late-stage assignments catch invalid inherited procedures and preserve valid ones before making any production prompt change.

2. **Material issues**

- **Use a runnable assignment, not just authentic rendered text.** Carry-forward Improve needs its bound child, runtime receipt, reviewed packet/result, frozen scope, and working callbacks. `improve_handoff_text` explicitly routes the reviewer to those artifacts; supplying the handoff alone would test an incomplete assignment. Keep the inherited procedure and relevant setup change within the review’s legitimate scope. See [shiploop_navigator.py — handoff dependencies:8079](/Users/dadleet/src/skill-craft-r05-20261115/skills/shiploop/scripts/shiploop_navigator.py:8079) and [shiploop-route.md — runtime and scope contract:9](/Users/dadleet/src/skill-craft-r05-20261115/skills/improve/references/shiploop-route.md:9).

- **The existing invalid fixture does not establish inheritance after a change.** Its `create → delete → update` sequence is already invalid under its recorded requirement. For the changed-setup situation, retain an earlier setup where the procedure genuinely works, then introduce one ordinary lifecycle change that makes its first deciding action fail. For example, an inherited `update sample; get sample` procedure formerly followed setup that created `sample`; the changed setup clears it. Preserve both setup identities and the old observation. Otherwise the experiment measures detection of a static invalid procedure. The existing [reference store and replay:2998](/Users/dadleet/src/skill-craft-r05-20261115/test/shiploop-guidance.test.py:2998) are adequate starting points; no general interpreter is needed.

- **A local callable package does not automatically justify a person request.** Release-verify must run available checks itself and request a person only for a required observation the host cannot perform. A fixture that merely declares an accessible CLI operation “person-only” creates conflicting inputs. Include a coherent actor/access boundary for the person-preparation arm, or limit that arm’s claim to automated release verification. An invalid release plan should take the existing `send-back` route; inaccessible execution alone should not be mistaken for invalid procedure semantics. These distinctions already appear in [release-verify duties:1840](/Users/dadleet/src/skill-craft-r05-20261115/skills/shiploop/scripts/shiploop_prompts.py:1840).

- **Subject/judge separation is sound, but the acceptance rule needs one clarification.** The *subject* must identify the invalid transition with supporting reasoning or evidence and act on it. The judge discovering the flaw afterward is not success. Score three things separately: semantic diagnosis, resulting disposition, and successful protocol execution. Generic caution or leaving everything open cannot qualify the negative cases; likewise, blocking every valid control cannot qualify safety. Permit a corrected procedure followed by genuine fresh observation to close the affected item. “Keep open” applies while that observation remains unperformed.

- **A preseeded reviewer-added case tests inherited coverage, not the subject’s own case creation.** Keep that situation, but describe its provenance accurately. Inspect any cases the current improver adds naturally; do not require it to invent a case merely to make the experiment scoreable. The historical unchecked-helper incident specifically involved a review adding the invalid case itself, as recorded in `abdb0fdd8b3206e3458603c2cefc87c6326ac556`.

The smallest useful setup is one local store package, one work item, one meaningful setup change, existing knowledge/result records, and two independently seeded late-stage assignments. Use a checked public operation and a separate unchecked replay helper whose result looks plausible but does not establish permission for the transition.

Concrete existing seams:

| Purpose | Existing seam and limitation |
|---|---|
| Seed predecessor state with normal effects | [navigator.accept_effects:10074](/Users/dadleet/src/skill-craft-r05-20261115/skills/shiploop/scripts/shiploop_navigator.py:10074), after `apply` and any synthetic predecessor `finish_improve`. It deliberately skips gates; its caller holds the run lock. Label predecessor results synthetic. |
| Emit actual packets and supporting files | CLI `next`, through [navigator.emit:2078](/Users/dadleet/src/skill-craft-r05-20261115/skills/shiploop/scripts/shiploop_navigator.py:2078). Capture stdout and the emitted files. |
| Enter actual carry-forward Improve | Seed to its producer, then use real producer completion and the resulting bound runtime. [ImproveCliFixture._start_parent_at_stage:222](/Users/dadleet/src/skill-craft-r05-20261115/test/shiploop-actual-improve-cli.test.py:222) demonstrates target-stage CLI composition; use the public effects seam for predecessor setup rather than copying its pure-state shortcut. |
| Preserve release ask/reply behavior | [partial-person-reply test:1319](/Users/dadleet/src/skill-craft-r05-20261115/test/shiploop-consumer-delivery.test.py:1319) supplies the existing scoped semantics. It is a contract example, not live observation evidence. |
| Verify later prompt placement | Extend [procedure-routing tests:915](/Users/dadleet/src/skill-craft-r05-20261115/test/shiploop-guidance.test.py:915), plus emitted CLI coverage at the repaired boundary. |

**Do not extend the stage-suite framework for this qualification.** Its [builder explicitly rejects Improve and outer-stage scenarios:736](/Users/dadleet/src/skill-craft-r05-20261115/test/shiploop_e2e/stage_suite/stage_build.py:736). That would turn this task into apparatus development.

3. **Minor nits**

- Keep the proposed four situations × two boundaries × two repetitions if each cell has coherent inputs. Cut the additional library/API/CLI cross-product: use thin views of the same package where useful, without claiming independent domain coverage.
- Include a valid expected-rejection case—such as updating a missing key expecting `NotFound`—within the positive control. This distinguishes invalid expectations from legitimate negative tests.
- Hiding answers outside the workspace is insufficient if subject tools can read the surrounding evidence directory. Keep reference proof outside subject-readable scope.
- Do not concatenate all Improve reference files into the opening assignment. Preserve normal routing and let the subject open them.
- Freeze the repair comparison’s source delta as well as fixture identity; otherwise a later main update could confound the paired result.

4. **Open unknowns**

- Which exact local observation genuinely requires a person?
- What candidate change makes the formerly valid procedure invalid, and where will the ordinary assignment expose that change?
- Will “reviewer-added” mean an inherited case with recorded provenance, or a case actually created during this subject session?
- Which existing run mode and delegation route will be qualified? One is sufficient initially, but report it precisely.
- Packet/callback usability remains unverified here. I inspected source and the three cited historical commit messages; I ran no tests and made no workspace edits.

5. **If I were implementing tomorrow**

1. Freeze one fixture and its before/after setup, required observation, candidate identity, and permitted correction routes.
2. Build only the disposable seeding adapter around `apply`/`accept_effects` and normal CLI emission. Preserve real target-stage runtime behavior.
3. Check apparatus coherence before subject calls: every locator resolves, callbacks target the frozen package, the invalid transition follows from the specification, and the valid control genuinely works.
4. Register the small matrix and behavior-based verdict rules, then launch fresh subjects. Keep the independent judge outside the subject’s execution and repair loop.
5. For a reproduced semantic miss, patch only the owning prompt boundary. Carry-forward already selects `END_REVIEW_FOCUS_HEAD`; release-verify already has its own duty. Neither presently requires navigator restructuring.
6. Add emitted-placement and meaningful reference regressions, rerun affected subjects and controls, and update R05 with the bounded result. If no miss reproduces, retain the evidence and leave production prompts unchanged.
