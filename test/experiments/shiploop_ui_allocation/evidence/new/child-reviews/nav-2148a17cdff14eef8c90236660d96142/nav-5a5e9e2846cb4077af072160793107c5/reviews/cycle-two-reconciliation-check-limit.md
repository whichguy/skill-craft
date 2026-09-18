# Cycle-two reconciliation-check limitation

`cycle-two-reconciliation-check-stdout.json` returned false only because one assertion expected a particular combined sentence from the correction note. The correction note contained the same applicable boundary in separate sentences: child-only/no-rewrite scope, W6 as the actual target/consumer boundary, no external operation, and removal of the unsupported edge.

That literal assertion did not reveal a plan defect and was not treated as a review finding. `cycle-two-reconciliation-check-corrected-stdout.json` replaces it with explicit checks for the four actual invariants and passed. Both raw outputs are retained; neither is a product test or target/consumer receipt.
