# E6b excerpt: the planning review and platform claims

Copied on 2026-10-05 from `docs/shiploop-composition-state-experiments-2026-09-26.md` (the paragraph of section "E6 and
E6b: platform claims" about the planning review, the header and one row of the table in "After implementation: rerun
on the shipped text", and the closing paragraph of that section), so the figure the SPEC carve-out cites is kept with
the decision's evidence. The text between the rules is unchanged. Limits that document states, and the attack that
asked for this copy repeats: Sonnet, condensed packets, five plans with three trials each (15 trials per cell), and
the judge shares the gaps of the reviewer (no web access).

---

**Planning review, real errors (30 trials).** The five E1 plans with real errors
went through the current planning review focus, and through the focus plus:

> a claim about what the runtime, platform or a library can do that a decision
> depends on, with no primary-documentation source or probe result: check it,
> and correct the plan where it is wrong

The current focus caught 0/15; with the bullet, 10/15. The judge also reported ten
new errors in those reviews. On inspection about three are real (for example
`DmlException` where Salesforce throws `QueryException`); others are the judge
lacking web access, such as the documented rule that ORDER BY cannot be used in
a locking query. Errors enter at the plan stage, after research, so the review
that follows the plan is where to check them.

---

| Measure | Before (current wording) | Experiment wording | Shipped text |
| --- | --- | --- | --- |
| Planning review catches plan-stage platform errors | 0/15 | 10/15 | 10/15 |

---

Planning reviews with the claim bullet again added some platform claims the
judge (without web access) rated wrong: 6 across 15 reviews, fewer than the 10
in E6b, with the same caveat that several are the judge's own gaps.

