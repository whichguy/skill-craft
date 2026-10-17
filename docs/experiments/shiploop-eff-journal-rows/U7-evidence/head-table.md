# Head allocation table (U7)

Printed characters of each producer stage's packet on the two-item run with multi-step plans (`test/shiploop_head_plans.py`), the largest occurrence of the stage, CLI path 96 characters, run directory 83 (a normal install) or 163 (the live run). `before` is the integration branch at e4c675d5 (U1's merge, packets and loop branches), `after` this unit. Form: head or whole print. `required end` is the character at which the required text ends (the last pointer line of a head; the end of the result block of a whole print): the hard bound is 19,500 at 83. `to 16,000` is the distance of the packet file's text to the whole-print limit (negative: the stage prints a head), `to 20,000` the room left under the host cut (Grok gives a model 20,000 characters whole; above that it keeps the first and last 10,000).

Over 20,000 before: plan inline/83 21144, plan inline/163 22024, plan ask-agent/83 21144, plan ask-agent/163 22024, step-plan inline/83 20856, step-plan inline/163 22296, step-plan ask-agent/83 22538, step-plan ask-agent/163 23978, implement ask-agent/163 20725.

Over 20,000 after: none.

Largest required end after: inline/83 (19378, 'plan'), inline/163 (19858, 'plan'), ask-agent/83 (19378, 'plan'), ask-agent/163 (19858, 'plan').


## inline/83

| stage | before | after | change | form | required end | to 16,000 (file) | to 20,000 (print) |
|---|--:|--:|--:|---|--:|--:|--:|
| intake | 9964 | 9988 | +24 | whole | 5737 | 6038 | 10012 |
| discovery | 12457 | 12456 | -1 | head | 10904 | -311 | 7544 |
| research | 13432 | 13456 | +24 | whole | 7674 | 2570 | 6544 |
| spec | 12099 | 12098 | -1 | head | 10391 | -1 | 7902 |
| test-strategy | 13458 | 13665 | +207 | head | 11637 | -1310 | 6335 |
| plan | 21144 | 19516 | -1628 | head | 19378 | -12163 | 484 |
| prepare | 11403 | 11427 | +24 | whole | 6210 | 4599 | 8573 |
| step-plan | 20856 | 19985 | -871 | head | 17775 | -7352 | 15 |
| test-spec | 14766 | 14791 | +25 | whole | 9768 | 1235 | 5209 |
| validate-existing | 15918 | 15943 | +25 | whole | 10746 | 83 | 4057 |
| implement | 17832 | 19427 | +1595 | head | 16475 | -5950 | 573 |
| test | 15753 | 18834 | +3081 | head | 15745 | -5065 | 1166 |
| document | 14153 | 14178 | +25 | whole | 8538 | 1848 | 5822 |
| verify | 16362 | 18699 | +2337 | head | 15451 | -4919 | 1301 |
| carry-forward | 17160 | 17983 | +823 | head | 15904 | -6134 | 2017 |
| system-test-author | 15428 | 15452 | +24 | whole | 10032 | 574 | 4548 |
| system-test | 14110 | 14134 | +24 | whole | 8900 | 1892 | 5866 |
| product-acceptance | 12952 | 13014 | +62 | head | 9226 | -115 | 6986 |
| release-plan | 13295 | 13294 | -1 | head | 11120 | -82 | 6706 |
| release-check | 12478 | 12502 | +24 | whole | 7322 | 3524 | 7498 |
| release | 12050 | 12074 | +24 | whole | 6881 | 3952 | 7926 |
| release-verify | 14586 | 14610 | +24 | whole | 9001 | 1416 | 5390 |
| operations | 11915 | 11939 | +24 | whole | 6775 | 4087 | 8061 |
| handoff | 13256 | 13280 | +24 | whole | 7606 | 2746 | 6720 |

## inline/163

| stage | before | after | change | form | required end | to 16,000 (file) | to 20,000 (print) |
|---|--:|--:|--:|---|--:|--:|--:|
| intake | 10844 | 10868 | +24 | whole | 6057 | 5158 | 9132 |
| discovery | 13337 | 13336 | -1 | head | 11384 | -1191 | 6664 |
| research | 14312 | 14336 | +24 | whole | 7994 | 1690 | 5664 |
| spec | 12979 | 12978 | -1 | head | 10871 | -961 | 7022 |
| test-strategy | 14338 | 14545 | +207 | head | 12117 | -2190 | 5455 |
| plan | 22024 | 19996 | -2028 | head | 19858 | -13123 | 4 |
| prepare | 12283 | 12307 | +24 | whole | 6530 | 3719 | 7693 |
| step-plan | 22296 | 20000 | -2296 | head | 18815 | -8872 | 0 |
| test-spec | 13855 | 14248 | +393 | head | 11287 | -125 | 5752 |
| validate-existing | 13534 | 14929 | +1395 | head | 12612 | -1624 | 5071 |
| implement | 19192 | 19669 | +477 | head | 17515 | -7390 | 331 |
| test | 17273 | 19862 | +2589 | head | 16946 | -6093 | 138 |
| document | 15593 | 15618 | +25 | whole | 9418 | 408 | 4382 |
| verify | 17722 | 19537 | +1815 | head | 16408 | -5757 | 463 |
| carry-forward | 18600 | 19423 | +823 | head | 16944 | -7654 | 577 |
| system-test-author | 13906 | 14113 | +207 | head | 11269 | -306 | 5887 |
| system-test | 14990 | 15014 | +24 | whole | 9220 | 1012 | 4986 |
| product-acceptance | 13832 | 13894 | +62 | head | 9706 | -1075 | 6106 |
| release-plan | 14175 | 14174 | -1 | head | 11600 | -962 | 5826 |
| release-check | 13358 | 13382 | +24 | whole | 7642 | 2644 | 6618 |
| release | 12930 | 12954 | +24 | whole | 7201 | 3072 | 7046 |
| release-verify | 15466 | 15490 | +24 | whole | 9321 | 536 | 4510 |
| operations | 12795 | 12819 | +24 | whole | 7095 | 3207 | 7181 |
| handoff | 14136 | 14160 | +24 | whole | 7926 | 1866 | 5840 |

