# Cold-preview grading and provenance

This is the parent's post-run semantic assessment against the five fixed criteria
per case in `../../cold-cases.json`, not an automated language-quality metric.
Packets and responses retain original action IDs. Temporary/source roots are
normalized to explicit placeholders; these archival packets are non-executable.
Prior transitions are synthetic and none of these previews issued a callback.

| Trial | Current stage/action identity | Risk/ownership criteria | Learning criteria |
| --- | --- | --- | --- |
| Initial | Stage correct 1/2; neither response supplied a literal action ID | 5/5 semantic criteria | 5/5 |
| Unblinded diagnostic correction | Both stage and action IDs correct | Not rescored | Not rescored |
| Fresh two-case repeat | Both stage and action IDs correct | 4/5: criterion 3 failed | 5/5 |
| Fresh risk-only preview after prerequisite wording | Correct stage and action ID | 5/5 | Not rerun |

The initial risk response used the last accepted `plan-improve` stage instead of
current `step-plan`. Its substantive release-only prerequisite decision and
bounded ownership were sound. The original output request's `action` field was
ambiguous, so absence of literal IDs is recorded separately, not retroactively
scored as a fixed semantic criterion. The worker's explicit diagnostic correction
is preserved and does not turn the initial response into a pass.

The common prompt then clarified Current node/Action versus Last accepted
transition; the next output request explicitly asked for those literal fields.
That fresh repeat got both identities right. However, its risk-case eligibility
statement made local implementation/integration wait for required staging
validation, although the supplied scenario required staging only before release.
An independent reviewer confirmed this criterion-3 failure. Other criteria held:
relevant risk selection, delegated ownership, staging not waived, and no invented
nodes or callback fields. The learning response retained a tentative local
observation, rejected a blanket timeout rule, required broader evidence for
promotion, kept investigation proportionate and future work distinct.

The step-plan prompt then distinguished current prerequisites from downstream
integration/system/release conditions. A third fresh agent's risk-only response
explicitly allows independently authorized local work, assigns staging access
and validation to release, and preserves the current planning evidence needs.
It also satisfies the other four fixed criteria. These changes and output-field
clarification make the sequence an iterative capability check, not a matched
causal A/B test or a reliability estimate.

The initial pair used the working candidate before the orientation clarification.
The repeat used source commit `44fcfbc`; the final risk-only packet additionally
used the later step-plan prerequisite paragraph, before that paragraph was
committed. Exact normalized packet text is preserved for each trial.
