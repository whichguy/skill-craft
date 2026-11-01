---
bump: minor
---
Step-plan now refuses a plan in which an executed criterion that a focused command names has no focused test ID of its
own. Test-spec writes one case per focused ID, and each case names one criterion, so such a plan left a criterion
without a case. In the saved runs of 2026-10-25 to 11-01, 24 of 175 step plans did this: 9 came back from test-spec as a
send-back, and 15 folded the criterion into another criterion's case. The refusal names the criteria and the IDs listed.
The step-plan result template now lists one ID per criterion its focused row names; with an open item due at the item,
it had shown three criteria and two IDs. The duty asks for an ID for each executed criterion a focused command names
(a searched criterion gets none: test-spec writes it no case), and the Checked-by line names the refusal.
