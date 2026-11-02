Read-only architectural planning consultation. Do not edit repository files, invoke other advisors, run live E2E campaigns, or change any configuration.

User asks: "I want to make sure that we are fully set up with the state information changes that happen between when we have an existing repo, we run a script, and we add another new prompt that would modify the features. Are we clear about the delineation of the spec file where the new features need to be implemented versus the previous spec file with the old features? Are we using this properly and then making sure those are referenced properly during the building activities? We need to make sure that those existing specs are respected unless the incoming spec actually changes the original spec items. plan this out"

Workspace /Users/dadleet/src/skill-craft, main HEAD c0bcf83dedc759a15ed924d3966bb8392422eeca. This task is a plan only, no product implementation, baseline/default/loop changes, release or deployment. Existing owner direction: scripts own durable state, small prompts; preserve stable IDs and existing specs except authorized requested changes; keep one current Markdown spec; source skills only, generated plugin outputs are release-owned. Read AGENTS.md.

Inspected current facts:
- New request gets fresh external workspace/run and literal new --prompt. Recovery is tied to same exact run/request; RUN/request.md mirrors original request in run state.
- Current living requirements are normally docs/shiploop/spec.md (KNOWLEDGE/spec.md logical home). Architecture/environment are separate standing files. Run-start HEAD in run-baseline.txt permits Git diff of spec and architecture to current content; no Git or no recorded baseline => no diff.
- spec instructions preserve R-n IDs, modify in place, move dropped requirements to Retired with reason; knowledge.check only mechanically refuses disappearance of committed IDs. It does not prove semantic preservation or validate justification of changes.
- Knowledge READS for spec is empty; spec gets path/instructions but no embedded prior spec. spec_diff is consumed by test-strategy, plan, document, carry-forward, product-acceptance, release-verify, not spec or implement. Current spec is consumed by step-plan/test-spec; later implement relies on cited plan/test spec and R-n follows.
- Inline implement/document writeback is protected: only marked acceptance additions within existing committed non-retired R-n spans; changed/deleted committed lines or new R-n are refused, send-back to planning required. Do not weaken this gate to solve stale status prose.
- workspace start snapshots tracked dirty content into isolated baseline; direct init can have dirty starting specs different from HEAD. Missing prior spec, direct non-Git, concurrent/changed source, compaction/resume need explicit treatment.

Important full commit messages reviewed:
b75963f8e8b310ac13d69fc03659fdec0085e92a fixes added requirements being their own allowed baseline spans; preserve this protection.
a7d5904985592ff36bb8cf7d48567a623e9bad88: 4 published runs pass inherited/hidden behavior, IDs preserved, modifying link updates R-2/R-3 in place; prior requirement citations sparse; one chain, no control, no general proof.
e7388075310577a7140aafc7f22ace2f5d2d0a2c: summary behavior and inherited tests all pass, but stale pending-versus-implemented spec and architecture assertions fail semantic checkpoint; no successor launched.
a232cf038789b532c8485c7583136177cb6be929: valid in-place change falsely failed a keyword/new-ID heuristic; tests must accept semantically correct in-place changes.
c30a829f568b4a4e04866bf875e3ff2acafe1c83 (another session, not ours): carry-forward-only status patch DROP; control already fixed status later; append-only document gate / send-back route gap remains separate. Do not revive rejected candidate or take over its branch/runs.

Proposed minimal direction for critique (not accepted design):
1. Keep one current effective living spec; prior spec is frozen run-start baseline (prefer existing Git object, materialized read-only view only if needed), new prompt remains immutable run input, run-scoped change record distinguishes proposed changes and their rationale.
2. Explicitly account for each existing requirement as preserved by default; only touched IDs need authored disposition/basis (modify/retire/restore) and additions get fresh stable IDs. Mere omission from incoming prompt is not repeal. Status/evidence updates must not be confused with product meaning changes. Existing approved but not implemented features remain deferred unless incoming request activates them.
3. Ensure spec reconciliation sees actual prior contents and original new request; retain known current behavior separately from intended requirements; conflicts or ambiguity go through existing clarification/replanning path, no last-file-wins inference.
4. Thread baseline identity, current spec identity and relevant new/changed/preserved R-n references into planning, step plans, test cases, implementation and review packets using existing stage surfaces. Script verifies structural identity/coverage where reliable, model judges semantic conflicts; no parser claiming prose equivalence, no requirement to quote every old spec in every prompt, no new blanket stage/gates without evidence.
5. Check incremental regression across add feature / modify existing rule / unrelated feature / deferred requirement activation / removal / ambiguous conflict / interrupted recovery / missing-or-dirty baseline. Preserve pristine earlier tests except checks explicitly superseded by authorized behavior changes. Compare candidate to frozen control before shipping, use existing harness and default profile, retain failure evidence.

Please answer with: (a) strongest concrete risks/gaps in that proposal relative to current code; (b) smallest sufficient design and implementation order; (c) what to avoid adding; (d) smallest useful validations and acceptance criteria. Challenge whether any new state/schema is needed versus better use of existing baseline/result artifacts. Distinguish observed facts from proposals.

Relevant source paths:
/Users/dadleet/src/skill-craft/skills/shiploop/scripts/shiploop_knowledge_home.py
/Users/dadleet/src/skill-craft/skills/shiploop/scripts/shiploop_request.py
/Users/dadleet/src/skill-craft/skills/shiploop/scripts/shiploop_navigator.py
/Users/dadleet/src/skill-craft/skills/shiploop/scripts/shiploop_stage_spec.py
/Users/dadleet/src/skill-craft/skills/shiploop/references/project-knowledge.md
/Users/dadleet/src/skill-craft/skills/shiploop/references/execution-planning.md
/Users/dadleet/src/skill-craft/test/shiploop-knowledge.test.py
/Users/dadleet/src/skill-craft/test/shiploop-cross-run.test.py
/Users/dadleet/src/skill-craft/docs/experiments/incremental-feature-chain-20261101/README.md
