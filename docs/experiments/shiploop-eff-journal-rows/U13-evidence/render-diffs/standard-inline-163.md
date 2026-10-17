# Render diff: node-fix-bug / inline/163/96, unit U13

- old /private/tmp/claude-501/-Users-dadleet-src-skill-craft/8acf399b-0cf4-40cc-bba3-bf238461db58/scratchpad/eff2/U13/base/inline-163 (commit 5e0ef0d0d107)
- new /private/tmp/claude-501/-Users-dadleet-src-skill-craft/8acf399b-0cf4-40cc-bba3-bf238461db58/scratchpad/eff2/U13/new/inline-163 (commit 5e0ef0d0d107)
- the head table is checked

| stage | printed old | printed new | Δ | table | to host cut | whole old | whole new | moved lines | result |
|---|--:|--:|--:|--:|--:|--:|--:|--:|---|
| step-plan | 19774 | 19774 | +0 | 19817 | 226 | 24871 | 24823 | 0 | ok |
| step-plan-improve | 3033 | 3033 | +0 | 3033 | 16967 | 3007 | 3007 | 0 | ok |
| test-spec | 14216 | 14216 | +0 | 15909 | 5784 | 16093 | 16045 | 0 | ok |
| test-spec-improve | 2265 | 2265 | +0 | 2265 | 17735 | 2239 | 2239 | 0 | ok |
| validate-existing | 13922 | 13922 | +0 | 13629 | 6078 | 16617 | 16569 | 0 | FAIL |
| implement | 16723 | 16723 | +0 | 16637 | 3277 | 19246 | 19198 | 0 | FAIL |
| implement-improve | 2974 | 2974 | +0 | 2974 | 17026 | 2948 | 2948 | 0 | ok |
| test | 19759 | 19362 | -397 | 19370 | 638 | 21990 | 21545 | 0 | ok |
| document | 15556 | 15508 | -48 | 15263 | 4492 | 15530 | 15482 | 0 | FAIL |
| verify | 19548 | 19548 | +0 | 19430 | 452 | 21768 | 21720 | 0 | FAIL |
| carry-forward | 19468 | 19468 | +0 | 19175 | 532 | 23699 | 23651 | 0 | FAIL |
| carry-forward-improve | 2962 | 2962 | +0 | 2962 | 17038 | 2936 | 2936 | 0 | ok |

## step-plan
  -    48  [W] Summary: as the status block's Done line shows.

## test-spec
  -    48  [W] Summary: as the status block's Done line shows.

## validate-existing
  FAIL head table: printed 13922 passes the table value 13629
  -    48  [W] Summary: as the status block's Done line shows.

## implement
  FAIL head table: printed 16723 passes the table value 16637
  -    48  [W] Summary: as the status block's Done line shows.

## test
  -   472  [PW] Base run: before the candidate run, ShipLoop runs every focused and regression command on the item's base (a …
  -   577  [PW] Each focused and regression command must also run at least its floor: the larger of the tests it ran on the i…
  -   293  [PW] Optional at test: "red_na": [{"id": "<a focused test ID>", "reason": "<why it already passes without this cha…
  -    48  [W] Summary: as the status block's Done line shows.
  +   446  [PW] Base run: before the candidate run, ShipLoop runs every focused and regression command on the item's base (a …   <- U13 offset: Base run: before the candidate run
  +   499  [PW] Each focused and regression command must also run at least its floor: the larger of the tests it ran on the i…   <- U13 offset: Each focused and regression command must also run

## document
  FAIL head table: printed 15508 passes the table value 15263
  -    48  [PW] Summary: as the status block's Done line shows.

## verify
  FAIL head table: printed 19548 passes the table value 19430
  -    48  [W] Summary: as the status block's Done line shows.

## carry-forward
  FAIL head table: printed 19468 passes the table value 19175
  -    48  [W] Summary: as the status block's Done line shows.

5 of 12 stages fail.
P = printed text, W = whole text (the packet file); sizes are characters including the newline.
