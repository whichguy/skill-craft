# UI default: decision and validation

New graphical interfaces start from the owner's selected light Gemini-like direction. Explicit visual requests, an existing product identity and platform conventions take precedence. This is a chosen default supported by diagnostic examples, not a measured universal quality gain.

The implementation is in the [UI profile](../../../skills/shiploop/references/platforms/ui.md#light-expressive-starting-point), [planning procedure](../../../skills/shiploop/references/plan-record.md#concrete-ui-direction), and [specification/criterion duties](../../../skills/shiploop/scripts/shiploop_prompts.py). The planning guidance requires concrete art direction before implementation: typography, spacing, color roles, placement of tonal surfaces, component shapes and important states belong in the existing design decision. Each visible-UI step selects the relevant section and carries observable choices into its criterion. Rendered inspection at the required sizes and themes remains necessary; functional checks alone did not catch the early visual defects. No toolkit, font download, new schema, gate or loop limit is introduced.

| Retained diagnostic | What was observed | Consequence |
| --- | --- | --- |
| Original prompt comparison | Owner preferred C, the explicit Gemini target; four model judges preferred B | Adopt the owner's direction; do not treat aesthetic judging as unanimous |
| First and refined chat handoffs | Both passed 16 bounded interaction checks; one first-handoff contrast failure, then avatar/focus misses in the refinement | Describe actual surface roles and inspect visible states |
| No-style appointment picker | Ten interaction checks passed, but the phone summary overlapped the date/time chooser | Preserve this adverse example; interactions do not prove layout quality |
| First full no-style Checkers run | Engine completed, outer checks 4/4, held-out checks 6/6; unequal board rows, serif heading and no theme control | A criterion requiring only cells, moves and reset was insufficient |
| Intermediate full Checkers run | Engine completed, outer checks 4/4, held-out checks 6/6; its own system review added a geometry correction; independent browser checks 9/9 | Rendered correction works, but OS-following appearance still missed the starting-theme policy |
| Fresh no-style chat | Design reached a fresh builder; first output passed 16 interactions but had two low-contrast labels, a stray desktop close button and crowded attachment metadata | Corrected copy passes 16 interactions and six additional observations; no failures in measured text-contrast samples, with unresolved backgrounds excluded |
| Final full Checkers run | Engine and harness completed, outer checks 4/4, held-out checks 6/6; ten independent browser checks pass | The final unrepaired output starts light even with a dark system preference, offers dark mode, and renders uniform cells with visible phone controls |

The final chat starts light even with a dark system preference, supports an explicit dark option, and keeps its composer reachable on desktop and phone. The corrected copy uses the same prompt and accepted design as its first build; it is not a new prompt arm or evidence of first-pass perfection.

The final source (`893619c8a811595720f96a80a9d532c79510cee5`) completed its no-style Checkers run in one subject session with no resume (2270.8 seconds). Its build and source were unchanged before/after. The final prompt's first accepted game plan retains a light starting theme, dark option, responsive rendering and focus checks. It still abbreviates some requested design detail: the specification paraphrases the named reference, AD-2 lacks concrete token values, and the criterion says “visual anchors” without enumerating every selected choice. Those are retained conformance limits. The rendered final output does carry the chosen light, rounded, task-focused direction; this does not establish perfect adherence to every planning instruction. The parent independently exercised the sealed server through direct loopback HTTP. The subject’s own Chrome proof used a real-HTTP forwarding bridge with byte-identical served/rendered HTML; direct subject Chrome loopback remains unobserved.

## Design continuity review, 2026-11-06

The owner clarified that decisions must remain in the product repository so
subsequent feature additions stay directionally consistent. The existing
`docs/shiploop/spec.md` and `architecture.md` are the durable home, with design
choices recorded as `AD-<n>` entries and links to product-owned design documents.
The [architecture decision](../../ARCHITECTURE.md#product-ui-continuity-partial-owner-decision-2026-11-06)
records that ownership and the distinction between requested requirements,
chosen product identity and observed validation.

Reviewing the returned products exposes a persistence limit beyond the rendered
results above. All three full Checkers runs (`default-live-01`, `-03`, `-04`)
retain a short UI AD without concrete token values. In the final run, AD-2 is one
sentence; color roles, radii and the responsive breakpoint have concrete values
in `index.html`. The document stage nevertheless reported that “AD-2 already
describes the implemented board and themes” and completed. Its C3 criterion and
`follows` do select AD-2, so the decision linkage exists; the selected record is
underspecified. Only the final run used the final planning duty text. These are
observations about retained outputs, not new grades or evidence that every run
loses design continuity.

The final specification also names `platforms/ui.md` without a corresponding
file in the delivered product. It retains the reference name, but the guidance
is not self-contained there. Later work must be able to recover the product's
actual decisions without the old run or a changing external skill reference.
The read-only review and exact source locators are retained under the experiment's
`integration/architecture-record-01/` evidence directory. The original products
and results remain unchanged.

A separate follow-on diagnostic used the published ShipLoop 1.33.0 runtime and
a copy of the final Checkers product. A clearly labeled synthetic AD-4 recorded
a future help panel below the board, a 32rem reading width, existing theme roles,
and the rationale for keeping the board usable. The feature prompt requested
only a How to play guide; it did not repeat that design. The fresh run read AD-4,
selected it in the plan and implementation criterion, and returned the decision
with its rationale and implementation/verification update. The implementation
packet named the architecture file and included the selected AD text. R-5's
earlier pending statement was explicitly labeled historical planning text.

The run completed in one session without resumes (2205.7 seconds), with all four
original game checks passing. Its own checks passed through the stated Chrome
bridge; its failed direct-browser attempt remained open. Independent inspection
of the returned product then passed at 1440×1000 and 390×844 in both themes:
the guide stayed below the board, respected its width and existing theme/font,
and caused no horizontal overflow. Keyboard toggles preserved selection, board,
turn and message without network requests; two subsequent moves and reset
succeeded through direct local HTTP. No console errors were observed.

This tests consumption and retention of a **prepared** decision, not automatic
creation of a detailed AD or a comparative quality gain. An inherited
real-boundary paragraph still ambiguously says the product check has not run,
beside more specific bridge/direct-transport records; retain that documentation
limitation. The fixture, immutable source/build identity, packet and journal
review, raw results and browser captures are in
`integration/architecture-record-01/continuity-probe-01/`. No runtime change or
new plugin release follows from this documentation and validation work.

## Evidence boundaries

This section retains the original 2026-11-05 prepublication checkpoint.

Each version has one diagnostic sample. The four original opt-in chat/chess full-workflow runs are separate frozen experiments and remain in progress when this record was written. None is a final-default comparison. Runs overlap, so elapsed times and mutation ratios are not used to claim a prompt speed or quality gain. Requested model/effort identity is recorded; independent served-model identity and dollar cost are not claimed.

The source's focused checks pass 127 tests. The initial full CI exposed an unrelated listener-identity defect in the E2E apparatus: the user-directory calibration received the ticket service's 404 response. The exact process was not retained, so that attribution is an inference from the response. A separate repair makes both readiness paths reject any reported listener outside the candidate's process group. A real IPv4/IPv6 mixed-owner experiment reproduced the ambiguity and both guards rejected it without killing the sibling. Existing own-EADDRINUSE retries, expected grades, fixtures and ceilings stay unchanged. The repaired apparatus passes 156 quality tests, the 41-test user-directory suite (one abstract-base skip), five HTTP binding checks and the whitespace check. Full source CI for commit `f1399b5b8b9d3f4d7a721e9e8e2514ea9ce74994` is pending when this record was written. This changes evaluator bytes; the frozen UI runs are not retrospectively regraded or compared across that boundary.

The packet measurement keeps the existing 20,000-character head limit. The final interaction walk's largest packet is 19,995 characters. Earlier drafts that exceeded the limit and the first failed CI/verification attempts remain retained.

Raw artifacts, source/build identities, retained outputs, original and corrected screenshots, and browser observations are under `/Users/dadleet/Documents/Codex/experiments/shiploop-ui-prompt-20261105/`. The local gallery is served at `http://127.0.0.1:53113/integration-review/`; it is a computer-local artifact, not an external deployment.

The [compact evidence](evidence.json) records all three completed Checkers deliveries, the chat correction lineage and partial contrast counts. Mutation results were 76/148, 83/121 and 82/169 killed for the three games, with 4, 18 and 7 timeouts respectively. Those differing generated products and small samples do not establish a test-quality gain. All raw adverse results remain retained.
