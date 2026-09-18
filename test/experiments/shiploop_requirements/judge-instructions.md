# Independent requirement experiment evaluation

Read only the supplied frozen oracle, fixture source map, original product files,
and participant artifacts. Do not consult current mutable ShipLoop guidance,
other judges, or edit an answer. Assess each stage according to its assigned work:
discovery locates intent/gaps; spec defines the candidate and planned checks;
document updates accepted intent in its existing home with evidence gaps explicit.
Synthetic fixture history is not an observed Improve run or successful product.

For each applicable oracle criterion, give PASS, FAIL, or UNKNOWN and a short
quote or precise path/line. Grade preserved qualifiers and exceptions as well as
headline requirements. Look for unauthorized relaxation, needless blocking,
fabricated targets, duplication of maintained authority, and false verification.
Correctly flagging uncertainty is not a failure. Unavailable evidence is UNKNOWN,
not PASS. The sources list is participant-reported; record whether the output
contains fixture-specific content that supports retrieval, without claiming an
independently instrumented file-access audit.

Return JSON with `trials` (each containing `id`, `criteria` [{`id`, `status`,
`evidence`}], `material_failures`, `uncertainties`, `current_stage_status`, and
`feature_acceptance_status`), `overall`, and `limitations`. Avoid scores based
on answer length or completeness outside the assigned scope.
The producer result's `outcome: done` can mean its draft was produced; it is not
by itself a claim that the feature or every dependent requirement is ready.
Judge the stated prerequisites, open decisions, and separate status record.

For a paired comparison also return `scores` keyed by task_adherence,
factual_accuracy, completeness, instruction_following, structural_clarity,
precision, conciseness (A/B/TIE), `winner` (A/B/TIE), and `reasoning`. Condition
positions are randomized externally. Reject a material regression regardless
of stylistic preference. Equal evidence in both arms is required to attribute
differences to guidance. A tiny sample cannot establish reliability or equivalence.
