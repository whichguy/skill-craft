# Render diff: node-fix-bug / inline/163/96, unit U11

- old <render>/before-inline-163 (commit e4c675d522e2)
- new <render>/after-inline-163 (commit e4c675d522e2)
- the head table is NOT checked (--no-head-table)

| stage | printed old | printed new | Δ | table | to host cut | whole old | whole new | moved lines | result |
|---|--:|--:|--:|--:|--:|--:|--:|--:|---|
| step-plan | 22149 | 22089 | -60 | – | -2089 | 26127 | 26067 | 0 | ok |
| step-plan-improve | 3007 | 3007 | +0 | – | 16993 | 3007 | 3007 | 0 | ok |
| test-spec | 15938 | 15982 | +44 | – | 4018 | 15938 | 15982 | 0 | ok |
| test-spec-improve | 2239 | 2239 | +0 | – | 17761 | 2239 | 2239 | 0 | ok |
| validate-existing | 13322 | 13369 | +47 | – | 6631 | 16379 | 16426 | 0 | ok |
| implement | 16000 | 16047 | +47 | – | 3953 | 19105 | 19152 | 0 | ok |
| implement-improve | 2948 | 2948 | +0 | – | 17052 | 2948 | 2948 | 0 | ok |
| test | 16962 | 17190 | +228 | – | 2810 | 21656 | 21884 | 0 | ok |
| document | 15309 | 15356 | +47 | – | 4644 | 15309 | 15356 | 0 | ok |
| verify | 17404 | 17281 | -123 | – | 2719 | 21722 | 21599 | 0 | ok |
| carry-forward | 18388 | 18435 | +47 | – | 1565 | 23478 | 23525 | 0 | ok |
| carry-forward-improve | 2936 | 2936 | +0 | – | 17064 | 2936 | 2936 | 0 | ok |

## step-plan
  -    93  [PW]      large for the loop contract is refused: shorten IDs, drop duplicates or split the item.
  -   113  [PW]    - Every criterion is named in some command's `criteria`, and a command names only listed criteria. A list …
  -  1254  [PW] Checked by: at done ShipLoop checks the Until Loop receipt (in evidence_refs) against the contract and refuse…
  -   555  [PW] Work: Do duty items 1-12 of /home/render/wwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwww/wwwwwwwwwwwwwwwwwwwwwwwwwww…
  +   102  [PW]    - Every criterion is named in some command's `criteria`, and a command names only listed criteria.   <- U11 offset: - Every criterion is named in some command's `criteria` | large for the loop contract is refused
  +  1301  [PW] Checked by: at done ShipLoop checks the Until Loop receipt (in evidence_refs) against the contract and refuse…   <- U11 approval: efficiency plan 3.2 rows SP-5, TD-6, SPEC-7, VR-6 and rev 4 Step 8.1 (U11): the false tail 'prints every refusal first' becomes 'prints the first refusal without accepting, so repeat it until it accepts' (+47 per producer packet)
  +   552  [PW] Work: Do duty items 1-12 of /home/render/wwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwww/wwwwwwwwwwwwwwwwwwwwwwwwwww…   <- U11 approval: efficiency plan 3.2 rows SP-5, TD-6, SPEC-7, VR-6 and rev 4 Step 8.1 (U11): the duty range is generated from the parsed duty count (test-spec 1-7, implement 1-7, test 1-8, document 1-7, carry-forward 1-4, verify 1-9); the check-only clause is the Callback command with the flag added