## ask-agent/83

| stage | before | after | change | form | required end | to 16,000 (file) | to 20,000 (print) |
|---|--:|--:|--:|---|--:|--:|--:|
| intake | 10180 | 10204 | +24 | whole | 5737 | 5822 | 9796 |
| discovery | 12457 | 12456 | -1 | head | 10904 | -527 | 7544 |
| research | 13648 | 13672 | +24 | whole | 7674 | 2354 | 6328 |
| spec | 12099 | 12098 | -1 | head | 10391 | -217 | 7902 |
| test-strategy | 13458 | 13665 | +207 | head | 11637 | -1526 | 6335 |
| plan | 21144 | 19516 | -1628 | head | 19378 | -12379 | 484 |
| prepare | 11619 | 11643 | +24 | whole | 6210 | 4383 | 8357 |
| step-plan | 22538 | 19446 | -3092 | head | 18079 | -10743 | 554 |
| test-spec | 12495 | 12888 | +393 | head | 10327 | -333 | 7112 |
| validate-existing | 12174 | 13329 | +1155 | head | 11412 | -1592 | 6671 |
| implement | 19365 | 19810 | +445 | head | 17638 | -8416 | 190 |
| test | 15533 | 18524 | +2991 | head | 15745 | -6323 | 1476 |
| document | 15486 | 15511 | +25 | whole | 9911 | 515 | 4489 |
| verify | 16447 | 18642 | +2195 | head | 15650 | -6430 | 1358 |
| carry-forward | 18363 | 19249 | +886 | head | 15729 | -8968 | 751 |
| system-test-author | 15644 | 15668 | +24 | whole | 10032 | 358 | 4332 |
| system-test | 14326 | 14350 | +24 | whole | 8900 | 1676 | 5650 |
| product-acceptance | 12952 | 13014 | +62 | head | 9226 | -331 | 6986 |
| release-plan | 13295 | 13294 | -1 | head | 11120 | -298 | 6706 |
| release-check | 12694 | 12718 | +24 | whole | 7322 | 3308 | 7282 |
| release | 12266 | 12290 | +24 | whole | 6881 | 3736 | 7710 |
| release-verify | 14802 | 14826 | +24 | whole | 9001 | 1200 | 5174 |
| operations | 12131 | 12155 | +24 | whole | 6775 | 3871 | 7845 |
| handoff | 13472 | 13496 | +24 | whole | 7606 | 2530 | 6504 |

## ask-agent/163

| stage | before | after | change | form | required end | to 16,000 (file) | to 20,000 (print) |
|---|--:|--:|--:|---|--:|--:|--:|
| intake | 11060 | 11084 | +24 | whole | 6057 | 4942 | 8916 |
| discovery | 13337 | 13336 | -1 | head | 11384 | -1407 | 6664 |
| research | 14528 | 14552 | +24 | whole | 7994 | 1474 | 5448 |
| spec | 12979 | 12978 | -1 | head | 10871 | -1177 | 7022 |
| test-strategy | 14338 | 14545 | +207 | head | 12117 | -2406 | 5455 |
| plan | 22024 | 19996 | -2028 | head | 19858 | -13339 | 4 |
| prepare | 12499 | 12523 | +24 | whole | 6530 | 3503 | 7477 |
| step-plan | 23978 | 19971 | -4007 | head | 19015 | -12155 | 29 |
| test-spec | 13855 | 14248 | +393 | head | 11287 | -1693 | 5752 |
| validate-existing | 13534 | 14929 | +1395 | head | 12612 | -3192 | 5071 |
| implement | 20725 | 19863 | -862 | head | 18678 | -9856 | 137 |
| test | 17053 | 19862 | +2809 | head | 16946 | -7661 | 138 |
| document | 12999 | 13176 | +177 | head | 10158 | -925 | 6824 |
| verify | 17807 | 19736 | +1929 | head | 16607 | -7524 | 264 |
| carry-forward | 19803 | 19999 | +196 | head | 16662 | -10381 | 1 |
| system-test-author | 13906 | 14113 | +207 | head | 11269 | -522 | 5887 |
| system-test | 15206 | 15230 | +24 | whole | 9220 | 796 | 4770 |
| product-acceptance | 13832 | 13894 | +62 | head | 9706 | -1291 | 6106 |
| release-plan | 14175 | 14174 | -1 | head | 11600 | -1178 | 5826 |
| release-check | 13574 | 13598 | +24 | whole | 7642 | 2428 | 6402 |
| release | 13146 | 13170 | +24 | whole | 7201 | 2856 | 6830 |
| release-verify | 15682 | 15706 | +24 | whole | 9321 | 320 | 4294 |
| operations | 13011 | 13035 | +24 | whole | 7095 | 2991 | 6965 |
| handoff | 14352 | 14376 | +24 | whole | 7926 | 1650 | 5624 |
