# Review Coverage ledger contract

ShipLoop treats Review Coverage as outer-loop evidence, not a text assertion.
The ledger must be the repository's actual REVIEW_CONVERGE.md, bind to the
current plan path and hash, report complete, and be present as a clean tracked
Git blob. A stale, foreign, untracked, dirty, or merely claimed ledger is not
coverage completion.

The accepted public status grammar is:

~~~text
(?im)\bStatus\b[^\n]*(?P<state>stopped\s*\([^\n)]*\)|complete\b|active\b)
~~~

The plan binding is a plan contract line plus 64-hex plan hash:

~~~text
**Plan contract:** <path>
**Plan hash:** <sha256>
~~~

A completed latest Round uses an H3 heading and a committed marker. Both plain
`Committed: yes` and bold `**Committed:** yes` are accepted:

~~~markdown
## Log

### Round 2

Forward: <actual spec-to-product review>
Reverse: <actual diff-to-regression review>
Suite: PASS — <checks actually run>
Committed: yes
~~~

The latest round's Git commit subject must begin `review-converge: round 2 —`
(or `grok-review-converge: round 2 —`), substituting the actual round number.
That commit must change `REVIEW_CONVERGE.md` and contain its current exact
blob, which must also be clean and tracked at HEAD. A matching subject on an
unrelated commit is not evidence. Record actual outer reviews; do not relabel
inner-loop receipts as outer rounds.

Committed: no and stopped(...) are not success. An explicit waiver only counts
when it already appears, unfenced, in the bound plan's Review Coverage section
with a concrete reason. It cannot waive fresh outer acceptance/integration
checks or a corrective step made necessary by later learning.