## test-spec
  -   892  [PW] Checked by: at done ShipLoop checks the Until Loop receipt (in evidence_refs) against the contract and refuse…
  -   352  [PW] Work: Do duty items 1-6 of /home/render/wwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwww/wwwwwwwwwwwwwwwwwwwwwwwwwwww…
  +   939  [PW] Checked by: at done ShipLoop checks the Until Loop receipt (in evidence_refs) against the contract and refuse…   <- U11 approval: efficiency plan 3.2 rows SP-5, TD-6, SPEC-7, VR-6 and rev 4 Step 8.1 (U11): the false tail 'prints every refusal first' becomes 'prints the first refusal without accepting, so repeat it until it accepts' (+47 per producer packet)
  +   349  [PW] Work: Do duty items 1-7 of /home/render/wwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwww/wwwwwwwwwwwwwwwwwwwwwwwwwwww…   <- U11 approval: efficiency plan 3.2 rows SP-5, TD-6, SPEC-7, VR-6 and rev 4 Step 8.1 (U11): the duty range is generated from the parsed duty count (test-spec 1-7, implement 1-7, test 1-8, document 1-7, carry-forward 1-4, verify 1-9); the check-only clause is the Callback command with the flag added

## validate-existing
  -   685  [PW] Checked by: at done ShipLoop checks the Until Loop receipt (in evidence_refs) against the contract and refuse…
  -   353  [PW] Work: Take the first expectation whose check does not match its state and do duty items 1-2 of /home/render/w…
  +   732  [PW] Checked by: at done ShipLoop checks the Until Loop receipt (in evidence_refs) against the contract and refuse…   <- U11 approval: efficiency plan 3.2 rows SP-5, TD-6, SPEC-7, VR-6 and rev 4 Step 8.1 (U11): the false tail 'prints every refusal first' becomes 'prints the first refusal without accepting, so repeat it until it accepts' (+47 per producer packet)
  +   353  [PW] Work: Take the first expectation whose check does not match its state and do duty items 1-4 of /home/render/w…   <- U11 approval: efficiency plan 3.2 rows SP-5, TD-6, SPEC-7, VR-6 and rev 4 Step 8.1 (U11): validate-existing cites duty items 1-4

## implement
  -   817  [PW] Checked by: at done ShipLoop checks the Until Loop receipt (in evidence_refs) against the contract and refuse…
  +   864  [PW] Checked by: at done ShipLoop checks the Until Loop receipt (in evidence_refs) against the contract and refuse…   <- U11 approval: efficiency plan 3.2 rows SP-5, TD-6, SPEC-7, VR-6 and rev 4 Step 8.1 (U11): the false tail 'prints every refusal first' becomes 'prints the first refusal without accepting, so repeat it until it accepts' (+47 per producer packet)

## test
  -  1057  [PW] Checked by: at done ShipLoop checks the Until Loop receipt (in evidence_refs) against the contract and refuse…
  -   541  [PW] Repeat while a case has no test or the latest iteration found a failing command, a missing ID, a count below …
  -   599  [PW] Work: Do duty items 1-4 of /home/render/wwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwww/wwwwwwwwwwwwwwwwwwwwwwwwwwww…
  +  1104  [PW] Checked by: at done ShipLoop checks the Until Loop receipt (in evidence_refs) against the contract and refuse…   <- U11 approval: efficiency plan 3.2 rows SP-5, TD-6, SPEC-7, VR-6 and rev 4 Step 8.1 (U11): the false tail 'prints every refusal first' becomes 'prints the first refusal without accepting, so repeat it until it accepts' (+47 per producer packet)
  +   562  [PW] Repeat while a case has no test or the latest iteration found a failing command, a missing ID, a count below …   <- U11 approval: efficiency plan 3.2 rows SP-5, TD-6, SPEC-7, VR-6 and rev 4 Step 8.1 (U11): 'a lint finding or a check-only refusal'
  +   759  [PW] Work: Do duty items 1-8 of /home/render/wwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwww/wwwwwwwwwwwwwwwwwwwwwwwwwwww…   <- U11 approval: efficiency plan 3.2 rows SP-5, TD-6, SPEC-7, VR-6 and rev 4 Step 8.1 (U11): the duty range is generated from the parsed duty count (test-spec 1-7, implement 1-7, test 1-8, document 1-7, carry-forward 1-4, verify 1-9); the check-only clause is the Callback command with the flag added

