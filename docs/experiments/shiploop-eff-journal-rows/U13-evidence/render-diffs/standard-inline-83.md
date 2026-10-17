# Render diff: node-fix-bug / inline/83/96, unit U13

- old /private/tmp/claude-501/-Users-dadleet-src-skill-craft/8acf399b-0cf4-40cc-bba3-bf238461db58/scratchpad/eff2/U13/base/inline-83 (commit 5e0ef0d0d107)
- new /private/tmp/claude-501/-Users-dadleet-src-skill-craft/8acf399b-0cf4-40cc-bba3-bf238461db58/scratchpad/eff2/U13/new/inline-83 (commit 5e0ef0d0d107)
- the head table is checked

| stage | printed old | printed new | Δ | table | to host cut | whole old | whole new | moved lines | result |
|---|--:|--:|--:|--:|--:|--:|--:|--:|---|
| step-plan | 19988 | 19988 | +0 | 19988 | 12 | 23351 | 23303 | 0 | ok |
| step-plan-improve | 2713 | 2713 | +0 | 2713 | 17287 | 2687 | 2687 | 0 | ok |
| test-spec | 14759 | 14711 | -48 | 14711 | 5289 | 14733 | 14685 | 0 | ok |
| test-spec-improve | 1945 | 1945 | +0 | 1945 | 18055 | 1919 | 1919 | 0 | ok |
| validate-existing | 15283 | 15235 | -48 | 15235 | 4765 | 15257 | 15209 | 0 | ok |
| implement | 15763 | 15763 | +0 | 15763 | 4237 | 18286 | 18238 | 0 | ok |
| implement-improve | 2654 | 2654 | +0 | 2654 | 17346 | 2628 | 2628 | 0 | ok |
| test | 18239 | 17842 | -397 | 17842 | 2158 | 20470 | 20025 | 0 | ok |
| document | 14116 | 14068 | -48 | 14068 | 5932 | 14090 | 14042 | 0 | ok |
| verify | 18188 | 18188 | +0 | 18188 | 1812 | 20408 | 20360 | 0 | ok |
| carry-forward | 18028 | 18028 | +0 | 18028 | 1972 | 22179 | 22131 | 0 | ok |
| carry-forward-improve | 2642 | 2642 | +0 | 2642 | 17358 | 2616 | 2616 | 0 | ok |

## step-plan
  -    48  [W] Summary: as the status block's Done line shows.

## test-spec
  -    48  [PW] Summary: as the status block's Done line shows.

## validate-existing
  -    48  [PW] Summary: as the status block's Done line shows.

## implement
  -    48  [W] Summary: as the status block's Done line shows.

## test
  -   472  [PW] Base run: before the candidate run, ShipLoop runs every focused and regression command on the item's base (a …
  -   577  [PW] Each focused and regression command must also run at least its floor: the larger of the tests it ran on the i…
  -   293  [PW] Optional at test: "red_na": [{"id": "<a focused test ID>", "reason": "<why it already passes without this cha…
  -    48  [W] Summary: as the status block's Done line shows.
  +   446  [PW] Base run: before the candidate run, ShipLoop runs every focused and regression command on the item's base (a …   <- U13 offset: Base run: before the candidate run
  +   499  [PW] Each focused and regression command must also run at least its floor: the larger of the tests it ran on the i…   <- U13 offset: Each focused and regression command must also run

## document
  -    48  [PW] Summary: as the status block's Done line shows.

## verify
  -    48  [W] Summary: as the status block's Done line shows.

## carry-forward
  -    48  [W] Summary: as the status block's Done line shows.

All 12 stages pass.
P = printed text, W = whole text (the packet file); sizes are characters including the newline.
