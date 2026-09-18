# Independent context-package evaluator

Evaluate the supplied anonymous A/B contexts and exact answers. Do not inspect
other trials, infer which is a candidate, execute plans or reward extra length.
Quality is conditional on evidence actually supplied. The normative oracle is
fixed separately; unavailable facts produce UNKNOWN, not a guessed PASS or an
unfair FAIL. Distinguish sound uncertainty from confidently inventing authority.

For each answer, report every applicable frozen mandatory criterion with
PASS/FAIL/UNKNOWN and a short verbatim quote or an explicit omission. Also report
decision readiness: enough known intent to plan the requested change safely,
or needs additional facts/decisions. Contract availability is not itself quality.
Material failure overrides stylistic preferences. Do not equate a planning answer
with observed implementation, passing tests, or real ShipLoop traversal.

Return JSON with:
- scores: task_adherence, factual_accuracy, completeness, instruction_following,
  structural_clarity, precision, conciseness; each A, B or ~;
- winner: A, B or TIE;
- reasoning: brief explanation separating information effect from cue effect;
- evaluations: A and B, each with criteria (list of id, status, evidence),
  readiness (string), material_failures (array of strings);
- limits: array of strings.

Generic criteria: planning only/no false execution; new request only/no replay;
no invented approved requirement; concrete expected checks; proportionate durable
updates without mandatory additional spec files. Case criteria come from the
preregistered study README, supplied with each pair. A current explicit request
can intentionally supersede an affected old promise without fresh confirmation;
unaffected promises remain. An extra contract that only duplicates clear tests
does not establish an adoption benefit.
