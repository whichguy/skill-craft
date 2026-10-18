# Backchain route

Split from the ShipLoop skill card (`../SKILL.md`). Read at a planning stage whose packet names Backchain, and before choosing `--backchain-passes`.

## Backchain passes option

`--backchain-passes one|converge|none` at `init` or `workspace start` records the
run option `backchain_passes` (default `one`): how many passes the Backchain
planning child may take. `one` is one review/fix/check cycle, `converge` is two
consecutive trivial reviews, and `none` offers no whole Backchain loop at `plan`. The `one`
plan packet prints the gate and an exit condition, which the host copies into the child's
start contract, and says the child is the host's choice (nothing refuses a plan without it
and ShipLoop cannot see whether it ran) and that the result's summary names the route taken;
the `converge` plan packet prints the two-review gate, and the host takes its
exit condition from Backchain's convergence reference. In `none` the plan packet prints the
read-only audit route the other Backchain stages print (the one resource it needs and the
loop-resource status line), says no whole `plan`/`draft` is requested in this run, and
omits the six-file Backchain and Until Loop resource block; a material finding at any stage
still allows one `repair`/`revise`, which runs one pass.
Like `lint`, a saved run without the key is refused (start a fresh run), never
migrated, and an `init` or `workspace start` retry cannot change it. Unlike
`lint`, no verb changes it mid-run: a fresh run is the route to another value.
Improve's review loops are not covered by it.

## Source-aware Backchain selection

`source-aware-native` is the only Backchain route; there is no embedded
Backchain mode. A planning host that calls Backchain records the selection in
ordinary run notes. The native selection binds
the observed Backchain `SKILL.md`, `backchain-caller/v1` action/stage resource,
`references/convergence.md`, and `prompts/convergence-review.prompt.md`, plus the selected
physical Until Loop root with its card, `references/runtime-ephemeral.md`, and
`scripts/until_loop_ephemeral.py` capability. It records their identities, action ID/owner,
original source/candidate identities, locator bases plus resolved paths, protected bounds,
and receipts. Read the Backchain convergence resources; they must support the direct natural-language
handoff under `Backchain standalone Until Loop binding: <binding-id>`: a plan-only child
where the actual loaded Until Loop card starts its adapter, is the sole CLI caller, and
returns the exact terminal packet. Caller/v1 alone is insufficient; reject an observed old
custom Backchain loop even when an Until Loop package is installed. A recovery reopens these
records rather than deriving either skill root from CWD or a same-named package.

A selected native `plan`/`draft` or authorized `repair`/`revise` is one whole
Backchain operation. Backchain supplies its dependency-specific review/fix/check
work, plan candidate files, source/lens context, and protected bounds to the selected
actual Until Loop using `Backchain standalone Until Loop binding: <binding-id>`. Until
Loop owns the temporary callback handle, progress, its review gate (the packet's printed
gate for the run's Backchain passes option; a `repair`/`revise` packet in `one` and `none`
points to Backchain's convergence reference for it, and in `converge` the default two-review
gate applies), recovery, continuation, and terminal transition; ShipLoop owns
none of those controls. Backchain
returns only opaque actual Until Loop terminal evidence after the child reports
`complete` and its exact receipt is saved, plus its domain evidence: binding_id, owner,
candidate input/output digests, resolved resources, opaque `terminal_receipt`,
domain_evidence, planning_gaps, execution_blockers, and next_action. A nonterminal,
missing, blocked, stopped, cancelled, damaged, or incompatible child leaves the parent
action incomplete. Only its exact `complete` receipt plus final candidate identity and
domain evidence permits Backchain planning convergence. `review`/`audit`
remains read-only and one-pass; it does not start Until Loop. Ordinary ShipLoop Improve
stays independent and never starts a nested whole Backchain→Until Loop child; it uses
only a one-pass Backchain primitive for a relevant diagnostic.

The Until Loop child is plan-only: it may change the candidate plan and permitted planning
companions, but may not commit, push, merge, execute the project, or broaden scope.

Graph check (record only): a Backchain stage's packet prints
`python3 "$CLI" backchain-check --run-dir "$RUN_DIR" --candidate <your candidate file>`.
It checks the candidate, packaged first, against Backchain's seven structural invariants,
prints a JSON receipt and writes it with a snapshot of the checked bytes under
`backchain/<action>/`; exit 0 valid, 1 invalid, 3 could not run. Treat a failure as a
loop finding and cite the receipt in `evidence_refs`; nothing is refused.


Use the selected card only when it and the contract/resource are observed and
compatible. A missing, stale, ambiguous, or incompatible material input is an
incomplete/blocked native request with its recovery locator, not permission to
guess or silently use another package. The host judges
capability and source adequacy, including the host-judged semantic compatibility of
the direct handoff; the ShipLoop script does not claim to machine-enforce those
judgments.
