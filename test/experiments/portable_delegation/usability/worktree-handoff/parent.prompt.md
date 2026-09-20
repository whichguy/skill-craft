Use the Ask Agent U18 skill to run W1 with fresh general-purpose native workers. Do not
edit source or production files except the final parent-owned integration of the stated
pricing.json field. Do not use a dispatcher, shell model launcher, model mask/downgrade,
shared checkout worker, temporary result folder, sleep, polling loop or busywork.

Inputs supplied by operator:
- Current caller checkout: <SOURCE_CHECKOUT>
- Current Git root: <SOURCE_GIT_ROOT>
- Current branch and HEAD: <SOURCE_BRANCH>, <SOURCE_HEAD>
- Parent integration target and last checked revision: <INTEGRATION_TARGET>, <INTEGRATION_TARGET_SHA>
- Effective model selector, only if this host requires one: <EFFECTIVE_MODEL_SELECTOR_OR_NONE>
- Primary-main relationship evidence: <PRIMARY_MAIN_EVIDENCE>
- Frozen U18 main/reference: <U18_MAIN_PATH>, <U18_REFERENCE_PATH>
- Source snapshot/baseline receipt: <SOURCE_BASELINE_RECEIPT>
- Durable inbox outside every worker worktree: <DURABLE_INBOX>
- Code worker worktree/branch: <CODE_WORKTREE>, <CODE_BRANCH>
- Report worker worktree/branch: <REVIEW_WORKTREE>, <REVIEW_BRANCH>

First read the frozen U18 main skill and Git-integration reference at the supplied paths.
Then prepare and verify each worker worktree yourself from the current caller checkout,
including staged and unstaged layers, staged addition, unstaged deletion, untracked notes
and pricing input. Record observed source/worktree roots, baseline revision and inherited
snapshot. Do not dispatch unless the copy is faithful.

For each native launch, put the complete assignment, absolute assigned worktree and Git-root
paths, inherited-baseline receipt, U18 policy constraints and report/lifecycle requirements
in that native prompt itself. Retain the actual native dispatch schema/arguments as evidence;
do not generate or rely on a separate worker-transport prompt file.

Launch a fresh general-purpose worker with descriptive label pricing-handoff reviewer to
implement exactly discount_rate: 0.10 in pricing.json inside CODE_WORKTREE. It must not
modify dual.txt, staged-add.txt, deleted.txt, unstaged.txt or notes.txt. Its direct native
assignment requires it to make a worker-only contribution distinct from inherited dirty
state: do not stage, commit or otherwise include any inherited sentinel. It validates JSON,
then records its pricing-only contribution as an identifiable commit or patch. It creates at
least `reports/handoff-index.md` and `reports/validation.md` inside CODE_WORKTREE, and returns
actual cwd/root/baseline/contribution/test/report/lifecycle facts.

After confirmed launch, continue useful parent analysis: explain from SOURCE_BASELINE_RECEIPT
which inherited layers cannot be merged as worker contribution and why prepared work is not
integrated/accepted. Then launch a second fresh general-purpose worker with the same
descriptive label and a distinct handle/worktree, to independently audit its own snapshot
fidelity and report recovery in REVIEW_WORKTREE. Its direct assignment is
read-only against inputs except its own `reports/handoff-index.md` and
`reports/snapshot-audit.md`; it verifies its inherited sentinels. Launch this report worker
even when code work has already completed. If both were not pending together, record the
overlap predicate UNOBSERVED without forcing timing. Record UNSUPPORTED only when the host
cannot launch the required fresh report worker.

Collect actual returns through native notification or join. Verify report paths, observed
worktree/root, contribution relative to inherited baseline, and current target state. Copy
the durable handoff receipt/index and every required referenced result to DURABLE_INBOX before
any removal, updating final links if a path changes. Parent alone decides:
integrate only pricing.json worker contribution then validate and remove when ready; remove
report-only worktree after consumption; or retain a blocked/needed worktree with next owner.
Final synthesis separates worker completion, parent integration, source preservation and
public trace. Never claim success from a child receipt alone.
