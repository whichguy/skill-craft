# Head table, unit U8 (node-fix-bug, offline; characters of the printed text)

Before = the integration branch tip 5e0ef0d0, after = this branch. `to cut` = 20,000 minus after. A packet over 16,000 (PRINT_LIMIT) prints a head and keeps the rest in its file; one under it prints whole.

| route / run dir | stage | before | after | delta | form before -> after | to the 20,000 cut |
|---|---|--:|--:|--:|---|--:|
| inline / 83 | step-plan | 19988 | 19759 | -229 | head -> head | 241 |
| inline / 83 | step-plan-improve | 2713 | 2627 | -86 | whole -> whole | 17373 |
| inline / 83 | test-spec | 14759 | 15715 | +956 | whole -> whole | 4285 |
| inline / 83 | test-spec-improve | 1945 | 1859 | -86 | whole -> whole | 18141 |
| inline / 83 | validate-existing | 15283 | 12762 | -2521 | whole -> head | 7238 |
| inline / 83 | implement | 15763 | 15963 | +200 | head -> head | 4037 |
| inline / 83 | implement-improve | 2654 | 2568 | -86 | whole -> whole | 17432 |
| inline / 83 | test | 18239 | 18439 | +200 | head -> head | 1561 |
| inline / 83 | document | 14116 | 15072 | +956 | whole -> whole | 4928 |
| inline / 83 | verify | 18188 | 18388 | +200 | head -> head | 1612 |
| inline / 83 | carry-forward | 18028 | 18228 | +200 | head -> head | 1772 |
| inline / 83 | carry-forward-improve | 2642 | 2556 | -86 | whole -> whole | 17444 |
| inline / 163 | step-plan | 19774 | 19634 | -140 | head -> head | 366 |
| inline / 163 | step-plan-improve | 3033 | 2947 | -86 | whole -> whole | 17053 |
| inline / 163 | test-spec | 14216 | 14336 | +120 | head -> head | 5664 |
| inline / 163 | test-spec-improve | 2265 | 2179 | -86 | whole -> whole | 17821 |
| inline / 163 | validate-existing | 13922 | 14042 | +120 | head -> head | 5958 |
| inline / 163 | implement | 16723 | 16843 | +120 | head -> head | 3157 |
| inline / 163 | implement-improve | 2974 | 2888 | -86 | whole -> whole | 17112 |
| inline / 163 | test | 19759 | 19879 | +120 | head -> head | 121 |
| inline / 163 | document | 15556 | 13469 | -2087 | whole -> head | 6531 |
| inline / 163 | verify | 19548 | 19668 | +120 | head -> head | 332 |
| inline / 163 | carry-forward | 19468 | 19588 | +120 | head -> head | 412 |
| inline / 163 | carry-forward-improve | 2962 | 2876 | -86 | whole -> whole | 17124 |
| ask-agent / 83 | step-plan | 19449 | 19538 | +89 | head -> head | 462 |
| ask-agent / 83 | step-plan-improve | 2713 | 2627 | -86 | whole -> whole | 17373 |
| ask-agent / 83 | test-spec | 12856 | 13056 | +200 | head -> head | 6944 |
| ask-agent / 83 | test-spec-improve | 1945 | 1859 | -86 | whole -> whole | 18141 |
| ask-agent / 83 | validate-existing | 12562 | 12762 | +200 | head -> head | 7238 |
| ask-agent / 83 | implement | 17217 | 17417 | +200 | head -> head | 2583 |
| ask-agent / 83 | implement-improve | 2654 | 2568 | -86 | whole -> whole | 17432 |
| ask-agent / 83 | test | 18239 | 18439 | +200 | head -> head | 1561 |
| ask-agent / 83 | document | 15684 | 12109 | -3575 | whole -> head | 7891 |
| ask-agent / 83 | verify | 18608 | 18808 | +200 | head -> head | 1192 |
| ask-agent / 83 | carry-forward | 19294 | 19494 | +200 | head -> head | 506 |
| ask-agent / 83 | carry-forward-improve | 2642 | 2556 | -86 | whole -> whole | 17444 |
| ask-agent / 163 | step-plan | 19260 | 19938 | +678 | head -> head | 62 |
| ask-agent / 163 | step-plan-improve | 3033 | 2947 | -86 | whole -> whole | 17053 |
| ask-agent / 163 | test-spec | 14216 | 14336 | +120 | head -> head | 5664 |
| ask-agent / 163 | test-spec-improve | 2265 | 2179 | -86 | whole -> whole | 17821 |
| ask-agent / 163 | validate-existing | 13922 | 14042 | +120 | head -> head | 5958 |
| ask-agent / 163 | implement | 18177 | 18297 | +120 | head -> head | 1703 |
| ask-agent / 163 | implement-improve | 2974 | 2888 | -86 | whole -> whole | 17112 |
| ask-agent / 163 | test | 19759 | 19879 | +120 | head -> head | 121 |
| ask-agent / 163 | document | 13349 | 13469 | +120 | head -> head | 6531 |
| ask-agent / 163 | verify | 19968 | 19508 | -460 | head -> head | 492 |
| ask-agent / 163 | carry-forward | 19884 | 19893 | +9 | head -> head | 107 |
| ask-agent / 163 | carry-forward-improve | 2962 | 2876 | -86 | whole -> whole | 17124 |
