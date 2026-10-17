# Render diff: node-fix-bug / ask-agent/83/96, unit U13

- old /private/tmp/claude-501/-Users-dadleet-src-skill-craft/8acf399b-0cf4-40cc-bba3-bf238461db58/scratchpad/eff2/U13/base/ask-agent-83 (commit 5e0ef0d0d107)
- new /private/tmp/claude-501/-Users-dadleet-src-skill-craft/8acf399b-0cf4-40cc-bba3-bf238461db58/scratchpad/eff2/U13/new/ask-agent-83 (commit 5e0ef0d0d107)
- the head table is checked

| stage | printed old | printed new | Δ | table | to host cut | whole old | whole new | moved lines | result |
|---|--:|--:|--:|--:|--:|--:|--:|--:|---|
| step-plan | 19449 | 19449 | +0 | 19449 | 551 | 26742 | 26694 | 0 | ok |
| step-plan-improve | 2713 | 2713 | +0 | 2713 | 17287 | 2687 | 2687 | 0 | ok |
| test-spec | 12856 | 12856 | +0 | 12856 | 7144 | 16301 | 16253 | 0 | ok |
| test-spec-improve | 1945 | 1945 | +0 | 1945 | 18055 | 1919 | 1919 | 0 | ok |
| validate-existing | 12562 | 12562 | +0 | 12562 | 7438 | 16825 | 16777 | 0 | ok |
| implement | 17217 | 17217 | +0 | 17217 | 2783 | 21386 | 21338 | 0 | ok |
| implement-improve | 2654 | 2654 | +0 | 2654 | 17346 | 2628 | 2628 | 0 | ok |
| test | 18239 | 17842 | -397 | 17842 | 2158 | 22038 | 21593 | 0 | ok |
| document | 15684 | 15636 | -48 | 15636 | 4364 | 15658 | 15610 | 0 | ok |
| verify | 18608 | 18608 | +0 | 18608 | 1392 | 22396 | 22348 | 0 | ok |
| carry-forward | 19294 | 19294 | +0 | 19294 | 706 | 25013 | 24965 | 0 | ok |
| carry-forward-improve | 2642 | 2642 | +0 | 2642 | 17358 | 2616 | 2616 | 0 | ok |

## step-plan
  -    48  [W] Summary: as the status block's Done line shows.

## test-spec
  -    48  [W] Summary: as the status block's Done line shows.

## validate-existing
  -    48  [W] Summary: as the status block's Done line shows.

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