## document
  -   461  [PW] Checked by: at done ShipLoop checks the Until Loop receipt (in evidence_refs) against the contract and refuse…
  -   483  [PW] Work: Do duty items 1-5 of /home/render/wwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwww/wwwwwwwwwwwwwwwwwwwwwwwwwwww…
  +   508  [PW] Checked by: at done ShipLoop checks the Until Loop receipt (in evidence_refs) against the contract and refuse…   <- U11 approval: efficiency plan 3.2 rows SP-5, TD-6, SPEC-7, VR-6 and rev 4 Step 8.1 (U11): the false tail 'prints every refusal first' becomes 'prints the first refusal without accepting, so repeat it until it accepts' (+47 per producer packet)
  +   483  [PW] Work: Do duty items 1-7 of /home/render/wwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwww/wwwwwwwwwwwwwwwwwwwwwwwwwwww…   <- U11 approval: efficiency plan 3.2 rows SP-5, TD-6, SPEC-7, VR-6 and rev 4 Step 8.1 (U11): the duty range is generated from the parsed duty count (test-spec 1-7, implement 1-7, test 1-8, document 1-7, carry-forward 1-4, verify 1-9); the check-only clause is the Callback command with the flag added

## verify
  -   108  [PW]    policy (Workspace integration guidance). The original branch returns only at the final workspace return.
  -   116  [PW] 8. **Assembly.** Confirm the item's candidate is assembled in the execution checkout under workspace and repo…
  -  1042  [PW] Checked by: at done ShipLoop checks the Until Loop receipt (in evidence_refs) against the contract and refuse…
  -   326  [PW] Work: Do duty items 1-7 of /home/render/wwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwww/wwwwwwwwwwwwwwwwwwwwwwwwwwww…
  -    10  [PW] in order.
  +  1089  [PW] Checked by: at done ShipLoop checks the Until Loop receipt (in evidence_refs) against the contract and refuse…   <- U11 approval: efficiency plan 3.2 rows SP-5, TD-6, SPEC-7, VR-6 and rev 4 Step 8.1 (U11): the false tail 'prints every refusal first' becomes 'prints the first refusal without accepting, so repeat it until it accepts' (+47 per producer packet)
  +   326  [PW] Work: Do duty items 1-9 of /home/render/wwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwww/wwwwwwwwwwwwwwwwwwwwwwwwwwww…   <- U11 approval: efficiency plan 3.2 rows SP-5, TD-6, SPEC-7, VR-6 and rev 4 Step 8.1 (U11): the duty range is generated from the parsed duty count (test-spec 1-7, implement 1-7, test 1-8, document 1-7, carry-forward 1-4, verify 1-9); the check-only clause is the Callback command with the flag added
  +    64  [PW] in order; items 8-9 once, before you report the exit satisfied.   <- U11 approval: efficiency plan 3.2 rows SP-5, TD-6, SPEC-7, VR-6 and rev 4 Step 8.1 (U11) (VR-6): verify's duty says which items repeat

## carry-forward
  -   769  [PW] Checked by: at done ShipLoop checks the Until Loop receipt (in evidence_refs) against the contract and refuse…
  -   488  [PW] Work: Do duty items 1-3 of /home/render/wwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwww/wwwwwwwwwwwwwwwwwwwwwwwwwwww…
  +   816  [PW] Checked by: at done ShipLoop checks the Until Loop receipt (in evidence_refs) against the contract and refuse…   <- U11 approval: efficiency plan 3.2 rows SP-5, TD-6, SPEC-7, VR-6 and rev 4 Step 8.1 (U11): the false tail 'prints every refusal first' becomes 'prints the first refusal without accepting, so repeat it until it accepts' (+47 per producer packet)
  +   488  [PW] Work: Do duty items 1-4 of /home/render/wwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwww/wwwwwwwwwwwwwwwwwwwwwwwwwwww…   <- U11 approval: efficiency plan 3.2 rows SP-5, TD-6, SPEC-7, VR-6 and rev 4 Step 8.1 (U11): the duty range is generated from the parsed duty count (test-spec 1-7, implement 1-7, test 1-8, document 1-7, carry-forward 1-4, verify 1-9); the check-only clause is the Callback command with the flag added

All 12 stages pass.
P = printed text, W = whole text (the packet file); sizes are characters including the newline.
